# Pendientes

## Por resolver

### 1. Verificar las migraciones contra un PostgreSQL vacío

Las cuatro migraciones de `migrations/versions/` se escribieron y se
probaron sólo contra SQLite (el motor de desarrollo). Los índices únicos
parciales (`sqlite_where=...` / `postgresql_where=...` en
`uq_fondos_capital_activo` y `uq_ejercicio_vigente`) y los `CHECK` de la
migración `909b3621ff6e` se escribieron pensando en los dos motores, pero
los tipos (`Numeric`, `JSON`, `Boolean`) y el modo `render_as_batch` se
comportan distinto entre SQLite y PostgreSQL, y Alembic puede generar SQL
válido para uno que no lo sea (o no haga falta) en el otro.

Antes de desplegar a producción hay que:

1. Levantar un PostgreSQL vacío (local o de prueba).
2. Apuntar `DATABASE_URL` ahí y correr `flask db upgrade`.
3. Confirmar que las 12 tablas, sus FK, sus `UNIQUE`, sus índices parciales
   y sus `CHECK` quedan iguales a los de SQLite (`\d+ nombre_tabla` en
   `psql`, o `inspect(db.engine)`).

### 2. `utilidades/limite_peticiones.py` no sirve con más de un worker

El contador de consultas por IP vive en un diccionario en memoria
(`_consultas`), del proceso de Python. En desarrollo, con un solo proceso,
funciona. En producción el stack es Gunicorn + Nginx (ver README): si
Gunicorn se levanta con varios workers, cada uno tiene su propio
diccionario, sin compartir nada entre sí.

Un límite de "10 intentos de login por IP cada 5 minutos" con 4 workers
permite en la práctica hasta 40, porque cada request cae en un worker al
azar y cada worker cuenta por su cuenta. El límite deja de cumplir lo que
promete (RNF-02, RNF-03) apenas se corre con más de un worker.

Corrección: mover el contador a un almacén compartido entre procesos
(Redis, o una tabla en la base) antes de desplegar con más de un worker de
Gunicorn.

### 3. `pagos.cuit`: ¿es del aportante o de quien transfiere?

La columna existe (`app/modelos/pagos.py`) y se completa en los
formularios de aporte adicional ("CUIT, si aporta una empresa"), pero el
cliente nunca definió qué representa exactamente:

- ¿el CUIT del propio `Aportante` (una forma alternativa de identificarlo,
  además del DNI)?
- ¿o el CUIT de un tercero (una empresa) que hizo la transferencia en
  nombre o a beneficio del aportante, que puede ser una persona distinta?

La diferencia importa para conciliar contra el extracto del banco y para
cualquier reporte que agrupe aportes por quien realmente puso la plata.
Hoy el dato se guarda pero no se usa para nada más que mostrarlo.

### 4. `pagos_grupales_detalle.estado`: ¿se puede verificar parcialmente una transferencia grupal?

La columna existe con su propio estado (`pendiente`, `verificado`,
`rechazado`) por persona, pero `servicios/pagos_grupales.py` siempre la
actualiza en bloque, junto con el estado de todo el `PagoGrupal`
(`verificar_pago_grupal()` y `rechazar_pago_grupal()` recorren *todos* los
detalles y *todos* los pagos de la transferencia y los pasan al mismo
estado). No hay ningún camino en el código para verificar o rechazar a una
sola persona del grupo sin tocar a las demás.

El cliente no definió si esto es el diseño definitivo (una transferencia
grupal se verifica entera o no se verifica) o si en algún momento hace
falta poder aceptar a algunas personas del grupo y rechazar a otras por
separado. Mientras no se defina, la columna por-persona sugiere una
granularidad que el sistema no ofrece.

### 5. Normalización pendiente: `carreras.anios` y `aportantes.anio`

`Carrera.anios` (`app/modelos/carreras.py`) guarda los años que dicta esa
carrera como texto separado por comas (por ejemplo `'1°,2°,3°'`): no es un
valor atómico, viola 1FN, y para usarlo hay que parsearlo a mano en algún
lado.

`Aportante.anio` (`app/modelos/aportantes.py`) es una columna de texto
libre (`String(5)`) sin ninguna restricción: no hay manera de que la base
impida guardar un año que no está en la lista de esa carrera, ni siquiera
un valor que no esté en `app/constantes.py::ANIOS` (`['1°', '2°', '3°']`,
la misma lista, escrita una tercera vez para poblar los `<select>` de los
formularios).

Corrección: una tabla `carreras_anios` (`carrera_id`, `anio`) con una fila
por año que dicta cada carrera, y `aportantes.anio` pasa a ser una clave
foránea a esa tabla en lugar de texto suelto. Fuera de alcance de los
bloques anteriores porque toca el modelo de datos de aportantes y carreras,
no sólo agrega una restricción sobre lo que ya hay.

### 6. `MAX_CONTENT_LENGTH` del `.env.example` no se usa

`.env.example` documenta una variable `MAX_CONTENT_LENGTH` (bytes, 16 MB),
pero `app/config.py` nunca la lee con `os.getenv`: el límite queda fijo en
`TAMANIO_MAXIMO_COMPROBANTE` (`app/constantes.py`) sin importar lo que diga
el `.env`. Detectado en el Bloque 1 (constantes compartidas).

### 7. `nuevo_ejercicio` sigue sin controlar `fecha_asamblea`

Si `fecha_asamblea` viene con un formato inválido, `date.fromisoformat()`
tira una excepción sin capturar (`app/controladores/administracion.py`).
Es un bug preexistente al Bloque 4, detectado ahí pero fuera de ese
alcance: corregirlo habría cambiado el comportamiento actual, que es lo
que ese bloque pedía no hacer.

---

## Decisiones de ambigüedad ya tomadas (contexto, no bugs)

Registro de las veces que hubo más de una lectura posible de un pedido y
se eligió una sin volver a preguntar, para que quede el porqué.

### Bloque 4

- **URL de `app/controladores/api.py`**: la consigna decía que los cuatro
  endpoints quedan en `/api/validar-dni` etc. y, en la misma frase, que "las
  URL quedan idénticas". Hoy son `/aportante/api/validar-dni` (por el
  `url_prefix='/aportante'` de `aportantes_bp`), y `sistcoop.js` ya llama a
  esa ruta completa. Prioricé "las URL quedan idénticas": `api_bp` se
  registra con el mismo `url_prefix='/aportante'`, así que las cuatro rutas
  no cambiaron un carácter y no hizo falta tocar el JavaScript.
- **`validaciones.validar_fecha` / `validar_fecha_transferencia` /
  `texto_a_fecha` ahora aceptan un `date` además de un texto** (ver
  `_a_fecha_o_none`). Hacía falta para que `validar_datos()` del servicio
  pueda seguir revalidando cuando el controlador ya le manda un `date`
  tipado (como pide el Bloque 4), sin repetir la regla de "no futura / no
  demasiado vieja" en dos lugares. La regla de negocio no cambió: sólo el
  tipo de dato que puede entrar.
- **`app/formularios/administracion.py` no reusa `validaciones.validar_importe`
  para `cuota`**: `editar_cuota` y `nuevo_ejercicio` ya usaban una regla más
  simple y un mensaje genérico distinto ("El monto de la cuota no es
  válido.", "Año o cuota inválidos.") del que ve el aportante en los
  formularios públicos. Repliqué esa regla tal cual para no cambiarle el
  mensaje a la Cooperadora; no es la misma validación que la de
  `validar_importe()`, así que no correspondía reusar esa función ahí.

### Bloque 6 — las tres restricciones de 6.3 quedaron en la base

Los tres supuestos (un fondo de capital activo, un fondo por carrera, un
ejercicio vigente) se probaron como índices únicos —dos de ellos parciales,
con `WHERE`— y los tres funcionaron con `render_as_batch` en SQLite,
incluso con filas ya referenciándolos por FK. No quedó ninguno resuelto
sólo en el servicio: la base los garantiza a los tres. El guard de servicio
para "ejercicio vigente" (`app/servicios/ejercicios.py::abrir_ejercicio`)
se agregó de todos modos, como pidió el usuario, para que cerrar el
anterior y abrir el nuevo no dependa de que cada llamador se acuerde de
hacerlo en el orden correcto — es una capa extra sobre el índice, no un
reemplazo.

### Notas operativas para futuras migraciones (Bloque 6)

- **`migrations/env.py` apaga `PRAGMA foreign_keys` durante la migración**
  (sólo en esa conexión, sólo mientras corre `flask db migrate`/`upgrade`).
  Hacía falta porque el modo batch de SQLite recrea la tabla entera
  (DROP + CREATE) para cualquier cambio que no sea un simple índice —una
  `UniqueConstraint` o un `CheckConstraint` de tabla—, y si otra tabla la
  referencia por FK con `PRAGMA foreign_keys=ON` (ver `app/__init__.py`,
  Bloque 5), ese DROP TABLE falla. La app en uso normal sigue con las
  claves foráneas activas siempre: esto es sólo para la conexión de
  Alembic. Ver el comentario en `migrations/env.py` para el detalle de por
  qué el pragma se pide sobre el driver crudo y no sobre la `Connection` de
  SQLAlchemy (pedirlo ahí abre una transacción implícita que se pierde sin
  commit al cerrar la conexión, y la migración entera queda revertida sin
  ningún error visible).
- **Alembic no detecta `CheckConstraint` con autogenerate**: `flask db
  migrate` no encontró los cuatro `CHECK` del Bloque 6.4 aunque estaban en
  los modelos ("No changes in schema detected"). Esa migración
  (`909b3621ff6e`) se escribió a mano con `flask db revision` +
  `batch_op.create_check_constraint(...)`. Si se agrega o cambia un `CHECK`
  más adelante, hay que repetir el archivo a mano y no confiar en el
  autogenerate para esa parte.
