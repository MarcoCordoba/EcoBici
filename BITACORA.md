# Bitácora del trabajo

Registro cronológico del procedimiento seguido: qué se hizo, con qué comandos y qué
resultó. El enunciado no pide este archivo; las decisiones formales están en
[`DECISIONES.md`](DECISIONES.md).

---

## 2026-10-23 — Preparación del entorno

1. Se creó la estructura de carpetas de la sección 4 del enunciado (`data/raw`, `data/bronze`,
   `data/silver`, `data/gold/reportes`, `src/`).
2. Se extrajo `DatosEcobici.zip` (contenedor con las 6 descargas) en `data/raw/`. Los ZIP de
   recorridos quedaron sin descomprimir.
3. Entorno virtual con Python 3.12.4:
   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install pandas pyarrow
   ```
   Versiones instaladas: pandas 3.1.0, pyarrow 26.0.0 (fijadas en `requirements.txt`).
4. Esqueleto del código: `src/config.py` (rutas y años), un módulo por capa con una función
   `ejecutar()`, y `main.py` que las llama en orden. Se comprobó que `python main.py` corre.
5. `git init` y `.gitignore` que excluye `.venv/` y los datos pesados (solo se versionan los
   reportes de `data/gold/reportes/`).

## 2026-10-23 — Tarea 1: exploración de archivos

1. Se miraron las primeras líneas en binario de cada archivo para ver separador, comillas,
   BOM y fin de línea, y se listó el contenido de cada ZIP con `zipfile`. Cada ZIP tiene un
   solo CSV.
2. Se escribió `src/exploracion.py`, que para cada archivo:
   - detecta separador (`csv.Sniffer`), BOM y fin de línea;
   - lee una muestra con `pd.read_csv(..., dtype=str, nrows=1000)` (directo desde el ZIP);
   - cuenta el total de filas con `chunksize=500_000` leyendo una sola columna, y lo
     compara con las líneas físicas (en los 6 archivos: filas = líneas − 1, así que no
     hay saltos de línea dentro de los campos);
   - muestra ejemplos de fechas, duraciones e ids, y los valores de género.
   ```powershell
   .venv\Scripts\python.exe -m src.exploracion
   ```
   Salida: `docs/exploracion_tarea1.md`.
3. Verificaciones adicionales (comandos sueltos en la consola):
   - Formato de `fecha_alta` 2016: la primera parte llega a 31 y la segunda a 12, por lo
     tanto es `DD-MM-YY`.
   - Duración vs. fin − inicio sobre la muestra: coincide al 100 % en 2019 (quitando la coma
     de miles) y en 2024; en 2016 no coincide en ninguna fila.
   - Usuarios: sin ids nulos ni duplicados en ningún año. Hay edades fuera de rango en 2019
     (0 a 935, 765 nulas) y en 2024 (4 a 2021).
4. Se completaron las tablas de la Tarea 1 en `DECISIONES.md`.

### Hallazgos para tener en cuenta en silver

- **2016 no trae id de viaje ni id de usuario.** Hay que decidir cómo generar `id_viaje`, y
  `id_usuario` va a quedar nulo.
- **2016:** la duración viene como texto timedelta y no coincide con las fechas, así que
  conviene recalcularla desde las fechas.
- **2019:** la duración viene con coma de miles, y los ids traen el sufijo `BAEcobici`.
- **2024:** `id_usuario` viene como decimal (`992557.0`).
- **Nombres de estación:** 2019 y 2024 llevan un prefijo numérico (`005 - `) que 2016 no
  tiene. Esto impacta en `dim_estacion`.
- **Usuarios 2016:** fecha `DD-MM-YY` y hora en 12 h AM/PM. 2019 y 2024 usan `YYYY-MM-DD`
  y 24 h.
- **Género:** 2016 usa `M`/`F`; 2019 y 2024 usan `MALE`/`FEMALE`/`OTHER`, con nulos en 2019.

## 2026-10-23 — Tarea 2: capa Bronze

1. Se revisaron los recursos de la PC: 7,6 GB de RAM. Para no cargar el CSV de 2019
   (1,9 GB) entero en memoria, se decidió leer por partes y escribir el Parquet de a bloques.
2. Se implementó `src/bronze.py`:
   - `elegir_csv_del_zip()`: abre el ZIP con `zipfile` y valida que tenga un único CSV.
   - `leer_por_partes()`: `pd.read_csv(dtype=str, keep_default_na=False, chunksize=500_000)`.
   - `agregar_metadatos()`: agrega `_archivo_origen`, `_fecha_ingesta` y `_anio`.
   - `ingestar_archivo()`: escribe cada bloque con `pyarrow.ParquetWriter` en un `.tmp` y al
     final lo renombra a `data.parquet`.
   - `verificar()`: compara filas, columnas y tipos usando los metadatos del Parquet.
   ```powershell
   .venv\Scripts\python.exe -m src.bronze
   ```
3. Resultado (94 s): las filas de cada año coinciden con las contadas en la Tarea 1.

   | Conjunto | 2016 | 2019 | 2024 |
   |---|---|---|---|
   | Recorridos | 596.807 (12,4 MB) | 6.217.004 (265,8 MB) | 3.559.284 (125,4 MB) |
   | Usuarios | 39.481 (0,5 MB) | 83.600 (1,0 MB) | 197.077 (2,3 MB) |

4. Prueba de idempotencia: se ejecutó la capa dos veces y se comparó un hash del
   contenido de cada Parquet (sin `_fecha_ingesta`, que cambia en cada corrida a propósito).
   Las cantidades de filas y los hashes resultaron idénticos.
5. Controles manuales:
   - Todas las columnas del Parquet son texto.
   - La columna `género` de 2019 conserva bien el acento (UTF-8). La consola de Windows la
     muestra como `g�nero`, pero es solo un problema de visualización.
   - En 2019 hay 1.760 viajes con `id_estacion_destino` vacío (`""`). Quedan así en bronze y
     en silver van a caer en la regla `ESTACION_NULA`.

## 2026-10-23 — Análisis previo a Silver: id de viaje para 2016

Como 2016 no trae id de recorrido, se evaluó generarlo como `2016-<número de fila>`. Se
revisó sobre los Parquet de bronze completos (con pandas, `duplicated()`):

- **Choques entre años:** los ids de 2019 van de 10 a 6.875.895, una vez quitado el sufijo
  `BAEcobici`, y los de 2024 de 20.180.969 a 24.503.283. No hay ids compartidos entre 2019 y
  2024, y el prefijo `2016-` evita choques con los otros dos años.
- **Repetidos dentro de un año:** 2019 no tiene ids repetidos; **2024 tiene 1** (va a ir a
  cuarentena por `DUPLICADO`).
- **Repetidos en 2016 por contenido:** comparando inicio + fin + estaciones aparecieron 9.
  Al inspeccionarlos con `repr()` se vio que **todos tienen la fecha de fin vacía** (`''`):
  no son repetidos reales. Contando solo filas con ambas fechas, hay **0 repetidos**.
- **Hallazgo:** en 2016 hay **93.555 viajes sin fecha de fin** (15,7 % del año). Ninguno
  tiene vacía la fecha de inicio. Van a ir a cuarentena por `FECHA_INVALIDA`.

Conclusión: numerar por fila no hace perder detección de duplicados en 2016, porque entre
los viajes válidos no hay repetidos.

## 2026-10-23 — Tarea 3: capa Silver

### 1. Perfilado previo sobre bronze completo

Antes de programar se midió, en los archivos completos, todo lo que afecta a las decisiones:

| Control | 2016 | 2019 | 2024 |
|---|---|---|---|
| Fechas de inicio vacías / no interpretables | 0 / 0 | 0 / 0 | 0 / 0 |
| Fechas de fin vacías / no interpretables | 93.555 / 0 | 0 / 0 | 3.379 / 0 |
| Ids de estación vacíos o no numéricos (quitando `BAEcobici`) | 0 | 1.760 (destino) | 0 |
| Duración = fin − inicio | 0,04 % | 100 % | 100 % (6 con > 60 s de diferencia) |
| Fin anterior al inicio | 0 | 0 | 0 |
| Viajes de más de 24 h | 0 | 9.048 | 687 |
| Nombres con prefijo numérico (`005 - `) | 0 % | 98,7 % | 100 % |
| Ids de estación con más de un nombre dentro del año | 0 | 0 | 0 |

- Entre 2016 y 2024 hay 69 estaciones con el mismo id. En 44 coincide el nombre (sin prefijo).
  En el resto difiere por tildes (`PACÍFICO`/`PACIFICO`, `GUZMÁN`/`GÚZMAN`), por sufijos
  (`RETIRO`/`RETIRO I`) o porque la estación se renombró (`ZOOLÓGICO`/`ECOPARQUE`).
- Usuarios: todas las fechas de alta se interpretan con el formato de cada año. 2019 trae el
  texto `"NA"` en 765 edades y 857 géneros vacíos. Hay 5.231 ids de usuario repetidos entre
  archivos de años distintos.
- Cruce viajes–usuarios: el 71,1 % de los viajes de 2019 y el 48,1 % de los de 2024 tienen un
  `id_usuario` que no está en ningún archivo de usuarios. Es esperable, porque cada archivo
  trae solo los usuarios dados de alta ese año. Se retoma en gold.

### 2. Implementación (`src/silver.py`)

Organizado en secciones numeradas:
1. Esquemas canónicos (diccionarios columna → tipo).
2. Mapeos que cambian entre años: columnas, formatos de fecha y valores de género.
3. Funciones de limpieza: `vacios_a_nulo`, `renombrar`, `limpiar_id`, `a_entero`, `a_fecha`,
   `normalizar_nombre_estacion`, `normalizar_genero`.
4. `validar_esquema()` y `aplicar_esquema()`.
5. `EscritorParquet`, que escribe por partes en un `.tmp` y lo reemplaza al final.
6. `transformar_viajes()`: pasos 2, 3 y 4 del enunciado para un año.
7. `aplicar_calidad_viajes()`: las 5 reglas en orden, con el primer motivo que falla.
8. Usuarios: `transformar_usuarios()` y `aplicar_calidad_usuarios()`.
9. `verificar()`: conciliación, unicidad y esquemas, leyendo lo que quedó en disco.

```powershell
.venv\Scripts\python.exe -m src.silver
```

### 3. Resultado (270 s)

| Viajes | Bronze | Silver | Cuarentena | Motivos |
|---|---|---|---|---|
| 2016 | 596.807 | 503.252 | 93.555 | FECHA_INVALIDA 93.555 |
| 2019 | 6.217.004 | 6.207.851 | 9.153 | DURACION_MAYOR_24H 7.393, ESTACION_NULA 1.760 |
| 2024 | 3.559.284 | 3.555.217 | 4.067 | FECHA_INVALIDA 3.379, DURACION_MAYOR_24H 687, DUPLICADO 1 |

| Usuarios | Bronze | Silver | Cuarentena | Edades → nulo |
|---|---|---|---|---|
| 2016 | 39.481 | 34.250 | 5.231 (DUPLICADO) | 0 |
| 2019 | 83.600 | 83.600 | 0 | 46 |
| 2024 | 197.077 | 197.077 | 0 | 94 |

La verificación automática pasó: bronze = silver + cuarentena en todos los años, `id_viaje` e
`id_usuario` sin repetidos, y columnas y tipos idénticos al esquema canónico (leídos de disco).

### 4. Revisión manual de resultados

- `viajes.dtypes` coincide exactamente con el esquema del enunciado.
- La estación 14 queda como `PACIFICO` en los tres años (es el ejemplo del enunciado).
- En 2019 se esperaban 9.048 viajes de más de 24 h, pero solo 7.393 tienen ese motivo. La
  diferencia está en viajes sin estación de destino, que caen antes en `ESTACION_NULA`. Por
  ejemplo, un viaje de 18.983.954 s (unos 7 meses) sin destino.
- El `DUPLICADO` de 2024 (id 22425357) es una fila repetida idéntica en el archivo original.
- La duración de 2016 recalculada va de 600 a 10.797 s: el archivo parece contener solo
  viajes de entre 10 minutos y 3 horas.
- Usuarios duplicados: son ids de 2016 que reaparecen en 2019 con otra fecha de alta. Solo
  el 38,8 % coincide en género, así que probablemente el sistema de 2019 reutilizó ids. Se
  dejó registrado como limitación en `DECISIONES.md`. Todas esas altas de 2019 son de mayo
  (1.673) o junio (3.558).

### 5. Idempotencia

Se ejecutó silver dos veces y se comparó un hash del contenido de las 4 tablas: resultaron
idénticas.

| Tabla | Filas |
|---|---|
| `viajes` | 10.266.320 |
| `viajes_cuarentena` | 106.775 |
| `usuarios` | 314.927 |
| `usuarios_cuarentena` | 5.231 |

## 2026-10-23 — Tarea 4: capa Gold

### 1. Controles previos sobre silver

- Año de `fecha_hora_inicio` vs. `anio_fuente`: coinciden en el 100 % de los viajes. Rangos:
  2016 del 01/01 al 26/12, 2019 del 17/02 al 31/12 y 2024 del 01/01 al 31/12.
- Cada id de estación tiene un solo nombre por año, juntando origen y destino. Hay 532
  estaciones distintas y todas aparecen al menos una vez como origen.
- Viajes con `id_usuario` que no está en silver/usuarios: 6.120.635 de 9.763.068 (los que
  traen id).

### 2. Refactor

El escritor idempotente de Parquet se movió de `silver.py` a `src/io_parquet.py`
(`EscritorParquet` y `guardar_tabla`) para usarlo también en gold. Se volvió a correr silver
completo: la verificación pasó igual.

### 3. Implementación (`src/gold.py`)

- `construir_dim_fecha()`: calendario 1/1–31/12 de cada año con viajes, con día de la semana
  en español y marca de fin de semana.
- `construir_dim_estacion()`: apila origen y destino, cuenta apariciones por
  (id, nombre, año) y elige el nombre del año más reciente (desempata por frecuencia).
- `construir_dim_usuario()`: agrega `rango_etario` y `anio_alta`.
- `construir_fact_viajes()`: `fecha_key`, `hora_inicio`, `duracion_min` y `es_circular`.
- `verificar()`: comprueba filas de fact = silver, integridad referencial con dim_fecha y
  dim_estacion, y claves únicas en las dimensiones; además cuenta los viajes cuyo usuario no
  está en dim_usuario.

```powershell
.venv\Scripts\python.exe -m src.gold
```

### 4. Resultado

| Tabla | Filas |
|---|---|
| `dim_fecha` | 1.097 (366 + 365 + 366) |
| `dim_estacion` | 532 |
| `dim_usuario` | 314.927 |
| `fact_viajes` | 10.266.320 (= silver/viajes) |

- Verificación OK: todas las `fecha_key` y todos los ids de estación existen en sus dimensiones.
- Viajes con `id_usuario` fuera de dim_usuario: 4.410.500 en 2019 y 1.710.135 en 2024
  (411.270 usuarios distintos). Explicación en `DECISIONES.md`.
- Controles manuales:
  - `20190315` → viernes, no es fin de semana (coincide con el ejemplo del enunciado).
  - Estación 14 → `PACIFICO`, 2016–2024.
  - Estación 44 → `ECOPARQUE`, que era `ZOOLOGICO` en 2016.
  - El primer viaje de 2016 dura 26,4 min, recalculado desde las fechas.
- Rango etario: 16-25 → 106.906; 26-35 → 104.019; 36-50 → 73.608; 51+ → 29.489;
  DESCONOCIDO → 905.
- El 11,43 % de los viajes son circulares.
- Se corrigió un aviso de pandas 3: `dt.dayofweek` está deprecado y se reemplazó por
  `dt.day_of_week`.

### 5. Idempotencia

Se ejecutó gold dos veces y se comparó el hash de las 4 tablas: resultaron idénticas.

## 2026-10-23 — Tarea 5: reportes

### 1. Implementación (`src/reportes.py`)

Una función por reporte:
- `reporte_viajes_por_mes`: parte de `dim_fecha`, para que los meses sin viajes salgan con 0.
- `reporte_top10_estaciones`: cuenta por id de estación de origen.
- `reporte_duracion_por_rango_y_genero`: join interno con `dim_usuario`.
- `reporte_viajes_circulares`.
- `reporte_calidad_por_anio`: el único que lee bronze (metadatos) y silver.

Además, `verificar()` controla que los totales de los reportes cierren con `fact_viajes` antes
de guardar los CSV en `data/gold/reportes/` (con codificación `utf-8-sig`).

### 2. Problema detectado al revisar los resultados

En la primera corrida, el top 10 de 2016 incluía las estaciones `ERRONEA` y `KP1808000368`.
Al investigar:

| id | Nombre 2016 | Nombre 2019 | Dirección 2019 |
|---|---|---|---|
| 1 | FACULTAD DE DERECHO | ERRONEA | Av. Pres. Figueroa Alcorta 2120 |
| 10 | PUERTO MADERO - UCA | KP1808000368 | 1600 Moreau De Justo, Alicia Av. |
| 300 | — | 175 | Cramer 4500 |
| 350 | — | 234 | Av. Triunvirato 5752 |

La regla de "nombre más reciente" de `dim_estacion` tomaba valores que no son nombres.

**Corrección:**
- **Silver:** `normalizar_nombre_estacion()` pasa a nulo los nombres `ERRONEA`, `KP<números>`
  y los solo numéricos. Afecta a 26.481 nombres de origen y 30.528 de destino, todos de 2019.
- **Gold:** `dim_estacion` toma el nombre válido más reciente. Si nunca hubo uno, queda
  `DESCONOCIDA`: son 2 estaciones, la 300 y la 350.

Esto es limpieza de valores, así que se hizo en silver y no en gold, como indica el
enunciado.

### 3. Ejecución completa con `python main.py`

Se agregó a `main.py` la medición del tiempo de cada capa y se corrió el pipeline desde
cero, de bronze a reportes:

| Capa | Tiempo |
|---|---|
| bronze | 93 s |
| silver | 264 s |
| gold | 16 s |
| reportes | 14 s |
| **Total** | **387 s** |

Todas las verificaciones pasaron. Tamaño en disco: bronze 408 MB, silver 308 MB, gold 140 MB.

### 4. Resultados principales

| Reporte | Contenido |
|---|---|
| `viajes_por_mes.csv` | 36 filas (12 meses × 3 años). Enero 2019 = 0 viajes |
| `top10_estaciones_por_anio.csv` | 30 filas. Solo `PACIFICO`, `CONGRESO` y `PLAZA ITALIA` están en el top de los tres años |
| `duracion_por_rango_y_genero.csv` | 20 combinaciones, 3.642.433 viajes con usuario conocido |
| `viajes_circulares.csv` | 2016: 12,1 % · 2019: 10,2 % · 2024: 13,5 % |
| `calidad_por_anio.csv` | Cuarentena 2016: 15,68 % · 2019: 0,15 % · 2024: 0,11 % |

- Se verificó a mano que la suma del reporte 3 sea igual a viajes − viajes sin id − viajes con
  id fuera de `dim_usuario` (10.266.320 − 503.252 − 6.120.635 = 3.642.433).
- Los rankings se compararon por id. `FACULTAD DE DERECHO` de 2016 (id 1) y la de 2024
  (id 202) son estaciones distintas con el mismo nombre.
