"""Capa Bronze: copia fiel de los archivos de data/raw/ en Parquet.

Reglas de esta capa (enunciado, sección 3.1):
- Todas las filas y todas las columnas, con sus nombres originales.
- Todos los valores como texto (dtype=str): no se convierte ni se limpia nada.
- Se agregan tres columnas de metadatos: _archivo_origen, _fecha_ingesta y _anio.

Salida:
    data/bronze/recorridos/anio=AAAA/data.parquet
    data/bronze/usuarios/anio=AAAA/data.parquet
"""
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src import config

# Cantidad de filas que se leen por vez. Con 500.000 filas de texto cada bloque
# ocupa unos cientos de MB, lo que permite procesar el archivo de 2019 (6,2 millones
# de filas, 1,9 GB descomprimido) sin cargarlo entero en memoria.
CHUNKSIZE = 500_000

COLUMNAS_METADATOS = ["_archivo_origen", "_fecha_ingesta", "_anio"]


# ---------------------------------------------------------------------------
# Lectura del archivo original
# ---------------------------------------------------------------------------

def elegir_csv_del_zip(ruta_zip: Path) -> str:
    """Devuelve el nombre del CSV que hay dentro del ZIP.

    Hoy cada ZIP trae un solo CSV, pero si el portal agregara otro archivo
    (por ejemplo un diccionario de datos) preferimos fallar con un mensaje
    claro antes que ingestar el archivo equivocado.
    """
    with zipfile.ZipFile(ruta_zip) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(csvs) != 1:
        raise ValueError(f"{ruta_zip.name}: se esperaba un único CSV y se encontró {csvs}")
    return csvs[0]


def leer_por_partes(ruta: Path):
    """Itera el archivo original en bloques de CHUNKSIZE filas, todo como texto.

    - dtype=str: ningún valor se interpreta como número o fecha.
    - keep_default_na=False: pandas no convierte "", "NA", "null", etc. en NaN;
      el texto queda exactamente como vino (un vacío queda como "").
    - Los ZIP se leen directo, sin descomprimir a disco. Se abre el CSV con
      zipfile para elegir explícitamente cuál leer.
    """
    opciones = dict(dtype=str, keep_default_na=False, chunksize=CHUNKSIZE)

    if ruta.suffix.lower() == ".zip":
        with zipfile.ZipFile(ruta) as zf, zf.open(elegir_csv_del_zip(ruta)) as f:
            yield from pd.read_csv(f, **opciones)
    else:
        yield from pd.read_csv(ruta, **opciones)


# ---------------------------------------------------------------------------
# Ingesta de un archivo
# ---------------------------------------------------------------------------

def agregar_metadatos(df: pd.DataFrame, ruta: Path, anio: int, fecha_ingesta: str) -> pd.DataFrame:
    """Agrega las columnas de metadatos (el guion bajo indica que no vienen del origen)."""
    df["_archivo_origen"] = ruta.name
    df["_fecha_ingesta"] = fecha_ingesta
    df["_anio"] = str(anio)
    return df


def ingestar_archivo(ruta: Path, anio: int, destino: Path) -> int:
    """Copia un archivo original a destino/anio=AAAA/data.parquet. Devuelve las filas escritas.

    Idempotencia: el Parquet se escribe primero en un archivo temporal y, recién
    cuando terminó bien, reemplaza al anterior. Así, ejecutar dos veces deja
    siempre el mismo resultado (nunca se agregan filas a un archivo existente) y
    si el proceso se corta a la mitad no queda un data.parquet incompleto.
    """
    carpeta = destino / f"anio={anio}"
    carpeta.mkdir(parents=True, exist_ok=True)
    final = carpeta / "data.parquet"
    temporal = carpeta / "data.parquet.tmp"

    # Una sola marca de tiempo por archivo: todas sus filas comparten la misma ingesta.
    fecha_ingesta = datetime.now().isoformat(timespec="seconds")

    escritor = None
    filas = 0
    try:
        for bloque in leer_por_partes(ruta):
            bloque = agregar_metadatos(bloque, ruta, anio, fecha_ingesta)

            # Todas las columnas se guardan como string en Parquet.
            tabla = pa.Table.from_pandas(bloque, preserve_index=False)
            tabla = tabla.cast(pa.schema([(c, pa.string()) for c in tabla.column_names]))

            # El escritor se crea con el esquema del primer bloque; los siguientes
            # se agregan como nuevos "row groups" del mismo archivo temporal.
            if escritor is None:
                escritor = pq.ParquetWriter(temporal, tabla.schema)
            escritor.write_table(tabla)
            filas += len(bloque)
    finally:
        if escritor is not None:
            escritor.close()

    temporal.replace(final)  # reemplazo atómico del archivo anterior
    return filas


# ---------------------------------------------------------------------------
# Verificación
# ---------------------------------------------------------------------------

def columnas_originales(ruta: Path) -> list[str]:
    """Lee solo el encabezado del archivo original, para comparar contra bronze."""
    if ruta.suffix.lower() == ".zip":
        with zipfile.ZipFile(ruta) as zf, zf.open(elegir_csv_del_zip(ruta)) as f:
            return list(pd.read_csv(f, dtype=str, nrows=0).columns)
    return list(pd.read_csv(ruta, dtype=str, nrows=0).columns)


def verificar(ruta_original: Path, parquet: Path, filas_leidas: int) -> None:
    """Controles de la sección 'Cómo verificar que está bien' de la Tarea 2.

    - La cantidad de filas del Parquet es igual a la leída del original.
    - Las columnas son las originales (mismo orden) más las tres de metadatos.
    - Todas las columnas están guardadas como texto.
    Se usan solo los metadatos del Parquet, sin volver a cargar los datos.
    """
    archivo = pq.ParquetFile(parquet)
    esquema = archivo.schema_arrow

    if archivo.metadata.num_rows != filas_leidas:
        raise AssertionError(f"{parquet}: {archivo.metadata.num_rows} filas, se esperaban {filas_leidas}")

    esperadas = columnas_originales(ruta_original) + COLUMNAS_METADATOS
    if esquema.names != esperadas:
        raise AssertionError(f"{parquet}: columnas {esquema.names}, se esperaban {esperadas}")

    no_texto = [f.name for f in esquema if f.type != pa.string()]
    if no_texto:
        raise AssertionError(f"{parquet}: columnas que no son texto: {no_texto}")


# ---------------------------------------------------------------------------
# Punto de entrada de la capa
# ---------------------------------------------------------------------------

def ingestar_conjunto(nombre: str, archivos: dict[int, Path]) -> dict[int, int]:
    """Ingesta y verifica todos los años de un conjunto (recorridos o usuarios)."""
    destino = config.BRONZE / nombre
    conteos = {}
    for anio, ruta in archivos.items():
        filas = ingestar_archivo(ruta, anio, destino)
        verificar(ruta, destino / f"anio={anio}" / "data.parquet", filas)
        conteos[anio] = filas
        print(f"[bronze] {nombre} {anio}: {filas:,} filas  <- {ruta.name}")
    return conteos


def ejecutar() -> dict[str, dict[int, int]]:
    """Ejecuta la capa bronze completa. Devuelve las filas por conjunto y año."""
    return {
        "recorridos": ingestar_conjunto("recorridos", config.ARCHIVOS_RECORRIDOS),
        "usuarios": ingestar_conjunto("usuarios", config.ARCHIVOS_USUARIOS),
    }


if __name__ == "__main__":
    ejecutar()
