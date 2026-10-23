"""Tarea 1: exploración de los archivos originales.

No forma parte del pipeline (main.py no lo ejecuta). Se corre a mano con:

    python -m src.exploracion

Lee cada archivo de data/raw/ tal cual viene (sin descomprimir a disco) y deja
el resultado en docs/exploracion_tarea1.md, que sirve de respaldo para la
tabla de DECISIONES.md.
"""
import csv
import io
import zipfile
from pathlib import Path

import pandas as pd

from src import config

SALIDA = config.RAIZ / "docs" / "exploracion_tarea1.md"
NROWS = 1000
CHUNK = 500_000


def nombre_csv_en_zip(ruta: Path) -> str:
    """Devuelve el nombre del único CSV dentro del ZIP (falla si hay otro número)."""
    with zipfile.ZipFile(ruta) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(csvs) != 1:
        raise ValueError(f"{ruta.name}: se esperaba 1 CSV y hay {csvs}")
    return csvs[0]


def abrir_binario(ruta: Path):
    """Abre el CSV crudo en binario, venga suelto o dentro de un ZIP."""
    if ruta.suffix == ".zip":
        zf = zipfile.ZipFile(ruta)
        return zf.open(nombre_csv_en_zip(ruta))
    return open(ruta, "rb")


def detectar_formato(ruta: Path) -> dict:
    """Separador, BOM y fin de línea, mirando los primeros bytes del archivo."""
    with abrir_binario(ruta) as f:
        muestra = f.read(64 * 1024)
    tiene_bom = muestra.startswith(b"\xef\xbb\xbf")
    texto = muestra.decode("utf-8-sig", errors="replace")
    separador = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;").delimiter
    fin_linea = "CRLF" if b"\r\n" in muestra else "LF"
    return {"separador": separador, "bom": tiene_bom, "fin_linea": fin_linea}


def leer_muestra(ruta: Path, sep: str) -> pd.DataFrame:
    kwargs = {"compression": "zip"} if ruta.suffix == ".zip" else {}
    return pd.read_csv(ruta, sep=sep, dtype=str, nrows=NROWS, **kwargs)


def contar_filas(ruta: Path, sep: str) -> int:
    """Cuenta filas de datos con pandas, por partes, leyendo una sola columna."""
    kwargs = {"compression": "zip"} if ruta.suffix == ".zip" else {}
    total = 0
    for parte in pd.read_csv(ruta, sep=sep, dtype=str, usecols=[0],
                             chunksize=CHUNK, **kwargs):
        total += len(parte)
    return total


def contar_lineas(ruta: Path) -> int:
    """Líneas físicas del archivo (sirve para detectar saltos de línea dentro de campos)."""
    with abrir_binario(ruta) as f:
        return sum(1 for _ in io.BufferedReader(f))


def columnas_con(df: pd.DataFrame, *claves: str) -> list[str]:
    return [c for c in df.columns if any(k in c.lower() for k in claves)]


def describir(ruta: Path, anio: int, tipo: str) -> list[str]:
    print(f"Explorando {ruta.name} ...")
    fmt = detectar_formato(ruta)
    df = leer_muestra(ruta, fmt["separador"])
    filas = contar_filas(ruta, fmt["separador"])
    lineas = contar_lineas(ruta)

    lineas_md = [f"### {tipo} {anio} — `{ruta.name}`", ""]
    if ruta.suffix == ".zip":
        lineas_md.append(f"- Archivo dentro del ZIP: `{nombre_csv_en_zip(ruta)}`")
    lineas_md += [
        f"- Separador: `{fmt['separador']}` | BOM UTF-8: {fmt['bom']} | Fin de línea: {fmt['fin_linea']}",
        f"- Filas de datos (pandas): **{filas:,}** | Líneas físicas: {lineas:,}",
        f"- Columnas ({len(df.columns)}): " + ", ".join(f"`{c}`" for c in df.columns),
        "",
        "Primeras 3 filas:",
        "",
        "```",
        df.head(3).T.to_string(),
        "```",
        "",
    ]

    for col in columnas_con(df, "fecha", "hora"):
        ejemplos = df[col].dropna().unique()[:3]
        lineas_md.append(f"- Ejemplos `{col}`: " + ", ".join(f"`{e}`" for e in ejemplos))
    for col in columnas_con(df, "duracion"):
        ejemplos = df[col].dropna().unique()[:5]
        lineas_md.append(f"- Ejemplos `{col}`: " + ", ".join(f"`{e}`" for e in ejemplos))
    for col in [c for c in df.columns if c.lower().startswith("id")]:
        ejemplos = df[col].dropna().unique()[:3]
        nulos = df[col].isna().sum()
        lineas_md.append(f"- Ejemplos `{col}` (nulos en muestra: {nulos}): "
                         + ", ".join(f"`{e}`" for e in ejemplos))
    for col in columnas_con(df, "genero", "género", "edad"):
        if "edad" in col.lower():
            edades = pd.to_numeric(df[col], errors="coerce")
            lineas_md.append(f"- `{col}` en muestra: min={edades.min()}, max={edades.max()}, "
                             f"nulos={df[col].isna().sum()}")
        else:
            conteo = df[col].value_counts(dropna=False).to_dict()
            lineas_md.append(f"- Valores de `{col}` en muestra: {conteo}")
    lineas_md.append("")
    return lineas_md


def generos_completos(ruta: Path, sep: str) -> dict:
    """value_counts del género sobre el archivo completo de usuarios (es chico)."""
    df = pd.read_csv(ruta, sep=sep, dtype=str)
    col = columnas_con(df, "genero", "género")[0]
    return df[col].value_counts(dropna=False).to_dict()


def main() -> None:
    texto = ["# Tarea 1 — Exploración de archivos (salida de `python -m src.exploracion`)", "",
             f"Muestra leída con `nrows={NROWS}`; las filas totales se cuentan por partes "
             f"(`chunksize={CHUNK:,}`).", "", "## Recorridos", ""]
    for anio in config.ANIOS:
        texto += describir(config.ARCHIVOS_RECORRIDOS[anio], anio, "Recorridos")

    texto += ["## Usuarios", ""]
    for anio in config.ANIOS:
        ruta = config.ARCHIVOS_USUARIOS[anio]
        texto += describir(ruta, anio, "Usuarios")
        sep = detectar_formato(ruta)["separador"]
        texto += [f"- Valores de género en el archivo **completo**: {generos_completos(ruta, sep)}", ""]

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(texto), encoding="utf-8")
    print(f"Resultado escrito en {SALIDA}")


if __name__ == "__main__":
    main()
