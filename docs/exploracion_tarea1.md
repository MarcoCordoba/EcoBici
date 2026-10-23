# Tarea 1 — Exploración de archivos (salida de `python -m src.exploracion`)

Muestra leída con `nrows=1000`; las filas totales se cuentan por partes (`chunksize=500,000`).

## Recorridos

### Recorridos 2016 — `recorridos-realizados-2016.zip`

- Archivo dentro del ZIP: `recorridos-realizados-2016.csv`
- Separador: `,` | BOM UTF-8: False | Fin de línea: CRLF
- Filas de datos (pandas): **596,807** | Líneas físicas: 596,808
- Columnas (15): `periodo`, `genero_usuario`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `domicilio_estacion_origen`, `duracion_recorrido`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `domicilio_estacion_destino`

Primeras 3 filas:

```
                                                       0                                                     1                                                     2
periodo                                             2016                                                  2016                                                  2016
genero_usuario                                         M                                                     M                                                     M
fecha_origen_recorrido               2016-01-01 02:21:41                                   2016-01-01 08:38:19                                   2016-01-01 15:01:07
id_estacion_origen                                    11                                                    28                                                    28
nombre_estacion_origen                        Tribunales                                           Plaza Boedo                                           Plaza Boedo
long_estacion_origen                 -58.385021610721594                                   -58.412398197949294                                   -58.412398197949294
lat_estacion_origen                    -34.6013128134582                                     -34.6228502511336                                     -34.6228502511336
domicilio_estacion_origen                     Tribunales  Carlos Calvo entre Virrey Liniers y Sánchez de Loria  Carlos Calvo entre Virrey Liniers y Sánchez de Loria
duracion_recorrido             0 days 00:16:29.000000000                             0 days 00:55:26.000000000                             0 days 00:40:27.000000000
fecha_destino_recorrido              2016-01-01 02:48:05                                   2016-01-01 09:36:12                                   2016-01-01 16:04:15
id_estacion_destino                                    5                                                    28                                                    30
nombre_estacion_destino                     Plaza Italia                                           Plaza Boedo                                                  Peña
long_estacion_destino                -58.420997041077996                                   -58.412398197949294                                     -58.3973783649902
lat_estacion_destino                   -34.5801273443074                                     -34.6228502511336                                     -34.5903936115174
domicilio_estacion_destino  Av. Santa Fe y Av. Sarmiento  Carlos Calvo entre Virrey Liniers y Sánchez de Loria                                      Azcuénaga y Peña
```

- Ejemplos `fecha_origen_recorrido`: `2016-01-01 02:21:41`, `2016-01-01 08:38:19`, `2016-01-01 15:01:07`
- Ejemplos `fecha_destino_recorrido`: `2016-01-01 02:48:05`, `2016-01-01 09:36:12`, `2016-01-01 16:04:15`
- Ejemplos `duracion_recorrido`: `0 days 00:16:29.000000000`, `0 days 00:55:26.000000000`, `0 days 00:40:27.000000000`, `0 days 00:45:44.000000000`, `0 days 00:44:09.000000000`
- Ejemplos `id_estacion_origen` (nulos en muestra: 0): `11`, `28`, `5`
- Ejemplos `id_estacion_destino` (nulos en muestra: 0): `5`, `28`, `30`
- Valores de `genero_usuario` en muestra: {'M': 790, 'F': 210}

### Recorridos 2019 — `recorridos-realizados-2019.zip`

- Archivo dentro del ZIP: `trips_2019.csv`
- Separador: `,` | BOM UTF-8: False | Fin de línea: CRLF
- Filas de datos (pandas): **6,217,004** | Líneas físicas: 6,217,005
- Columnas (18): `Unnamed: 0`, `Id_recorrido`, `duracion_recorrido`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `direccion_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `direccion_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `id_usuario`, `modelo_bicicleta`, `género`

Primeras 3 filas:

```
                                                  0                           1                                           2
Unnamed: 0                                        1                           2                                           3
Id_recorrido                          9379BAEcobici               7441BAEcobici                               6828BAEcobici
duracion_recorrido                              239                       2,814                                         298
fecha_origen_recorrido          2019-02-27 19:44:42         2019-02-27 14:35:58                         2019-02-27 11:51:40
id_estacion_origen                       5BAEcobici                  6BAEcobici                                 73BAEcobici
nombre_estacion_origen           005 - Plaza Italia         006 - Parque Lezama                    073 - Ruy Díaz de Guzmán
direccion_estacion_origen        Av. Sarmiento 2601  Avenida Martin Garcia, 295  Avenida Martin Garcia y Ruy Díaz de Guzmán
long_estacion_origen                    -58.4209542                  -58.369758                                 -58.3718235
lat_estacion_origen                     -34.5805497                  -34.628526                                 -34.6306814
fecha_destino_recorrido         2019-02-27 19:48:41         2019-02-27 15:22:52                         2019-02-27 11:56:38
id_estacion_destino                      5BAEcobici                  6BAEcobici                                  6BAEcobici
nombre_estacion_destino          005 - Plaza Italia         006 - Parque Lezama                         006 - Parque Lezama
direccion_estacion_destino       Av. Sarmiento 2601  Avenida Martin Garcia, 295                  Avenida Martin Garcia, 295
long_estacion_destino                   -34.5805497                  -34.628526                                  -34.628526
lat_estacion_destino        -34.5805497,-58.4209542       -34.628526,-58.369758                       -34.628526,-58.369758
id_usuario                            6243BAEcobici              11140BAEcobici                               1994BAEcobici
modelo_bicicleta                             ICONIC                      ICONIC                                      ICONIC
género                                        OTHER                        MALE                                        MALE
```

- Ejemplos `fecha_origen_recorrido`: `2019-02-27 19:44:42`, `2019-02-27 14:35:58`, `2019-02-27 11:51:40`
- Ejemplos `fecha_destino_recorrido`: `2019-02-27 19:48:41`, `2019-02-27 15:22:52`, `2019-02-27 11:56:38`
- Ejemplos `duracion_recorrido`: `239`, `2,814`, `298`, `2,324`, `1,215`
- Ejemplos `Id_recorrido` (nulos en muestra: 0): `9379BAEcobici`, `7441BAEcobici`, `6828BAEcobici`
- Ejemplos `id_estacion_origen` (nulos en muestra: 0): `5BAEcobici`, `6BAEcobici`, `73BAEcobici`
- Ejemplos `id_estacion_destino` (nulos en muestra: 1): `5BAEcobici`, `6BAEcobici`, `9BAEcobici`
- Ejemplos `id_usuario` (nulos en muestra: 0): `6243BAEcobici`, `11140BAEcobici`, `1994BAEcobici`
- Valores de `género` en muestra: {'MALE': 821, 'FEMALE': 157, 'OTHER': 22}

### Recorridos 2024 — `recorridos-realizados-2024.zip`

- Archivo dentro del ZIP: `badata_ecobici_recorridos_realizados_2024.csv`
- Separador: `,` | BOM UTF-8: True | Fin de línea: LF
- Filas de datos (pandas): **3,559,284** | Líneas físicas: 3,559,285
- Columnas (17): `id_recorrido`, `duracion_recorrido`, `fecha_origen_recorrido`, `id_estacion_origen`, `nombre_estacion_origen`, `direccion_estacion_origen`, `long_estacion_origen`, `lat_estacion_origen`, `fecha_destino_recorrido`, `id_estacion_destino`, `nombre_estacion_destino`, `direccion_estacion_destino`, `long_estacion_destino`, `lat_estacion_destino`, `id_usuario`, `modelo_bicicleta`, `genero`

Primeras 3 filas:

```
                                                                      0                       1                           2
id_recorrido                                                   20428222                20431744                    20429936
duracion_recorrido                                                  568                    1355                           0
fecha_origen_recorrido                              2024-01-23 18:36:00     2024-01-23 22:41:20         2024-01-23 20:06:22
id_estacion_origen                                                  513                     460                         467
nombre_estacion_origen                              308 - SAN MARTIN II  133 - BEIRO Y SEGUROLA          328 - SARMIENTO II
direccion_estacion_origen                           Av. San Martín 5129           Segurola 3194              Sarmiento 2037
long_estacion_origen                                -58.490739000000005      -58.51193000000001                 -58.3958925
lat_estacion_origen                                         -34.5971297                -34.6075                 -34.6055135
fecha_destino_recorrido                             2024-01-23 18:45:28     2024-01-23 23:03:55         2024-01-23 20:06:22
id_estacion_destino                                                 498                     382                           6
nombre_estacion_destino                                    055 - HABANA          204 - Biarritz         006 - Parque Lezama
direccion_estacion_destino  Gral. José Gervasio Artigas 4298 (y Habana)           Biarritz 2403  Avenida Martin Garcia, 295
long_estacion_destino                                -58.49495850000001      -58.47725521899702                  -58.369758
lat_estacion_destino                                        -34.5865976      -34.60543081369964                  -34.628526
id_usuario                                                     992557.0                320782.0                    828678.0
modelo_bicicleta                                                    FIT                     FIT                         FIT
genero                                                             MALE                  FEMALE                      FEMALE
```

- Ejemplos `fecha_origen_recorrido`: `2024-01-23 18:36:00`, `2024-01-23 22:41:20`, `2024-01-23 20:06:22`
- Ejemplos `fecha_destino_recorrido`: `2024-01-23 18:45:28`, `2024-01-23 23:03:55`, `2024-01-23 20:06:22`
- Ejemplos `duracion_recorrido`: `568`, `1355`, `0`, `680`, `466`
- Ejemplos `id_recorrido` (nulos en muestra: 0): `20428222`, `20431744`, `20429936`
- Ejemplos `id_estacion_origen` (nulos en muestra: 0): `513`, `460`, `467`
- Ejemplos `id_estacion_destino` (nulos en muestra: 0): `498`, `382`, `6`
- Ejemplos `id_usuario` (nulos en muestra: 0): `992557.0`, `320782.0`, `828678.0`
- Valores de `genero` en muestra: {'MALE': 536, 'FEMALE': 350, 'OTHER': 110, nan: 4}

## Usuarios

### Usuarios 2016 — `usuarios-ecobici-2016.csv`

- Separador: `,` | BOM UTF-8: False | Fin de línea: CRLF
- Filas de datos (pandas): **39,481** | Líneas físicas: 39,482
- Columnas (5): `id_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta`

Primeras 3 filas:

```
                         0            1            2
id_usuario          223858       223873       223874
genero_usuario           M            M            M
edad_usuario            41           35           47
fecha_alta        01-01-16     01-01-16     01-01-16
hora_alta       3:45:19 AM  12:36:42 PM  12:45:44 PM
```

- Ejemplos `fecha_alta`: `01-01-16`, `02-01-16`, `03-01-16`
- Ejemplos `hora_alta`: `3:45:19 AM`, `12:36:42 PM`, `12:45:44 PM`
- Ejemplos `id_usuario` (nulos en muestra: 0): `223858`, `223873`, `223874`
- Valores de `genero_usuario` en muestra: {'M': 529, 'F': 471}
- `edad_usuario` en muestra: min=16, max=83, nulos=0

- Valores de género en el archivo **completo**: {'M': 21697, 'F': 17784}

### Usuarios 2019 — `usuarios_ecobici_2019.csv`

- Separador: `,` | BOM UTF-8: False | Fin de línea: CRLF
- Filas de datos (pandas): **83,600** | Líneas físicas: 83,601
- Columnas (5): `ID_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta`

Primeras 3 filas:

```
                         0           1           2
ID_usuario          627966      628268      627943
genero_usuario       OTHER        MALE        MALE
edad_usuario            36          43          47
fecha_alta      2019-12-31  2019-12-31  2019-12-31
hora_alta         10:46:10    18:54:57    10:18:36
```

- Ejemplos `fecha_alta`: `2019-12-31`, `2019-12-30`, `2019-12-29`
- Ejemplos `hora_alta`: `10:46:10`, `18:54:57`, `10:18:36`
- Ejemplos `ID_usuario` (nulos en muestra: 0): `627966`, `628268`, `627943`
- Valores de `genero_usuario` en muestra: {'MALE': 439, 'FEMALE': 356, 'OTHER': 205}
- `edad_usuario` en muestra: min=16, max=85, nulos=0

- Valores de género en el archivo **completo**: {'MALE': 41107, 'FEMALE': 24285, 'OTHER': 17351, nan: 857}

### Usuarios 2024 — `usuarios_ecobici_2024.csv`

- Separador: `,` | BOM UTF-8: True | Fin de línea: LF
- Filas de datos (pandas): **197,077** | Líneas físicas: 197,078
- Columnas (5): `id_usuario`, `genero_usuario`, `edad_usuario`, `fecha_alta`, `hora_alta`

Primeras 3 filas:

```
                         0           1           2
id_usuario         1094487     1097128     1102901
genero_usuario       OTHER      FEMALE       OTHER
edad_usuario            35          21          19
fecha_alta      2024-01-18  2024-01-21  2024-01-29
hora_alta         09:21:02    23:02:26    19:33:32
```

- Ejemplos `fecha_alta`: `2024-01-18`, `2024-01-21`, `2024-01-29`
- Ejemplos `hora_alta`: `09:21:02`, `23:02:26`, `19:33:32`
- Ejemplos `id_usuario` (nulos en muestra: 0): `1094487`, `1097128`, `1102901`
- Valores de `genero_usuario` en muestra: {'OTHER': 442, 'FEMALE': 293, 'MALE': 265}
- `edad_usuario` en muestra: min=18, max=76, nulos=0

- Valores de género en el archivo **completo**: {'MALE': 88655, 'FEMALE': 79310, 'OTHER': 29112}
