# Pendientes

Bugs y ambigüedades detectados durante trabajos de reorganización, anotados
para no perder el hilo pero sin corregir (fuera del alcance de esa tarea).

## MAX_CONTENT_LENGTH del .env.example no se usa

`.env.example` documenta una variable `MAX_CONTENT_LENGTH` (bytes, 16 MB),
pero `app/config.py` nunca la lee con `os.getenv`: el límite queda fijo en
`TAMANIO_MAXIMO_COMPROBANTE` (`app/constantes.py`) sin importar lo que diga
el `.env`. Detectado en el Bloque 1 (constantes compartidas).

## Bloque 4 — decisiones de ambigüedad, no bugs

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
- **`nuevo_ejercicio` sigue sin controlar `fecha_asamblea`**: si viene con un
  formato inválido, `date.fromisoformat()` iba a tirar una excepción sin
  capturar antes del Bloque 4, y sigue igual (no es parte de lo que pedía
  este bloque, y corregirlo cambiaría el comportamiento actual).

## Bloque 5 — migraciones contra PostgreSQL

`migrations/versions/1321d039f458_estado_inicial.py` se generó con
`flask db migrate` contra SQLite (es el motor de desarrollo). Revisé a mano
que estén todas las claves foráneas y todos los `UniqueConstraint` de los
modelos, incluida la restricción con nombre `uq_saldo_aportante_ejercicio`
de `SaldoAportante`, y coinciden.

Lo que NO se probó todavía es correr esta migración contra una base
PostgreSQL vacía real: los tipos (`Numeric`, `JSON`, `Boolean`) y el modo
`render_as_batch` se comportan distinto entre motores, y Alembic puede
generar SQL válido para SQLite que no sea válido (o no haga falta) en
PostgreSQL. Antes de desplegar a producción hay que:

1. Levantar un PostgreSQL vacío (local o de prueba).
2. Apuntar `DATABASE_URL` ahí y correr `flask db upgrade`.
3. Confirmar que las 12 tablas, sus FK y sus `UNIQUE` quedan iguales a los
   de SQLite (`\d+ nombre_tabla` en `psql`, o `inspect(db.engine)`).
