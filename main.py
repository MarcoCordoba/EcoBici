"""Ejecuta el pipeline completo: bronze -> silver -> gold -> reportes.

    python main.py

Cada capa lee únicamente lo que dejó la anterior y reemplaza su propia salida,
así que el pipeline se puede correr las veces que haga falta con el mismo resultado.
"""
import time

from src import bronze, silver, gold, reportes

CAPAS = [
    ("bronze", bronze.ejecutar),
    ("silver", silver.ejecutar),
    ("gold", gold.ejecutar),
    ("reportes", reportes.ejecutar),
]


def main() -> None:
    inicio_total = time.perf_counter()
    for nombre, ejecutar in CAPAS:
        print(f"\n=== {nombre.upper()} ===")
        inicio = time.perf_counter()
        ejecutar()
        print(f"--- {nombre} terminado en {time.perf_counter() - inicio:,.0f} s")
    print(f"\nPipeline completo en {time.perf_counter() - inicio_total:,.0f} s")


if __name__ == "__main__":
    main()
