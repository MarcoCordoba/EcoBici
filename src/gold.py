"""Capa Gold: modelo estrella construido a partir de silver.

Lee solo de silver (nunca de bronze) y genera:

    data/gold/dim_fecha/data.parquet      una fila por día
    data/gold/dim_estacion/data.parquet   una fila por estación
    data/gold/dim_usuario/data.parquet    una fila por usuario
    data/gold/fact_viajes/data.parquet    una fila por viaje válido

Como pide el enunciado, se usan los ids naturales como claves (sin claves
sustitutas). Acá no hay lógica de limpieza: eso es responsabilidad de silver.
"""
import pandas as pd

from src import config
from src.io_parquet import guardar_tabla

# Nombres de los días en español. pandas numera los días con day_of_week: 0 = lunes.
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Rangos etarios del enunciado: (edad mínima, edad máxima, etiqueta).
# Silver ya dejó en nulo las edades fuera de [16, 90], así que todas las no nulas
# caen en algún rango.
RANGOS_ETARIOS = [
    (16, 25, "16-25"),
    (26, 35, "26-35"),
    (36, 50, "36-50"),
    (51, 200, "51+"),
]


def leer_silver(tabla: str, columnas: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(config.SILVER / tabla / "data.parquet", columns=columnas)


def fecha_a_key(fechas: pd.Series) -> pd.Series:
    """Fecha -> entero AAAAMMDD (2019-03-15 -> 20190315)."""
    return (fechas.dt.year * 10_000 + fechas.dt.month * 100 + fechas.dt.day).astype("Int64")


# ===========================================================================
# dim_fecha
# ===========================================================================

def construir_dim_fecha(fechas_inicio: pd.Series) -> pd.DataFrame:
    """Una fila por cada día de los años cubiertos por los datos.

    Se genera el calendario completo (1/1 al 31/12) de cada año que aparece en
    los viajes. Así, un día sin viajes también existe en la dimensión (y en un
    reporte aparece con 0), pero no se inventan años sin datos (2017, 2018, ...).
    """
    anios = sorted(fechas_inicio.dt.year.dropna().unique())
    dias = pd.DatetimeIndex([])
    for anio in anios:
        dias = dias.append(pd.date_range(f"{anio}-01-01", f"{anio}-12-31", freq="D"))

    fecha = pd.Series(dias.astype("datetime64[ns]"))
    return pd.DataFrame({
        "fecha_key": fecha_a_key(fecha),
        "fecha": fecha,
        "anio": fecha.dt.year.astype("Int64"),
        "mes": fecha.dt.month.astype("Int64"),
        "dia": fecha.dt.day.astype("Int64"),
        "dia_semana": fecha.dt.day_of_week.map(dict(enumerate(DIAS_SEMANA))).astype("string"),
        "es_fin_de_semana": fecha.dt.day_of_week >= 5,   # 5 = sábado, 6 = domingo
    })


# ===========================================================================
# dim_estacion
# ===========================================================================

def construir_dim_estacion(viajes: pd.DataFrame) -> pd.DataFrame:
    """Una fila por estación, a partir de las estaciones de origen y de destino.

    - nombre_estacion: el del año más reciente en que la estación tiene un nombre
      válido (silver deja nulos los valores que no son nombres, como "ERRONEA").
      Si en ese año tuviera más de un nombre, se toma el más frecuente (en los
      datos actuales no pasa). Si nunca tuvo un nombre válido: "DESCONOCIDA".
    - primer_anio / ultimo_anio: primer y último año en que aparece (con o sin nombre).
    """
    # Se apilan origen y destino en un formato común (id, nombre, año).
    columnas = ["id_estacion", "nombre_estacion", "anio"]
    origen = viajes[["id_estacion_origen", "nombre_estacion_origen", "anio_fuente"]]
    destino = viajes[["id_estacion_destino", "nombre_estacion_destino", "anio_fuente"]]
    apariciones = pd.concat([origen.set_axis(columnas, axis=1),
                             destino.set_axis(columnas, axis=1)], ignore_index=True)

    # Años en que aparece cada estación (se cuentan también las filas sin nombre).
    rango_anios = (apariciones.groupby("id_estacion")["anio"]
                              .agg(primer_anio="min", ultimo_anio="max")
                              .reset_index())

    # Cantidad de apariciones de cada (id, nombre, año) con nombre válido: sirve
    # para desempatar. groupby descarta las filas con nombre nulo.
    conteo = (apariciones.groupby(columnas, observed=True).size()
                         .rename("veces").reset_index())

    # Nombre más reciente: ordenar por año desc. y frecuencia desc., quedarse con el primero.
    nombre_reciente = (conteo.sort_values(["id_estacion", "anio", "veces"],
                                          ascending=[True, False, False])
                             .drop_duplicates("id_estacion")
                             [["id_estacion", "nombre_estacion"]])

    dim = rango_anios.merge(nombre_reciente, on="id_estacion", how="left",
                            validate="one_to_one")
    dim["nombre_estacion"] = dim["nombre_estacion"].fillna("DESCONOCIDA")
    dim = dim[["id_estacion", "nombre_estacion", "primer_anio", "ultimo_anio"]]
    return (dim.sort_values("id_estacion")
               .reset_index(drop=True)
               .astype({"id_estacion": "Int64", "nombre_estacion": "string",
                        "primer_anio": "Int64", "ultimo_anio": "Int64"}))


# ===========================================================================
# dim_usuario
# ===========================================================================

def calcular_rango_etario(edad: pd.Series) -> pd.Series:
    """Edad -> rango etario. Edad nula -> DESCONOCIDO."""
    rango = pd.Series("DESCONOCIDO", index=edad.index, dtype="string")
    for minimo, maximo, etiqueta in RANGOS_ETARIOS:
        rango = rango.mask(edad.between(minimo, maximo).fillna(False), etiqueta)
    return rango


def construir_dim_usuario(usuarios: pd.DataFrame) -> pd.DataFrame:
    """Una fila por usuario de silver/usuarios (silver ya garantiza id único)."""
    return pd.DataFrame({
        "id_usuario": usuarios["id_usuario"].astype("string"),
        "genero": usuarios["genero"].astype("string"),
        "edad": usuarios["edad"],
        "rango_etario": calcular_rango_etario(usuarios["edad"]),
        "anio_alta": usuarios["fecha_alta"].dt.year.astype("Int64"),
    })


# ===========================================================================
# fact_viajes
# ===========================================================================

def construir_fact_viajes(viajes: pd.DataFrame) -> pd.DataFrame:
    """Una fila por viaje válido de silver, con claves hacia las dimensiones."""
    return pd.DataFrame({
        "id_viaje": viajes["id_viaje"],
        "fecha_key": fecha_a_key(viajes["fecha_hora_inicio"]),
        "hora_inicio": viajes["fecha_hora_inicio"].dt.hour.astype("Int64"),
        "id_estacion_origen": viajes["id_estacion_origen"],
        "id_estacion_destino": viajes["id_estacion_destino"],
        "id_usuario": viajes["id_usuario"],
        # Duración en minutos con un decimal (1185 s -> 19.8 min).
        "duracion_min": (viajes["duracion_seg"] / 60).round(1).astype("Float64"),
        "es_circular": (viajes["id_estacion_origen"] == viajes["id_estacion_destino"]).astype(bool),
    })


# ===========================================================================
# Verificación ("Cómo verificar que está bien")
# ===========================================================================

def verificar(fact: pd.DataFrame, filas_silver: int, dim_fecha: pd.DataFrame,
              dim_estacion: pd.DataFrame, dim_usuario: pd.DataFrame) -> dict:
    """Controles de integridad del modelo estrella.

    Errores (detienen el pipeline):
    - fact_viajes tiene las mismas filas que silver/viajes.
    - Todo fecha_key de fact existe en dim_fecha.
    - Todo id de estación (origen y destino) existe en dim_estacion.
    - Las claves de las dimensiones son únicas.

    Informativo (no es error, se anota en DECISIONES.md):
    - Viajes cuyo id_usuario no aparece en dim_usuario.
    """
    if len(fact) != filas_silver:
        raise AssertionError(f"fact_viajes tiene {len(fact):,} filas y silver {filas_silver:,}")

    for dim, clave in [(dim_fecha, "fecha_key"), (dim_estacion, "id_estacion"),
                       (dim_usuario, "id_usuario")]:
        if dim[clave].duplicated().any():
            raise AssertionError(f"Clave {clave} repetida en su dimensión")

    if not fact["fecha_key"].isin(dim_fecha["fecha_key"]).all():
        raise AssertionError("Hay fecha_key en fact_viajes que no existen en dim_fecha")

    for col in ["id_estacion_origen", "id_estacion_destino"]:
        if not fact[col].isin(dim_estacion["id_estacion"]).all():
            raise AssertionError(f"Hay {col} en fact_viajes que no existen en dim_estacion")

    con_usuario = fact["id_usuario"].notna()
    huerfanos = con_usuario & ~fact["id_usuario"].isin(dim_usuario["id_usuario"])
    resumen = {
        "viajes": len(fact),
        "sin_id_usuario": int((~con_usuario).sum()),
        "id_usuario_fuera_de_dim": int(huerfanos.sum()),
        "fuera_de_dim_por_anio": (fact.loc[huerfanos, "fecha_key"] // 10_000)
                                     .value_counts().sort_index().to_dict(),
    }
    print(f"[gold] verificación OK. Viajes sin id_usuario: {resumen['sin_id_usuario']:,} | "
          f"con id_usuario que no está en dim_usuario: {resumen['id_usuario_fuera_de_dim']:,} "
          f"{resumen['fuera_de_dim_por_anio']}")
    return resumen


# ===========================================================================
# Punto de entrada de la capa
# ===========================================================================

def ejecutar() -> dict:
    viajes = leer_silver("viajes")
    usuarios = leer_silver("usuarios")

    dim_fecha = construir_dim_fecha(viajes["fecha_hora_inicio"])
    dim_estacion = construir_dim_estacion(viajes)
    dim_usuario = construir_dim_usuario(usuarios)
    fact = construir_fact_viajes(viajes)
    filas_silver = len(viajes)
    del viajes, usuarios

    resumen = verificar(fact, filas_silver, dim_fecha, dim_estacion, dim_usuario)

    for nombre, tabla in [("dim_fecha", dim_fecha), ("dim_estacion", dim_estacion),
                          ("dim_usuario", dim_usuario), ("fact_viajes", fact)]:
        guardar_tabla(tabla, config.GOLD / nombre)
        print(f"[gold] {nombre}: {len(tabla):,} filas")
    return resumen


if __name__ == "__main__":
    ejecutar()
