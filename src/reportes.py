"""Reportes: tablas de resultados en CSV a partir del modelo estrella de gold.

Regla del enunciado: los reportes 1 a 4 se arman SOLO con tablas de gold. El
reporte 5 (calidad) es la única excepción: necesita los conteos de bronze, silver
y cuarentena.

Salida en data/gold/reportes/:
    viajes_por_mes.csv
    top10_estaciones_por_anio.csv
    duracion_por_rango_y_genero.csv
    viajes_circulares.csv
    calidad_por_anio.csv
"""
import pandas as pd
import pyarrow.parquet as pq

from src import config
from src.gold import RANGOS_ETARIOS

# utf-8-sig agrega una marca (BOM) al inicio del archivo para que Excel en Windows
# reconozca el UTF-8 y muestre bien caracteres como la Ñ. pandas la lee sin problemas.
ENCODING_CSV = "utf-8-sig"

# Orden lógico de los rangos etarios para el reporte 3 (y no alfabético).
ORDEN_RANGOS = [etiqueta for _, _, etiqueta in RANGOS_ETARIOS] + ["DESCONOCIDO"]
ORDEN_GENEROS = ["F", "M", "OTRO", "DESCONOCIDO"]


def leer_gold(tabla: str, columnas: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(config.GOLD / tabla / "data.parquet", columns=columnas)


def guardar_reporte(df: pd.DataFrame, nombre: str) -> None:
    """Guarda un CSV en data/gold/reportes/ (si ya existe, se reemplaza)."""
    config.REPORTES.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.REPORTES / nombre, index=False, encoding=ENCODING_CSV)
    print(f"[reportes] {nombre}: {len(df)} filas")


# ===========================================================================
# Reporte 1: cantidad de viajes por año y mes
# ===========================================================================

def reporte_viajes_por_mes(fact: pd.DataFrame, dim_fecha: pd.DataFrame) -> pd.DataFrame:
    """Viajes por año y mes.

    Se parte de dim_fecha (y no de los viajes) para que los meses sin viajes
    aparezcan con 0 en lugar de desaparecer (por ejemplo, enero de 2019).
    """
    viajes_por_dia = fact.groupby("fecha_key").size().rename("cantidad_viajes")
    por_dia = dim_fecha[["fecha_key", "anio", "mes"]].join(viajes_por_dia, on="fecha_key")
    return (por_dia.fillna({"cantidad_viajes": 0})
                   .groupby(["anio", "mes"], as_index=False)["cantidad_viajes"].sum()
                   .astype({"cantidad_viajes": "int64"}))


# ===========================================================================
# Reporte 2: top 10 de estaciones de origen por año
# ===========================================================================

def reporte_top10_estaciones(fact: pd.DataFrame, dim_fecha: pd.DataFrame,
                             dim_estacion: pd.DataFrame) -> pd.DataFrame:
    """Las 10 estaciones con más viajes iniciados en cada año.

    - Se cuenta por id de estación (la clave), no por nombre.
    - El nombre es el de dim_estacion (el más reciente), así una misma estación
      se reconoce con el mismo nombre en los tres años.
    - Empates: se ordena por cantidad desc. y luego por id asc., y el ranking es
      correlativo (1 a 10) para que haya exactamente 10 filas por año.
    """
    viajes = fact[["fecha_key", "id_estacion_origen"]].merge(
        dim_fecha[["fecha_key", "anio"]], on="fecha_key", validate="many_to_one")

    conteo = (viajes.groupby(["anio", "id_estacion_origen"]).size()
                    .rename("cantidad_viajes").reset_index()
                    .sort_values(["anio", "cantidad_viajes", "id_estacion_origen"],
                                 ascending=[True, False, True]))
    conteo["ranking"] = conteo.groupby("anio").cumcount() + 1
    top = conteo[conteo["ranking"] <= 10]

    top = top.merge(dim_estacion[["id_estacion", "nombre_estacion"]],
                    left_on="id_estacion_origen", right_on="id_estacion",
                    validate="many_to_one")
    return top[["anio", "ranking", "nombre_estacion", "cantidad_viajes"]].reset_index(drop=True)


# ===========================================================================
# Reporte 3: duración promedio por rango etario y género
# ===========================================================================

def reporte_duracion_por_rango_y_genero(fact: pd.DataFrame,
                                        dim_usuario: pd.DataFrame) -> pd.DataFrame:
    """Duración promedio (minutos) según rango etario y género del usuario.

    Solo entran los viajes cuyo id_usuario está en dim_usuario (join interno):
    los demás no tienen edad ni género conocidos. Ver DECISIONES.md.
    """
    viajes = fact[["id_usuario", "duracion_min"]].merge(
        dim_usuario[["id_usuario", "rango_etario", "genero"]],
        on="id_usuario", how="inner", validate="many_to_one")

    rep = (viajes.groupby(["rango_etario", "genero"], as_index=False)
                 .agg(cantidad_viajes=("duracion_min", "size"),
                      duracion_promedio_min=("duracion_min", "mean")))
    rep["duracion_promedio_min"] = rep["duracion_promedio_min"].astype(float).round(1)

    # Orden lógico: rangos de menor a mayor edad y géneros en un orden fijo.
    rep["rango_etario"] = pd.Categorical(rep["rango_etario"], ORDEN_RANGOS, ordered=True)
    rep["genero"] = pd.Categorical(rep["genero"], ORDEN_GENEROS, ordered=True)
    return rep.sort_values(["rango_etario", "genero"]).reset_index(drop=True)


# ===========================================================================
# Reporte 4: porcentaje de viajes circulares por año
# ===========================================================================

def reporte_viajes_circulares(fact: pd.DataFrame, dim_fecha: pd.DataFrame) -> pd.DataFrame:
    """Viajes que terminan en la misma estación donde empezaron, por año."""
    viajes = fact[["fecha_key", "es_circular"]].merge(
        dim_fecha[["fecha_key", "anio"]], on="fecha_key", validate="many_to_one")

    rep = (viajes.groupby("anio", as_index=False)
                 .agg(total_viajes=("es_circular", "size"),
                      viajes_circulares=("es_circular", "sum")))
    rep["porcentaje_circulares"] = (100 * rep["viajes_circulares"] / rep["total_viajes"]).round(1)
    return rep


# ===========================================================================
# Reporte 5: calidad de datos por año (excepción: usa bronze y silver)
# ===========================================================================

def filas_por_anio_silver(tabla: str) -> pd.Series:
    """Filas por anio_fuente de una tabla de silver (lee solo esa columna)."""
    anios = pd.read_parquet(config.SILVER / tabla / "data.parquet", columns=["anio_fuente"])
    return anios["anio_fuente"].value_counts()


def reporte_calidad_por_anio() -> pd.DataFrame:
    """Filas de bronze, silver y cuarentena de los viajes, por año de origen.

    Las filas de bronze se leen de los metadatos de cada Parquet (sin cargar datos).
    """
    silver = filas_por_anio_silver("viajes")
    cuarentena = filas_por_anio_silver("viajes_cuarentena")

    filas = []
    for anio in config.ANIOS:
        ruta = config.BRONZE / "recorridos" / f"anio={anio}" / "data.parquet"
        filas.append({
            "anio": anio,
            "filas_bronze": pq.ParquetFile(ruta).metadata.num_rows,
            "filas_silver": int(silver.get(anio, 0)),
            "filas_cuarentena": int(cuarentena.get(anio, 0)),
        })
    rep = pd.DataFrame(filas)
    rep["porcentaje_cuarentena"] = (100 * rep["filas_cuarentena"] / rep["filas_bronze"]).round(2)
    return rep


# ===========================================================================
# Verificación de consistencia entre reportes
# ===========================================================================

def verificar(reportes: dict[str, pd.DataFrame], total_viajes: int, viajes_con_usuario: int) -> None:
    """Controles cruzados: los totales de los reportes deben cerrar con gold."""
    if reportes["viajes_por_mes"]["cantidad_viajes"].sum() != total_viajes:
        raise AssertionError("Reporte 1: la suma de viajes por mes no coincide con fact_viajes")
    if reportes["viajes_circulares"]["total_viajes"].sum() != total_viajes:
        raise AssertionError("Reporte 4: el total de viajes no coincide con fact_viajes")
    if reportes["duracion_por_rango_y_genero"]["cantidad_viajes"].sum() != viajes_con_usuario:
        raise AssertionError("Reporte 3: no coincide con los viajes que cruzan con dim_usuario")
    if (reportes["top10_estaciones_por_anio"].groupby("anio").size() != 10).any():
        raise AssertionError("Reporte 2: algún año no tiene 10 estaciones")

    calidad = reportes["calidad_por_anio"]
    if not (calidad["filas_bronze"] == calidad["filas_silver"] + calidad["filas_cuarentena"]).all():
        raise AssertionError("Reporte 5: bronze != silver + cuarentena")
    if calidad["filas_silver"].sum() != total_viajes:
        raise AssertionError("Reporte 5: las filas de silver no coinciden con fact_viajes")
    print("[reportes] verificación OK: los totales cierran con fact_viajes")


# ===========================================================================
# Punto de entrada
# ===========================================================================

def ejecutar() -> dict[str, pd.DataFrame]:
    fact = leer_gold("fact_viajes", ["fecha_key", "id_estacion_origen", "id_usuario",
                                     "duracion_min", "es_circular"])
    dim_fecha = leer_gold("dim_fecha")
    dim_estacion = leer_gold("dim_estacion")
    dim_usuario = leer_gold("dim_usuario")

    reportes = {
        "viajes_por_mes": reporte_viajes_por_mes(fact, dim_fecha),
        "top10_estaciones_por_anio": reporte_top10_estaciones(fact, dim_fecha, dim_estacion),
        "duracion_por_rango_y_genero": reporte_duracion_por_rango_y_genero(fact, dim_usuario),
        "viajes_circulares": reporte_viajes_circulares(fact, dim_fecha),
        "calidad_por_anio": reporte_calidad_por_anio(),
    }

    viajes_con_usuario = int(fact["id_usuario"].isin(dim_usuario["id_usuario"]).sum())
    verificar(reportes, len(fact), viajes_con_usuario)

    for nombre, df in reportes.items():
        guardar_reporte(df, f"{nombre}.csv")
    return reportes


if __name__ == "__main__":
    ejecutar()
