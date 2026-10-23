"""Escritura idempotente de tablas Parquet, compartida por silver y gold."""
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class EscritorParquet:
    """Escribe <carpeta>/data.parquet de a partes, a través de un archivo temporal.

    Uso:
        with EscritorParquet(carpeta) as out:
            out.escribir(df_parte_1)
            out.escribir(df_parte_2)

    Al salir del bloque sin errores, el temporal reemplaza al data.parquet anterior.
    Así cada ejecución deja exactamente el mismo resultado (nunca se agregan filas a
    un archivo existente) y, si hay un error, no queda un archivo a medio escribir.
    """

    def __init__(self, carpeta: Path):
        carpeta.mkdir(parents=True, exist_ok=True)
        self.final = carpeta / "data.parquet"
        self.temporal = carpeta / "data.parquet.tmp"
        self.escritor = None

    def escribir(self, df: pd.DataFrame) -> None:
        tabla = pa.Table.from_pandas(df, preserve_index=False)
        if self.escritor is None:
            # El esquema del archivo queda fijado por la primera parte escrita.
            self.escritor = pq.ParquetWriter(self.temporal, tabla.schema)
        self.escritor.write_table(tabla)

    def __enter__(self):
        return self

    def __exit__(self, tipo_error, *_):
        if self.escritor is not None:
            self.escritor.close()
        if tipo_error is None:
            self.temporal.replace(self.final)
        else:
            self.temporal.unlink(missing_ok=True)


def guardar_tabla(df: pd.DataFrame, carpeta: Path) -> None:
    """Atajo para guardar una tabla completa en una sola parte."""
    with EscritorParquet(carpeta) as out:
        out.escribir(df)
