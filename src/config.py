"""Rutas y parámetros compartidos por todas las capas del pipeline."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
RAW = DATA / "raw"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
REPORTES = GOLD / "reportes"

ANIOS = [2016, 2019, 2024]

ARCHIVOS_RECORRIDOS = {
    2016: RAW / "recorridos-realizados-2016.zip",
    2019: RAW / "recorridos-realizados-2019.zip",
    2024: RAW / "recorridos-realizados-2024.zip",
}

ARCHIVOS_USUARIOS = {
    2016: RAW / "usuarios-ecobici-2016.csv",
    2019: RAW / "usuarios_ecobici_2019.csv",
    2024: RAW / "usuarios_ecobici_2024.csv",
}
