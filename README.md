# Pipeline Ecobici (Bronze / Silver / Gold)

**Autor:** Marco Cordoba
**Repositorio:** https://github.com/MarcoCordoba/EcoBici

Pipeline de datos sobre los viajes del sistema Ecobici (CABA) de los años 2016, 2019 y 2024,
organizado con la arquitectura medallion. Parte de los archivos tal como los publica el
portal de datos abiertos y termina en un modelo estrella y cinco reportes en CSV.

## Requisitos

- **Python 3.12** (probado con 3.12.4)
- Librerías en `requirements.txt`: **pandas 3.1.0** y **pyarrow 26.0.0**
- Unos 8 GB de RAM: los archivos grandes se leen por partes
- Unos 2 GB de disco libre para las capas generadas

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Datos de entrada

Descargar del portal https://data.buenosaires.gob.ar/dataset/bicicletas-publicas y colocar
**sin descomprimir ni modificar** en `data/raw/`:

| Año  | Recorridos (ZIP)                 | Usuarios (CSV)               |
|------|----------------------------------|------------------------------|
| 2016 | `recorridos-realizados-2016.zip` | `usuarios-ecobici-2016.csv`  |
| 2019 | `recorridos-realizados-2019.zip` | `usuarios_ecobici_2019.csv`  |
| 2024 | `recorridos-realizados-2024.zip` | `usuarios_ecobici_2024.csv`  |

Los nombres esperados están en `src/config.py`.

## Ejecución

```powershell
python main.py
```

Corre todo el pipeline, de bronze a los reportes, sin pasos manuales. Tarda unos 6 a 7 minutos: bronze ~95 s, silver ~265 s, gold ~15 s y reportes ~15 s.
Cada capa verifica sus resultados y detiene la ejecución si algo no cierra. El pipeline es
idempotente: se puede ejecutar varias veces y siempre deja el mismo resultado.

Cada capa también se puede correr sola, siempre que exista la anterior:
`python -m src.bronze`, `python -m src.silver`, `python -m src.gold`, `python -m src.reportes`.

La exploración de la Tarea 1 no forma parte del pipeline y se corre aparte:
`python -m src.exploracion`, que escribe `docs/exploracion_tarea1.md`.

## Estructura

```
ecobici-pipeline/
├── data/
│   ├── raw/                 archivos originales (sin tocar)
│   ├── bronze/              copia fiel en Parquet: todo texto + metadatos de ingesta
│   │   ├── recorridos/anio=AAAA/data.parquet
│   │   └── usuarios/anio=AAAA/data.parquet
│   ├── silver/              esquema canónico, tipado y validado
│   │   ├── viajes/  viajes_cuarentena/  usuarios/  usuarios_cuarentena/
│   └── gold/                modelo estrella
│       ├── dim_fecha/  dim_estacion/  dim_usuario/  fact_viajes/
│       └── reportes/        los 5 CSV de resultados
├── src/
│   ├── config.py            rutas, años y nombres de archivos
│   ├── io_parquet.py        escritura idempotente de Parquet (silver y gold)
│   ├── bronze.py            Tarea 2
│   ├── silver.py            Tarea 3
│   ├── gold.py              Tarea 4
│   ├── reportes.py          Tarea 5
│   └── exploracion.py       Tarea 1 (no forma parte del pipeline)
├── docs/exploracion_tarea1.md
├── main.py                  orquestador
├── DECISIONES.md            diferencias entre años, mapeos y decisiones justificadas
├── BITACORA.md              registro paso a paso del trabajo realizado
└── requirements.txt
```

## Documentación

- **`DECISIONES.md`**: tabla de diferencias entre años (Tarea 1), mapeo de columnas y de
  género, y cada decisión no indicada por el enunciado con su justificación.
- **`BITACORA.md`**: qué se hizo, en qué orden, con qué comandos y qué resultados se obtuvieron.
