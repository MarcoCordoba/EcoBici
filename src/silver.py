"""Capa Silver: datos limpios, tipados y unificados en un esquema canónico.

Toma los Parquet de bronze (todo texto, un esquema distinto por año) y genera:

    data/silver/viajes/data.parquet               viajes válidos de los tres años
    data/silver/viajes_cuarentena/data.parquet    viajes rechazados + columna motivo
    data/silver/usuarios/data.parquet             un registro por usuario
    data/silver/usuarios_cuarentena/data.parquet  usuarios rechazados + columna motivo

Todo lo que cambia entre años (nombres de columnas, formatos de fecha, sufijos en
los ids) está concentrado en las constantes de la primera sección. Si llega un año
nuevo con otro formato, solo se agrega una entrada ahí.
"""
import pandas as pd
import pyarrow.parquet as pq

from src import config
from src.io_parquet import EscritorParquet

# Tipo para las columnas de texto. Es el dtype "string" de pandas (usa pd.NA para
# los nulos, como pide el esquema), con almacenamiento en Arrow: ocupa mucha menos
# memoria que el almacenamiento en objetos de Python, lo que importa con los
# 6,2 millones de viajes de 2019.
STRING = pd.StringDtype("pyarrow")


# ===========================================================================
# 1. Esquemas canónicos (enunciado, Tarea 3, paso 1)
# ===========================================================================

ESQUEMA_VIAJES = {
    "id_viaje": "string",
    "fecha_hora_inicio": "datetime64[ns]",
    "fecha_hora_fin": "datetime64[ns]",
    "duracion_seg": "Int64",
    "id_estacion_origen": "Int64",
    "nombre_estacion_origen": "string",
    "id_estacion_destino": "Int64",
    "nombre_estacion_destino": "string",
    "id_usuario": "string",
    "anio_fuente": "Int64",
}
ESQUEMA_VIAJES_CUARENTENA = {**ESQUEMA_VIAJES, "motivo": "string"}

ESQUEMA_USUARIOS = {
    "id_usuario": "string",
    "genero": "string",
    "edad": "Int64",
    "fecha_alta": "datetime64[ns]",
    "anio_fuente": "Int64",
}
ESQUEMA_USUARIOS_CUARENTENA = {**ESQUEMA_USUARIOS, "motivo": "string"}


# ===========================================================================
# 2. Mapeos de columnas y valores (todo lo que cambia entre años)
# ===========================================================================

# Columna original -> columna canónica. Lo que no está en el mapeo se descarta.
# - 2016 no trae id de viaje: se genera en generar_id_viaje_2016().
# - 2016 no trae id de usuario: la columna se crea vacía.
# - 2016 trae la duración en otra unidad (texto timedelta) y además no coincide
#   con fin - inicio: no se mapea y se recalcula desde las fechas.
MAPEO_VIAJES = {
    2016: {
        "fecha_origen_recorrido": "fecha_hora_inicio",
        "fecha_destino_recorrido": "fecha_hora_fin",
        "id_estacion_origen": "id_estacion_origen",
        "nombre_estacion_origen": "nombre_estacion_origen",
        "id_estacion_destino": "id_estacion_destino",
        "nombre_estacion_destino": "nombre_estacion_destino",
    },
    2019: {
        "Id_recorrido": "id_viaje",
        "fecha_origen_recorrido": "fecha_hora_inicio",
        "fecha_destino_recorrido": "fecha_hora_fin",
        "duracion_recorrido": "duracion_seg",
        "id_estacion_origen": "id_estacion_origen",
        "nombre_estacion_origen": "nombre_estacion_origen",
        "id_estacion_destino": "id_estacion_destino",
        "nombre_estacion_destino": "nombre_estacion_destino",
        "id_usuario": "id_usuario",
    },
    2024: {
        "id_recorrido": "id_viaje",
        "fecha_origen_recorrido": "fecha_hora_inicio",
        "fecha_destino_recorrido": "fecha_hora_fin",
        "duracion_recorrido": "duracion_seg",
        "id_estacion_origen": "id_estacion_origen",
        "nombre_estacion_origen": "nombre_estacion_origen",
        "id_estacion_destino": "id_estacion_destino",
        "nombre_estacion_destino": "nombre_estacion_destino",
        "id_usuario": "id_usuario",
    },
}

# hora_alta no es una columna canónica: se usa solo para armar fecha_alta.
MAPEO_USUARIOS = {
    2016: {"id_usuario": "id_usuario", "genero_usuario": "genero", "edad_usuario": "edad",
           "fecha_alta": "fecha_alta", "hora_alta": "hora_alta"},
    2019: {"ID_usuario": "id_usuario", "genero_usuario": "genero", "edad_usuario": "edad",
           "fecha_alta": "fecha_alta", "hora_alta": "hora_alta"},
    2024: {"id_usuario": "id_usuario", "genero_usuario": "genero", "edad_usuario": "edad",
           "fecha_alta": "fecha_alta", "hora_alta": "hora_alta"},
}

# Formatos de fecha de cada año (verificados en la Tarea 1 sobre los archivos completos).
FORMATO_FECHA_VIAJES = {
    2016: "%Y-%m-%d %H:%M:%S",
    2019: "%Y-%m-%d %H:%M:%S",
    2024: "%Y-%m-%d %H:%M:%S",
}
# En usuarios la fecha y la hora vienen separadas; se unen con un espacio.
FORMATO_FECHA_USUARIOS = {
    2016: "%d-%m-%y %I:%M:%S %p",   # 31-12-16 3:45:19 PM
    2019: "%Y-%m-%d %H:%M:%S",
    2024: "%Y-%m-%d %H:%M:%S",
}

# Valores de género encontrados con value_counts() en cada año -> valor canónico.
# Cualquier valor que no esté acá (incluido vacío/nulo) pasa a DESCONOCIDO.
MAPEO_GENERO = {
    "F": "F", "FEMALE": "F",     # 2016 usa F; 2019 y 2024 usan FEMALE
    "M": "M", "MALE": "M",       # 2016 usa M; 2019 y 2024 usan MALE
    "OTHER": "OTRO",             # solo en 2019 y 2024
}

EDAD_MIN, EDAD_MAX = 16, 90       # fuera de este rango la edad pasa a nulo
DURACION_MAX_SEG = 24 * 60 * 60   # 86.400 s

# Vocales acentuadas -> sin acento. La Ñ se conserva porque es otra letra.
SIN_TILDES = str.maketrans("ÁÉÍÓÚÜÀÈÌÒÙÂÊÎÔÛ", "AEIOUUAEIOUAEIOU")

# Valores que aparecen en la columna de nombre pero no son un nombre de estación
# (se evalúan después de normalizar). Pasan a nulo, como un género no reconocido.
# Ejemplos reales de 2019: la estación 1 figura como "ERRONEA" (su dirección es la
# de Facultad de Derecho), la 10 como "KP1808000368" y la 300 como "175".
NOMBRE_ESTACION_INVALIDO = r"^(ERRONEA|KP\d+|\d+)$"


# ===========================================================================
# 3. Funciones auxiliares de limpieza (reutilizadas por viajes y usuarios)
# ===========================================================================

def leer_bronze(conjunto: str, anio: int, columnas: list[str]) -> pd.DataFrame:
    """Lee de bronze solo las columnas necesarias (ahorra memoria en 2019)."""
    ruta = config.BRONZE / conjunto / f"anio={anio}" / "data.parquet"
    return pd.read_parquet(ruta, columns=columnas)


def contar_filas_bronze(conjunto: str, anio: int) -> int:
    """Filas de bronze leídas de los metadatos del Parquet (sin cargar datos)."""
    ruta = config.BRONZE / conjunto / f"anio={anio}" / "data.parquet"
    return pq.ParquetFile(ruta).metadata.num_rows


def vacios_a_nulo(df: pd.DataFrame) -> pd.DataFrame:
    """Bronze guarda los vacíos como "" (y 2019 trae el texto "NA" en las edades).

    Acá se decide que ambos significan "sin dato" y se pasan a pd.NA.
    """
    df = df.astype(STRING)
    for col in df.columns:
        texto = df[col].str.strip()
        df[col] = texto.mask(texto.isin(["", "NA"]))
    return df


def renombrar(df: pd.DataFrame, mapeo: dict[str, str]) -> pd.DataFrame:
    """Renombra según el mapeo y descarta las columnas que no están en él."""
    df = df.rename(columns=mapeo)
    return df[list(mapeo.values())]


def limpiar_id(serie: pd.Series) -> pd.Series:
    """Lleva un id a su forma canónica de texto.

    - 2019 agrega el sufijo "BAEcobici" a todos los ids (9379BAEcobici -> 9379).
    - 2024 guarda id_usuario como decimal (992557.0 -> 992557).
    """
    return (serie.astype(STRING)
                 .str.removesuffix("BAEcobici")
                 .str.replace(r"\.0$", "", regex=True))


def a_entero(serie: pd.Series) -> pd.Series:
    """Texto -> Int64. Lo que no es número queda nulo (y lo atrapan las reglas de calidad)."""
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


def a_fecha(serie: pd.Series, formato: str) -> pd.Series:
    """Texto -> datetime64[ns] con un formato explícito. Lo no interpretable queda NaT."""
    return pd.to_datetime(serie, format=formato, errors="coerce").astype("datetime64[ns]")


def normalizar_nombre_estacion(serie: pd.Series) -> pd.Series:
    """Normaliza un nombre de estación para que sea comparable entre años.

    Además de lo que pide el enunciado (strip, mayúsculas, espacios múltiples),
    se quita el prefijo numérico de 2019/2024 ("005 - PLAZA ITALIA") y las tildes
    (en un año figura "PACÍFICO" y en otro "PACIFICO" para la misma estación).
    Por último, los valores que no son un nombre (ver NOMBRE_ESTACION_INVALIDO)
    quedan nulos.
    """
    nombre = (serie.str.strip()
                   .str.upper()
                   .str.replace(r"^\d+\s*-\s*", "", regex=True)  # prefijo "005 - "
                   .str.translate(SIN_TILDES)
                   .str.replace(r"\s+", " ", regex=True)          # espacios múltiples
                   .str.strip())
    return nombre.mask(nombre.str.fullmatch(NOMBRE_ESTACION_INVALIDO).fillna(False))


def normalizar_genero(serie: pd.Series) -> pd.Series:
    """Lleva las variantes de género a F, M, OTRO o DESCONOCIDO."""
    return serie.str.upper().map(MAPEO_GENERO).fillna("DESCONOCIDO").astype(STRING)


# ===========================================================================
# 4. Validación de esquema (paso 6: se llama siempre antes de guardar)
# ===========================================================================

def validar_esquema(df: pd.DataFrame, esquema: dict[str, str]) -> None:
    """Lanza un error si las columnas o los tipos no son exactamente los del esquema."""
    if list(df.columns) != list(esquema):
        raise ValueError(f"Columnas {list(df.columns)} != esquema {list(esquema)}")
    distintos = {c: str(df[c].dtype) for c, t in esquema.items() if str(df[c].dtype) != t}
    if distintos:
        raise TypeError(f"Tipos que no coinciden con el esquema: {distintos}")


def aplicar_esquema(df: pd.DataFrame, esquema: dict[str, str]) -> pd.DataFrame:
    """Ordena las columnas como el esquema y fija el tipo exacto de cada una."""
    tipos = {c: (STRING if t == "string" else t) for c, t in esquema.items()}
    return df[list(esquema)].astype(tipos)


# ===========================================================================
# 5. Escritura idempotente: ver src/io_parquet.py (EscritorParquet)
# ===========================================================================


# ===========================================================================
# 6. Viajes: transformación de un año al esquema canónico (pasos 2, 3 y 4)
# ===========================================================================

def generar_id_viaje_2016(df: pd.DataFrame) -> pd.Series:
    """2016 no trae id de recorrido: se genera '2016-<fila>' con la fila de bronze.

    La numeración sale del orden original del archivo (antes de cualquier filtro),
    por lo que es estable entre ejecuciones y permite volver a la fila de origen.
    """
    fila = pd.Series(range(1, len(df) + 1), index=df.index)
    return ("2016-" + fila.astype(str).str.zfill(6)).astype(STRING)


def transformar_viajes(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Convierte los viajes de bronze de un año al esquema canónico (sin filtrar filas)."""
    df = vacios_a_nulo(df)
    df = renombrar(df, MAPEO_VIAJES[anio])

    # --- Ids -----------------------------------------------------------------
    if "id_viaje" in df:
        df["id_viaje"] = limpiar_id(df["id_viaje"])
    else:
        df["id_viaje"] = generar_id_viaje_2016(df)

    if "id_usuario" in df:
        df["id_usuario"] = limpiar_id(df["id_usuario"])
    else:
        df["id_usuario"] = pd.Series(pd.NA, index=df.index, dtype=STRING)

    for col in ["id_estacion_origen", "id_estacion_destino"]:
        df[col] = a_entero(limpiar_id(df[col]))

    # --- Fechas --------------------------------------------------------------
    formato = FORMATO_FECHA_VIAJES[anio]
    df["fecha_hora_inicio"] = a_fecha(df["fecha_hora_inicio"], formato)
    df["fecha_hora_fin"] = a_fecha(df["fecha_hora_fin"], formato)

    # --- Duración ------------------------------------------------------------
    if "duracion_seg" in df:
        # 2019 usa coma como separador de miles ("2,814" = 2814 s).
        df["duracion_seg"] = a_entero(df["duracion_seg"].str.replace(",", "", regex=False))
    else:
        # No viene (o viene en otra unidad): se calcula desde las fechas.
        segundos = (df["fecha_hora_fin"] - df["fecha_hora_inicio"]).dt.total_seconds()
        df["duracion_seg"] = segundos.round().astype("Int64")

    # --- Nombres de estación -------------------------------------------------
    for col in ["nombre_estacion_origen", "nombre_estacion_destino"]:
        df[col] = normalizar_nombre_estacion(df[col])

    df["anio_fuente"] = anio
    return aplicar_esquema(df, ESQUEMA_VIAJES)


# ===========================================================================
# 7. Viajes: controles de calidad y cuarentena (paso 5)
# ===========================================================================

def aplicar_calidad_viajes(df: pd.DataFrame, ids_previos: pd.Series):
    """Devuelve (validos, cuarentena).

    Cada fila recibe el motivo de la PRIMERA regla que falla, en el orden del
    enunciado. ids_previos son los id_viaje de los años ya procesados: un id que
    ya apareció en una fila anterior (de este año o de uno previo) es DUPLICADO.
    """
    motivo = pd.Series(pd.NA, index=df.index, dtype=STRING)

    reglas = [
        ("FECHA_INVALIDA",
         df["fecha_hora_inicio"].isna() | df["fecha_hora_fin"].isna()),
        ("ESTACION_NULA",
         df["id_estacion_origen"].isna() | df["id_estacion_destino"].isna()),
        ("FIN_ANTERIOR_A_INICIO",
         df["fecha_hora_fin"] < df["fecha_hora_inicio"]),
        ("DURACION_MAYOR_24H",
         df["duracion_seg"] > DURACION_MAX_SEG),
        ("DUPLICADO",
         df["id_viaje"].duplicated() | df["id_viaje"].isin(ids_previos)),
    ]
    for nombre, condicion in reglas:
        # Las comparaciones con nulos dan NA; se toman como "no falla esta regla"
        # (los nulos ya los atrapan las reglas 1 y 2).
        condicion = condicion.fillna(False).astype(bool)
        motivo = motivo.mask(motivo.isna() & condicion, nombre)

    validos = df[motivo.isna()]
    cuarentena = df[motivo.notna()].assign(motivo=motivo[motivo.notna()])
    return validos, cuarentena


def procesar_viajes() -> dict[int, dict]:
    """Transforma, valida y guarda los viajes de todos los años, uno por vez.

    Se procesa año por año para no tener los ~10 millones de viajes en memoria a
    la vez; cada año se agrega como una parte del mismo Parquet.
    """
    resumen = {}
    ids_previos = pd.Series([], dtype=STRING)

    with EscritorParquet(config.SILVER / "viajes") as out_validos, \
         EscritorParquet(config.SILVER / "viajes_cuarentena") as out_cuarentena:
        for anio in config.ANIOS:
            bronze = leer_bronze("recorridos", anio, list(MAPEO_VIAJES[anio]))
            filas_bronze = len(bronze)
            viajes = transformar_viajes(bronze, anio)
            del bronze

            validos, cuarentena = aplicar_calidad_viajes(viajes, ids_previos)
            ids_previos = pd.concat([ids_previos, viajes["id_viaje"]], ignore_index=True)
            del viajes

            validar_esquema(validos, ESQUEMA_VIAJES)
            validar_esquema(cuarentena, ESQUEMA_VIAJES_CUARENTENA)
            out_validos.escribir(validos)
            out_cuarentena.escribir(cuarentena)

            resumen[anio] = {
                "bronze": filas_bronze,
                "silver": len(validos),
                "cuarentena": len(cuarentena),
                "motivos": cuarentena["motivo"].value_counts().to_dict(),
            }
            print(f"[silver] viajes {anio}: {filas_bronze:,} bronze -> "
                  f"{len(validos):,} válidos + {len(cuarentena):,} cuarentena "
                  f"{resumen[anio]['motivos']}")
            del validos, cuarentena
    return resumen


# ===========================================================================
# 8. Usuarios
# ===========================================================================

def transformar_usuarios(df: pd.DataFrame, anio: int) -> tuple[pd.DataFrame, int]:
    """Convierte los usuarios de bronze de un año al esquema canónico.

    Devuelve también cuántas edades fuera de rango se pasaron a nulo.
    """
    df = vacios_a_nulo(df)
    df = renombrar(df, MAPEO_USUARIOS[anio])

    df["id_usuario"] = limpiar_id(df["id_usuario"])
    df["genero"] = normalizar_genero(df["genero"])

    # Edad: las menores a 16 o mayores a 90 no se rechazan, se pasan a nulo.
    edad = a_entero(df["edad"])
    fuera_de_rango = (edad < EDAD_MIN) | (edad > EDAD_MAX)
    df["edad"] = edad.mask(fuera_de_rango.fillna(False))

    # Fecha y hora de alta vienen en dos columnas: se unen y se convierten juntas.
    texto_alta = df["fecha_alta"] + " " + df["hora_alta"]
    df["fecha_alta"] = a_fecha(texto_alta, FORMATO_FECHA_USUARIOS[anio])

    df["anio_fuente"] = anio
    return aplicar_esquema(df, ESQUEMA_USUARIOS), int(fuera_de_rango.sum())


def aplicar_calidad_usuarios(df: pd.DataFrame):
    """Devuelve (validos, cuarentena) para la tabla de usuarios de todos los años.

    Reglas, en orden:
    1. ID_NULO: id_usuario vacío.
    2. DUPLICADO: el id ya está en otro registro con fecha_alta más reciente.
       Se conserva el más reciente (a igual fecha, el de anio_fuente mayor).
    """
    orden = df.sort_values(["fecha_alta", "anio_fuente"], ascending=False,
                           na_position="last", kind="stable")
    duplicado = orden["id_usuario"].duplicated() & orden["id_usuario"].notna()

    motivo = pd.Series(pd.NA, index=df.index, dtype=STRING)
    motivo = motivo.mask(df["id_usuario"].isna(), "ID_NULO")
    motivo = motivo.mask(motivo.isna() & duplicado.reindex(df.index), "DUPLICADO")

    validos = df[motivo.isna()]
    cuarentena = df[motivo.notna()].assign(motivo=motivo[motivo.notna()])
    return validos, cuarentena


def procesar_usuarios() -> dict[int, dict]:
    """Transforma, valida y guarda los usuarios (son pocos: se procesan juntos)."""
    partes, edades_nulas = [], {}
    for anio in config.ANIOS:
        bronze = leer_bronze("usuarios", anio, list(MAPEO_USUARIOS[anio]))
        usuarios, edades_nulas[anio] = transformar_usuarios(bronze, anio)
        partes.append(usuarios)
    usuarios = pd.concat(partes, ignore_index=True)

    validos, cuarentena = aplicar_calidad_usuarios(usuarios)
    validar_esquema(validos, ESQUEMA_USUARIOS)
    validar_esquema(cuarentena, ESQUEMA_USUARIOS_CUARENTENA)

    with EscritorParquet(config.SILVER / "usuarios") as out:
        out.escribir(validos)
    with EscritorParquet(config.SILVER / "usuarios_cuarentena") as out:
        out.escribir(cuarentena)

    resumen = {}
    for anio in config.ANIOS:
        c = cuarentena[cuarentena["anio_fuente"] == anio]
        resumen[anio] = {
            "bronze": contar_filas_bronze("usuarios", anio),
            "silver": int((validos["anio_fuente"] == anio).sum()),
            "cuarentena": len(c),
            "motivos": c["motivo"].value_counts().to_dict(),
            "edades_a_nulo": edades_nulas[anio],
        }
        print(f"[silver] usuarios {anio}: {resumen[anio]['bronze']:,} bronze -> "
              f"{resumen[anio]['silver']:,} válidos + {len(c):,} cuarentena "
              f"{resumen[anio]['motivos']} | edades fuera de rango -> nulo: {edades_nulas[anio]}")
    return resumen


# ===========================================================================
# 9. Verificación final (paso 6), leyendo lo que quedó escrito en disco
# ===========================================================================

def verificar(resumen_viajes: dict, resumen_usuarios: dict) -> None:
    """Controles del paso 6 sobre los archivos ya guardados.

    - Conciliación: bronze = silver + cuarentena, por año, en viajes y usuarios.
    - id_viaje único en silver/viajes; id_usuario único en silver/usuarios.
    - Columnas y tipos idénticos al esquema canónico (leídos de disco).
    """
    for nombre, resumen in [("viajes", resumen_viajes), ("usuarios", resumen_usuarios)]:
        for anio, r in resumen.items():
            if r["bronze"] != r["silver"] + r["cuarentena"]:
                raise AssertionError(f"Conciliación {nombre} {anio}: {r}")

    viajes = pd.read_parquet(config.SILVER / "viajes" / "data.parquet")
    validar_esquema(viajes, ESQUEMA_VIAJES)
    if viajes["id_viaje"].duplicated().any():
        raise AssertionError("id_viaje repetido en silver/viajes")
    del viajes

    usuarios = pd.read_parquet(config.SILVER / "usuarios" / "data.parquet")
    validar_esquema(usuarios, ESQUEMA_USUARIOS)
    if usuarios["id_usuario"].duplicated().any():
        raise AssertionError("id_usuario repetido en silver/usuarios")

    for tabla, esquema in [("viajes_cuarentena", ESQUEMA_VIAJES_CUARENTENA),
                           ("usuarios_cuarentena", ESQUEMA_USUARIOS_CUARENTENA)]:
        validar_esquema(pd.read_parquet(config.SILVER / tabla / "data.parquet"), esquema)

    print("[silver] verificación OK: conciliación, unicidad de ids y esquemas")


# ===========================================================================
# Punto de entrada de la capa
# ===========================================================================

def ejecutar() -> dict:
    resumen = {"viajes": procesar_viajes(), "usuarios": procesar_usuarios()}
    verificar(resumen["viajes"], resumen["usuarios"])
    return resumen


if __name__ == "__main__":
    ejecutar()
