# Decisiones del pipeline

## 1. Exploración de archivos (Tarea 1)

Generado con `python -m src.exploracion` (muestra con `nrows=1000`; el total de filas se
contó leyendo cada archivo completo por partes). La salida detallada está en
[`docs/exploracion_tarea1.md`](docs/exploracion_tarea1.md).

### Recorridos

| Aspecto a revisar | 2016 | 2019 | 2024 |
|---|---|---|---|
| Nombre del archivo dentro del ZIP | `recorridos-realizados-2016.csv` | `trips_2019.csv` | `badata_ecobici_recorridos_realizados_2024.csv` |
| Separador de columnas | `,` | `,` | `,` (archivo con BOM UTF-8, fin de línea LF) |
| Nombres de las columnas (15 / 18 / 17) | `periodo`, `genero_usuario`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `domicilio_estacion_origen`, `duracion_recorrido`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `domicilio_estacion_destino` | columna sin nombre (`""`, índice 1..n), `Id_recorrido`, `duracion_recorrido`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `direccion_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `direccion_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `id_usuario`, `modelo_bicicleta`, `género` | `id_recorrido`, `duracion_recorrido`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `direccion_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `direccion_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `id_usuario`, `modelo_bicicleta`, `genero` |
| Formato de fecha y hora | `YYYY-MM-DD HH:MM:SS` | `YYYY-MM-DD HH:MM:SS` | `YYYY-MM-DD HH:MM:SS` |
| ¿Trae la duración? ¿En qué unidad? | Sí, como timedelta de texto (`0 days 00:16:29.000000000`). **No coincide** con fin − inicio (0 % de coincidencia en la muestra) | Sí, en segundos, con coma de miles (`2,814` = 2814 s). Coincide con fin − inicio | Sí, en segundos enteros (`568`). Coincide con fin − inicio |
| ¿Trae id de usuario? | **No** (solo `genero_usuario`). Tampoco trae id de recorrido | Sí, con sufijo: `6243BAEcobici` | Sí, como decimal: `992557.0` |
| Cantidad total de filas | 596.807 | 6.217.004 | 3.559.284 |

Otras diferencias detectadas en recorridos:

- **Ids con sufijo en 2019:** `Id_recorrido`, `id_estacion_*` e `id_usuario` traen el sufijo `BAEcobici` (`5BAEcobici`).
- **Nombres de estación:** en 2016 son nombres sueltos (`Tribunales`); en 2019 y 2024 llevan un número adelante (`005 - Plaza Italia`) y en 2024 se mezclan mayúsculas y minúsculas (`055 - HABANA`, `204 - Biarritz`).
- **Coordenadas corridas en 2019:** en el destino, `long_estacion_destino` contiene la latitud y `lat_estacion_destino` contiene `"lat,long"`. Las coordenadas no forman parte del esquema canónico, pero queda registrado.
- **Encabezados:** 2019 entrecomilla todos los campos y su primera columna no tiene nombre (pandas la lee como `Unnamed: 0`).
- **Columnas que solo aparecen en algunos años:** `periodo` (2016), `modelo_bicicleta` (2019, 2024), género del usuario dentro del archivo de viajes (los tres años, con nombre distinto: `genero_usuario` / `género` / `genero`).

### Usuarios

| Aspecto a revisar | 2016 | 2019 | 2024 |
|---|---|---|---|
| Nombre del archivo | `usuarios-ecobici-2016.csv` | `usuarios_ecobici_2019.csv` | `usuarios_ecobici_2024.csv` |
| Separador de columnas | `,` | `,` (todos los campos entre comillas) | `,` (BOM UTF-8, fin de línea LF) |
| Nombres de las columnas | `id_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta` | `ID_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta` | `id_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta` |
| Formato de fecha de alta | `DD-MM-YY` (`31-12-16`) | `YYYY-MM-DD` | `YYYY-MM-DD` |
| Formato de hora de alta | 12 h con AM/PM (`3:45:19 AM`) | 24 h (`10:46:10`) | 24 h (`09:21:02`) |
| Valores de género (archivo completo) | `M` 21.697, `F` 17.784 | `MALE` 41.107, `FEMALE` 24.285, `OTHER` 17.351, nulo 857 | `MALE` 88.655, `FEMALE` 79.310, `OTHER` 29.112 |
| Edad (archivo completo) | 16 a 88, sin nulos | 0 a 935; 765 nulos; 31 < 16 y 15 > 90 | 4 a 2021; sin nulos; 9 < 16 y 85 > 90 |
| Ids duplicados / nulos | 0 / 0 | 0 / 0 | 0 / 0 |
| Cantidad total de filas | 39.481 | 83.600 | 197.077 |

Notas:

- La fecha de alta de 2016 es `DD-MM-YY` y no `MM-DD-YY`: la primera parte llega hasta 31 y la segunda hasta 12.
- La fecha y la hora de alta vienen en dos columnas separadas en los tres años; en silver se unen en `fecha_alta`.

## 2. Mapeo de columnas

Definido en `src/silver.py` (`MAPEO_VIAJES`, `MAPEO_USUARIOS`). Las columnas originales
que no figuran se descartan en silver (siguen disponibles en bronze).

### Viajes

| Columna canónica | 2016 | 2019 | 2024 | Transformación |
|---|---|---|---|---|
| `id_viaje` | — (se genera `2016-NNNNNN`) | `Id_recorrido` | `id_recorrido` | Se quita el sufijo `BAEcobici` |
| `fecha_hora_inicio` | `fecha_origen_recorrido` | `fecha_origen_recorrido` | `fecha_origen_recorrido` | `to_datetime(format="%Y-%m-%d %H:%M:%S")` |
| `fecha_hora_fin` | `fecha_destino_recorrido` | `fecha_destino_recorrido` | `fecha_destino_recorrido` | ídem |
| `duracion_seg` | — (se calcula fin − inicio) | `duracion_recorrido` | `duracion_recorrido` | 2019: se quita la coma de miles |
| `id_estacion_origen` | `id_estacion_origen` | `id_estacion_origen` | `id_estacion_origen` | Se quita `BAEcobici` → `Int64` |
| `nombre_estacion_origen` | `nombre_estacion_origen` | `nombre_estacion_origen` | `nombre_estacion_origen` | Normalización (ver §4) |
| `id_estacion_destino` | `id_estacion_destino` | `id_estacion_destino` | `id_estacion_destino` | Se quita `BAEcobici` → `Int64` |
| `nombre_estacion_destino` | `nombre_estacion_destino` | `nombre_estacion_destino` | `nombre_estacion_destino` | Normalización (ver §4) |
| `id_usuario` | — (nulo) | `id_usuario` | `id_usuario` | 2019: se quita `BAEcobici`; 2024: se quita `.0` |
| `anio_fuente` | 2016 | 2019 | 2024 | Año del archivo de origen |

Columnas descartadas: `periodo`, `genero_usuario`/`género`/`genero` (el género del viaje no
está en el esquema canónico; el género se toma de la tabla de usuarios), coordenadas,
domicilio/dirección de estaciones, `modelo_bicicleta` y la columna índice sin nombre de 2019.

### Usuarios

| Columna canónica | 2016 | 2019 | 2024 | Transformación |
|---|---|---|---|---|
| `id_usuario` | `id_usuario` | `ID_usuario` | `id_usuario` | Misma limpieza de id que en viajes |
| `genero` | `genero_usuario` | `genero_usuario` | `genero_usuario` | Mapeo de género (§3) |
| `edad` | `edad_usuario` | `edad_usuario` | `edad_usuario` | `Int64`; fuera de [16, 90] → nulo |
| `fecha_alta` | `fecha_alta` + `hora_alta` | `fecha_alta` + `hora_alta` | `fecha_alta` + `hora_alta` | 2016: `%d-%m-%y %I:%M:%S %p`; 2019/2024: `%Y-%m-%d %H:%M:%S` |
| `anio_fuente` | 2016 | 2019 | 2024 | Año del archivo de origen |

## 3. Mapeo de valores de género

Valores encontrados con `value_counts()` sobre los archivos completos de usuarios:

| Valor original | Años en que aparece | Valor en silver |
|---|---|---|
| `F` | 2016 | `F` |
| `FEMALE` | 2019, 2024 | `F` |
| `M` | 2016 | `M` |
| `MALE` | 2019, 2024 | `M` |
| `OTHER` | 2019, 2024 | `OTRO` |
| vacío (857 en 2019) o cualquier otro | 2019 | `DESCONOCIDO` |

Antes de mapear se pasa a mayúsculas, así que variantes como `Female` también quedarían
cubiertas.

## 4. Otras decisiones

### Datos de entrada

- **Origen de los datos crudos:** los 6 archivos se recibieron agrupados en `DatosEcobici.zip`. Ese contenedor se extrajo en `data/raw/` para tener los archivos tal como los publica el portal; los ZIP de recorridos de cada año **no** se descomprimieron y los CSV no se modificaron.
### Bronze (Tarea 2)

- **Lectura por partes (`chunksize=500_000`) y escritura incremental con `pyarrow.ParquetWriter`:** la PC tiene 7,6 GB de RAM y el CSV de 2019 ocupa 1,9 GB descomprimido; así nunca se carga el archivo entero en memoria.
- **`keep_default_na=False` además de `dtype=str`:** sin esto, pandas convierte `""`, `"NA"`, `"null"`, etc. en NaN, lo cual ya es una interpretación del dato. En bronze un vacío queda como `""`, y silver decide qué es nulo.
- **El ZIP se abre con `zipfile` y se elige el CSV explícitamente** (falla si no hay exactamente uno), en lugar de `compression="zip"`, que falla con un mensaje poco claro si el ZIP trae más de un archivo.
- **Escritura en archivo temporal + reemplazo:** se escribe `data.parquet.tmp` y al terminar reemplaza a `data.parquet`. Garantiza la idempotencia y evita dejar un Parquet a medio escribir si el proceso se corta.
- **`_fecha_ingesta` única por archivo:** todas las filas de un mismo archivo comparten la marca de tiempo de inicio de su ingesta.
- **Columna sin nombre de 2019:** el encabezado original es `""`; pandas la nombra `Unnamed: 0` al leerla. Se conserva con ese nombre en bronze (es la forma estándar en que pandas expone un encabezado vacío; renombrarla a mano sería transformar el dato). En silver se descarta, porque es solo un índice de fila.
- **Verificación automática:** después de escribir cada año se comprueba, con los metadatos del Parquet, que las filas sean las leídas, que las columnas sean las originales más las tres de metadatos y que todas sean texto. Si algo no coincide, el pipeline se detiene.

### Silver (Tarea 3)

**Lectura y tipos**

- **Qué es "nulo":** bronze guarda los vacíos como `""`. Silver trata como nulo el texto vacío (después de quitar espacios) y el texto literal `"NA"`, que aparece en 765 edades de usuarios 2019. Es el primer paso de la transformación: centraliza la interpretación de "sin dato".
- **Texto con `StringDtype("pyarrow")`:** es el tipo `string` del esquema (con `pd.NA`), pero con almacenamiento en Arrow, mucho más liviano que objetos de Python. Con 10 millones de viajes y 7,6 GB de RAM, hace la diferencia.
- **Fechas forzadas a `datetime64[ns]`:** pandas 3 interpreta fechas de texto con resolución de microsegundos por defecto. Se convierte explícitamente a `[ns]` para cumplir el esquema canónico.
- **Procesamiento año por año:** se lee de bronze solo las columnas del mapeo y se procesa un año por vez, escribiendo cada uno como una parte del mismo Parquet. Así nunca están los tres años en memoria a la vez.
- **Una tabla = un archivo:** cada tabla se guarda como `data/silver/<tabla>/data.parquet` (archivo temporal + reemplazo, igual que en bronze, para garantizar idempotencia).

**Ids**

- **`id_viaje` de 2016 = `2016-` + número de fila de bronze con 6 dígitos (`2016-000001`).** 2016 no trae id. La numeración se hace antes de cualquier filtro, así es estable entre ejecuciones y permite ubicar la fila original. El prefijo evita choques con los ids numéricos de 2019 (10 a 6.875.895) y 2024 (20.180.969 a 24.503.283). Consecuencia: en 2016 la regla `DUPLICADO` no puede detectar nada; se verificó que entre los viajes de 2016 con ambas fechas no hay repetidos por inicio + fin + estaciones, así que no se pierde información.
- **Sufijo `BAEcobici` (2019) y `.0` (2024):** se quitan de todos los ids. Son artefactos del formato de exportación; sin quitarlos, el mismo usuario o estación tendría ids distintos entre años y no cruzarían con la tabla de usuarios.
- **`id_usuario` en viajes 2016:** queda nulo (el esquema lo permite). El archivo trae el género del usuario, pero sin id no se puede vincular.

**Duración**

- **2016 se recalcula como fin − inicio.** El archivo la trae como texto timedelta (otra unidad) y, además, solo coincide con fin − inicio en el 0,04 % de los viajes; el enunciado indica recalcularla en ese caso. Para los viajes sin fecha de fin queda nula (van a cuarentena igual).
- **2019 y 2024 se toman del archivo.** Están en segundos y coinciden con fin − inicio en el 100 % de los casos (en 2024 hay 6 viajes con más de 60 s de diferencia; se respeta el valor de origen).

**Nombres de estación**

- Además de lo que pide el enunciado (quitar espacios en los extremos, mayúsculas y espacios múltiples), se **quita el prefijo numérico** (`005 - PLAZA ITALIA` → `PLAZA ITALIA`) y las **tildes** (Á→A, Ü→U, etc.; la Ñ se conserva). Justificación: la misma estación aparece como `PACÍFICO` (2016), `PACIFICO` (2024) o `GUZMÁN`/`GÚZMAN`; sin esto, el nombre cambiaría entre años solo por formato. El prefijo es un código de estación que 2016 no tiene, no parte del nombre.
- **Nombres que no son nombres pasan a nulo** (`ERRONEA`, códigos como `KP1808000368` y valores solo numéricos como `175`). Se detectó al revisar el reporte 2: con la regla de "nombre más reciente", el top 10 de 2016 mostraba `ERRONEA` y `KP1808000368`. La dirección de la estación 1 en 2019 (Av. Figueroa Alcorta 2120) es la de Facultad de Derecho, que es su nombre en 2016, y la 10 era `PUERTO MADERO - UCA`. Es limpieza de valores, por eso va en silver y no en gold, con el mismo criterio que un género no reconocido. Afecta solo a 2019: 26.481 nombres de origen y 30.528 de destino. El id de estación se conserva, así que estos viajes no van a cuarentena (`ESTACION_NULA` mira el id, no el nombre).
- No se unifican estaciones que cambiaron de nombre de verdad (id 44 `ZOOLOGICO` → `ECOPARQUE`): eso no es un problema de formato. `dim_estacion` (gold) toma el nombre más reciente, como pide el enunciado.

**Calidad de viajes**

- **`DUPLICADO` compara contra todas las filas anteriores**, incluidas las que fueron a cuarentena por otra regla y las de años ya procesados (orden: 2016, 2019, 2024 y, dentro de cada año, el orden del archivo). Es la lectura literal de "el id ya apareció en una fila anterior".
- **Comparaciones con nulos:** en las reglas 3 y 4, una comparación con NaT/NA se toma como "no falla". Esos casos ya los atrapan las reglas 1 y 2, que se evalúan antes.

**Usuarios**

- **Las reglas se aplican sobre los tres años juntos:** un usuario puede aparecer en archivos de años distintos, y "sin duplicados" debe valer para toda la tabla.
- **Duplicados: se conserva el de `fecha_alta` más reciente** (lo indica el enunciado); a igual fecha, el de `anio_fuente` mayor.
- **Cuarentena de usuarios (`silver/usuarios_cuarentena`):** el enunciado solo pide cuarentena para viajes, pero se aplica el mismo criterio de "no se borra, se mueve" para no perder registros y poder conciliar bronze = silver + cuarentena también en usuarios. Motivos: `ID_NULO`, `DUPLICADO`.
- **Los 5.231 duplicados son ids de 2016 que reaparecen en el archivo de 2019**, siempre con alta entre mayo (1.673) y junio (3.558) de 2019, lo que sugiere una migración de cuentas al sistema nuevo. Solo el 38,8 % coincide en género con el registro de 2016, y la edad no es coherente con el paso del tiempo. Interpretación: el sistema de 2019 **reutilizó ids**, así que es probable que no sean la misma persona. Se aplica igual la regla del enunciado; queda como limitación conocida.
- **Edades fuera de rango:** las menores a 16 o mayores a 90 se reemplazan por nulo (lo indica el enunciado): 0 en 2016, 46 en 2019, 94 en 2024. Se cuenta cuántas en cada año para dejarlo registrado.

### Gold (Tarea 4)

- **Una tabla por carpeta:** `data/gold/<tabla>/data.parquet`. Se escribe con el mismo mecanismo temporal + reemplazo de silver (`src/io_parquet.py`, compartido por ambas capas para no duplicar código).
- **`dim_fecha` = calendario completo de cada año presente en los datos** (1/1 al 31/12 de 2016, 2019 y 2024: 1.097 días). Un día sin viajes debe existir en la dimensión (por ejemplo, 2019 empieza el 17/02 y así los días previos figuran con 0 viajes), pero no se inventan los años 2017, 2018 ni 2020–2023, de los que no hay datos.
- **`dia_semana` en minúsculas y con tildes** (`miércoles`, `sábado`), igual que el ejemplo del enunciado (`viernes`).
- **`fecha_key` se calcula desde la fecha de inicio del viaje.** Se verificó que todos los viajes empiezan en el mismo año que su `anio_fuente`, así que año de la fecha y año del archivo coinciden.
- **`dim_estacion`, nombre más reciente:** se toma el nombre **válido** del último año en que la estación lo tiene (lo pide el enunciado; los nombres inválidos ya llegan nulos desde silver). Si en ese año hubiera más de un nombre, se desempata por el más frecuente; hoy no pasa (se verificó que cada id tiene un solo nombre por año, sumando origen y destino). Si una estación nunca tuvo un nombre válido, queda `DESCONOCIDA`: son 2 casos, las estaciones 300 y 350, que en 2019 figuran como `175` y `234`. Resultado: 532 estaciones. Ejemplos: id 44 queda como `ECOPARQUE` (era `ZOOLOGICO` en 2016), id 14 como `PACIFICO` e id 1 como `FACULTAD DE DERECHO`.
- **`primer_anio`/`ultimo_anio` cuentan también los años sin nombre válido:** la estación existió y tuvo viajes ese año, aunque el nombre estuviera mal cargado.
- **`primer_anio`/`ultimo_anio`** se calculan sobre los años presentes (2016, 2019, 2024): "2016 a 2024" no garantiza que la estación haya existido en los años intermedios, que no tienen datos.
- **`rango_etario`:** 16-25, 26-35, 36-50, 51+ y `DESCONOCIDO` para edad nula (905 usuarios). Como silver deja en nulo las edades fuera de [16, 90], no existe un rango para menores de 16.
- **`duracion_min` = `duracion_seg / 60` redondeado a 1 decimal**, tipo `Float64` (acepta nulos como el resto de las columnas).
- **`es_circular`** = origen y destino con el mismo id de estación (no se compara por nombre, porque el id es la clave).
- **`anio_alta`** sale del año de `fecha_alta` de silver.

**Viajes con `id_usuario` que no está en `dim_usuario` (lo pide el enunciado)**

| Año del viaje | Viajes | Sin id de usuario | Con id que no está en `dim_usuario` |
|---|---|---|---|
| 2016 | 503.252 | 503.252 (el archivo no trae id) | — |
| 2019 | 6.207.851 | 0 | 4.410.500 (71,0 %) |
| 2024 | 3.555.217 | 0 | 1.710.135 (48,1 %) |
| **Total** | 10.266.320 | 503.252 | **6.120.635**, de 411.270 usuarios distintos |

Explicación: cada archivo de usuarios trae solo a los usuarios **dados de alta ese año**, pero los viajes de un año los hacen también usuarios que se registraron antes. Por ejemplo, los registrados en 2017, 2018 o entre 2020 y 2023, de quienes no tenemos archivo. Es coherente con lo que se ve en los viajes que sí cruzan: en 2024 viajan usuarios dados de alta en 2024 (1.134.699 viajes), en 2019 (692.483) y en 2016 (17.900). No es un error de datos, pero sí una limitación: los reportes por género o rango etario solo representan a los viajes de usuarios con alta en 2016, 2019 o 2024. No se crean usuarios "desconocidos" en `dim_usuario`, porque silver no agrega datos y gold no debe inventarlos: el `id_usuario` del viaje se conserva y la relación queda abierta.

Advertencia adicional: por la posible reutilización de ids detectada en silver, los 304.772 viajes de 2019 que cruzan con usuarios dados de alta en 2016 podrían corresponder a otra persona con el mismo id.

### Reportes (Tarea 5)

- **Los reportes 1 a 4 leen solo gold** (`fact_viajes` + dimensiones); el 5 usa los conteos de bronze (metadatos del Parquet) y de silver, como permite el enunciado.
- **Reporte 1 parte de `dim_fecha`:** así los meses sin viajes aparecen con 0 en lugar de desaparecer. Enero de 2019 figura con 0, porque los datos de 2019 empiezan el 17/02.
- **Reporte 2:**
  - Se cuenta por **id** de estación de origen y se muestra el nombre de `dim_estacion` (el más reciente), así la misma estación se reconoce igual en los tres años.
  - Ante empates, se ordena por id y el ranking es correlativo, para tener siempre exactamente 10 filas por año.
- **Reporte 3 incluye solo los viajes cuyo usuario está en `dim_usuario`** (join interno): 3.642.433 de 10.266.320. Los demás no tienen edad ni género conocidos. Agregarlos como una fila "sin usuario" mezclaría dos cosas distintas, porque `DESCONOCIDO` ya se usa para el usuario conocido que no declaró edad o género. Ver la limitación explicada en la sección de gold.
- **Orden de los reportes:** rangos etarios de menor a mayor edad y géneros F, M, OTRO, DESCONOCIDO, en lugar de orden alfabético, para que se lean más fácil.
- **Redondeo:** duración promedio y porcentaje de circulares con 1 decimal, y porcentaje de cuarentena con 2, como en los ejemplos del enunciado.
- **Formato CSV:** separador `,`, punto decimal, sin separador de miles (los puntos de miles de los ejemplos son solo de presentación) y codificación `utf-8-sig`, para que Excel en Windows muestre bien la Ñ (`PEÑA`, `NUÑEZ`).
- **Verificación cruzada antes de guardar:**
  - La suma del reporte 1 y el total del reporte 4 son iguales a las filas de `fact_viajes`.
  - El reporte 3 suma exactamente los viajes que cruzan con `dim_usuario`.
  - El reporte 2 tiene 10 filas por año.
  - En el reporte 5 se cumple bronze = silver + cuarentena.

### Observaciones sobre los resultados

- **¿Cambian las estaciones del top 10 entre años? Sí, bastante.** Comparando por id:
  - Solo 3 estaciones están en el top de los tres años: `PACIFICO` (14), `CONGRESO` (8) y `PLAZA ITALIA` (5).
  - `PARQUE LAS HERAS` y `PARQUE CENTENARIO` están en 2016 y 2019, pero salen del top en 2024.
  - `CONSTITUCION` (175) es la primera en 2019 y 2024; no existía en los datos de 2016.
  - 5 de las 10 de 2024 no estaban en el top de ningún año anterior: `PLAZA DE LA SHOA`, `JULIETA LANTERI`, `BARRANCAS DE BELGRANO`, `HOSPITAL DE CLINICAS` y `FACULTAD DE DERECHO`. Una de ellas, `PLAZA DE LA SHOA` (516), es una de las 117 estaciones que solo aparecen en 2024.
  - **Mismo nombre, distinta estación:** `FACULTAD DE DERECHO` aparece en 2016 (id 1) y en 2024 (id 202), y lo mismo pasa con `RETIRO I` (id 2) y `RETIRO II` (id 130). Por eso el ranking se cuenta por id y no por nombre.
- **2016 tiene muy pocos viajes** (503 mil contra 6,2 millones en 2019) y una distribución mensual irregular: abril tiene 2.509 viajes y octubre 91.458. Además, la duración recalculada va de 10 minutos a 3 horas. Todo sugiere que el archivo de 2016 es un subconjunto o una muestra y no el total del año. Las comparaciones de volumen entre 2016 y los otros años deben tomarse con cuidado.
- **Calidad:** 2016 pierde el 15,68 % de sus viajes (todos por falta de fecha de fin); 2019 y 2024 menos del 0,2 %.
