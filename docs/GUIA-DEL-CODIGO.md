# Guía del código — SistCoop 179


## 1. Las tres reglas del proyecto

Todo el código está acomodado alrededor de tres reglas. Si entendés estas
tres, entendés la carpeta.

**Regla 1 — Los modelos no modifican nada.**
Un archivo de `app/modelos/` describe una tabla y sabe *responder preguntas*
(los métodos que empiezan con `get_`). Nunca cambia datos.

**Regla 2 — Todo lo que modifica datos está en `app/servicios/`.**
Y cada operación es UNA función que termina con un `db.session.commit()`.
Para saber qué pasa cuando se verifica un pago, se lee una sola función.

**Regla 3 — Los controladores no piensan.**
Un archivo de `app/controladores/` hace tres cosas: lee el formulario, llama
al servicio que corresponde y muestra una pantalla. Nada más.

```
navegador  →  controlador  →  servicio  →  modelo  →  base de datos
              (la ruta)      (la regla)   (la tabla)
```

---

## 2. La regla de negocio más importante

**Cargar un comprobante NO acredita plata.**

Cuando alguien sube su comprobante, se crea un `Pago` en estado
`pendiente`. Ese pago no suma en ningún lado: ni en el fondo de la
Cooperadora ni en el saldo de la persona. La pantalla se lo dice con todas
las letras: *"en revisión"*.

Recién cuando alguien de la Cooperadora abre el extracto del banco, ve la
transferencia y aprieta **Verificar**, el pago suma.

Esto no es un detalle técnico: es el pedido central del cliente. Si el
sistema acreditara al subir el archivo, cualquiera podría figurar al día
subiendo una foto cualquiera.

En el código, esa regla vive en una sola función:
`app/servicios/pagos.py` → `verificar_pago()`. Son veinte líneas y hacen
tres cosas numeradas:

```python
# 1. El pago pasa a verificado
pago.estado = 'verificado'
...
# 2. La plata entra al fondo
fondos.registrar_movimiento(pago.fondo, monto=pago.importe, motivo=...)

# 3. Se recalcula el saldo de cuota del aportante
saldos.recalcular_saldo_de_pago(pago)
```

---

## 3. Mapa de la carpeta

```
sistcoop179/
├── run.py                 levanta el servidor de desarrollo
├── requirements.txt       qué hay que instalar
├── app/
│   ├── __init__.py        create_app(): arma la aplicación
│   ├── config.py          configuración por entorno
│   ├── constantes.py      valores compartidos por más de un módulo
│   ├── extensions.py      las extensiones de Flask (db, login, csrf)
│   │
│   ├── modelos/           las TABLAS      (no modifican nada)
│   ├── servicios/         las REGLAS      (acá se modifica todo)
│   ├── controladores/     las RUTAS       (leen el formulario y muestran)
│   ├── formularios/       un FlaskForm por área (valida antes de llamar
│   │                      al servicio; ver sección 5.8)
│   ├── seguridad/         permisos de acceso (decorador requiere_rol)
│   ├── utilidades/        funciones sueltas sin base de datos
│   ├── vistas/            las plantillas HTML
│   └── static/            css, javascript y Bootstrap
│
├── migrations/            Flask-Migrate/Alembic: el historial del esquema
├── seeds/                 datos de referencia (las carreras del instituto)
├── scripts/               tareas de consola (crear la base, agregar datos)
├── tests/                 pytest
├── docs/                  esta guía y los pendientes
└── instance/              la base SQLite y los comprobantes (NO se sube)
```

La carpeta de plantillas se llama `app/vistas/`, no `templates/` (el valor
por defecto de Flask): `create_app()` la configura a mano con
`Flask(__name__, template_folder='vistas')`. No se renombra ni se tocan los
`render_template()` para "corregirla".

`migrations/` es código generado por Flask-Migrate: `migrations/env.py`,
`script.py.mako` y el `alembic.ini` quedan en inglés, tal como los genera la
herramienta. Sólo se traduce o comenta lo que agrega el equipo (por ejemplo,
el manejo de `PRAGMA foreign_keys` dentro de `env.py`, o el contenido de
cada archivo en `migrations/versions/`).

### Los archivos, uno por uno

| Archivo | Qué tiene |
| ------- | --------- |
| `modelos/pagos.py` | La tabla `pagos` y sus consultas |
| `modelos/saldos.py` | El saldo de cuota de cada persona |
| `modelos/fondos.py` | Los fondos y sus movimientos |
| `modelos/pagos_grupales.py` | La transferencia grupal y su detalle |
| `modelos/aportantes.py` | Las personas que aportan |
| `modelos/ejercicios.py` | El año contable y la cuota |
| `modelos/solicitudes.py` | Pedidos de fondos y eventos |
| `modelos/usuarios.py` | Quiénes entran al panel |
| `modelos/auditoria.py` | El registro de todo lo que se hace |
| `modelos/carreras.py` | Las carreras del instituto |
| **`servicios/pagos.py`** | **Alta, verificación y rechazo de pagos** |
| **`servicios/pagos_grupales.py`** | **El reparto de una transferencia grupal** |
| `servicios/saldos.py` | Recalcular el saldo, entregar la libreta |
| `servicios/fondos.py` | Mover el saldo de un fondo |
| `servicios/ejercicios.py` | Cerrar el ejercicio vigente y abrir el siguiente |
| `servicios/auditoria.py` | Escribir un renglón de auditoría |
| **`controladores/aportantes.py`** | **El portal público** |
| `controladores/administracion.py` | El panel de la Cooperadora |
| `controladores/api.py` | Las cuatro validaciones en vivo (JSON) del portal |
| `controladores/autenticacion.py` | Entrar y salir |
| `controladores/principal.py` | La raíz y el chequeo de salud |
| `formularios/cuota.py` | Formulario de cuota individual y grupal |
| `formularios/adicional.py` | Formulario de aporte adicional |
| `formularios/solicitudes.py` | Formulario de pedido de fondos y de libreta |
| `formularios/autenticacion.py` | Formulario de login |
| `formularios/administracion.py` | Formularios de cuota y de ejercicio nuevo |
| `formularios/_comunes.py` | Validadores de WTForms que envuelven `validaciones.py` |
| `seguridad/permisos.py` | El decorador `requiere_rol()` |
| `utilidades/validaciones.py` | DNI, CUIT, fechas, importes |
| `utilidades/archivos.py` | Guardar y controlar el comprobante |
| `utilidades/limite_peticiones.py` | Tope de consultas por IP |
| `utilidades/peticion.py` | IP y User-Agent del pedido actual |

Los tres en negrita son los que hay que leer. El resto se entiende solo.

---

## 4. Un pago, de punta a punta

Seguimos un pago de cuota desde que alguien aprieta "Enviar" hasta que
aparece en el fondo.

**Paso 1 — El navegador manda el formulario a `/aportante/cuota`.**

**Paso 2 — `controladores/aportantes.py` → `procesar_cuota_individual()`**
Instancia `FormularioCuotaIndividual` y llama a `validate_on_submit()` (si
falla, flashea cada error y vuelve a mostrar la pantalla). Con el
formulario ya validado, arma un diccionario `data` con los valores tipados
(`Decimal`, `date`), guarda el archivo del comprobante y llama al servicio.

**Paso 3 — `servicios/pagos.py` → `crear_pago_de_cuota(data)`**
Vuelve a validar con `validar_datos()` (ver 5.8), busca o crea el
aportante, crea el `Pago` en estado `pendiente`, crea el saldo si no
existía (en cero), escribe el renglón de auditoría y hace `commit()`.

**Paso 4 — El aportante ve la pantalla de confirmación** con su código
`SC-XXXXXXXX`. Hasta acá **no se movió ni un peso**.

Días después:

**Paso 5 — La Cooperadora aprieta Verificar** en el panel.

**Paso 6 — `controladores/administracion.py` → `verificar_pago()`**
Chequea el permiso y llama al servicio.

**Paso 7 — `servicios/pagos.py` → `verificar_pago()`**
Hace las tres cosas de la sección 2 y `commit()`.

```
cuota.html
    │  POST /aportante/cuota
    ▼
controladores/aportantes.py :: procesar_cuota_individual()
    │
    ▼
servicios/pagos.py :: crear_pago_de_cuota()      →  Pago(estado='pendiente')
                                                     $$$ NO se mueve

- - - - - - - - - -  días después  - - - - - - - - - -

panel.html
    │  POST /admin/pagos/<id>/verificar
    ▼
controladores/administracion.py :: verificar_pago()
    │
    ▼
servicios/pagos.py :: verificar_pago()
    ├── pago.estado = 'verificado'
    ├── servicios/fondos.py  :: registrar_movimiento()  →  $$$ entra al fondo
    └── servicios/saldos.py  :: recalcular_saldo()      →  $$$ baja la cuota
```

---

## 5. Las nueve cosas que confunden la primera vez

### 5.1 ¿Por qué existe `create_app()` en vez de `app = Flask(__name__)`?

Porque necesitamos la misma aplicación configurada de tres formas: con
SQLite para desarrollar, con una base en memoria para las pruebas y con
PostgreSQL en el servidor. `create_app('testing')` devuelve una aplicación
apuntando a la base de prueba sin tocar la de desarrollo.

Se llama *application factory* y es la forma que recomienda la documentación
de Flask.

### 5.2 ¿Por qué `db.session.flush()` y no `commit()`?

Aparece en cuatro lugares, siempre por el mismo motivo:

```python
db.session.add(pago)
db.session.flush()      # ahora pago.id existe
auditoria.registrar(..., registro_id=pago.id)
db.session.commit()     # recién acá se confirma todo junto
```

- `flush()` manda el INSERT a la base, así la fila recibe su `id`. Todavía
  se puede deshacer.
- `commit()` confirma y ya no hay vuelta atrás.

Lo hacemos así para que el pago y su renglón de auditoría se guarden juntos:
o quedan los dos, o no queda ninguno.

### 5.3 ¿Por qué el saldo se recalcula en vez de sumarse?

`recalcular_saldo()` no hace `saldo.pagado += importe`. Vuelve a buscar
todos los pagos verificados de esa persona en ese año y los suma desde cero.

Suena más lento, y lo es, pero:

- si un pago se rechaza, el saldo se arregla solo;
- si alguna vez queda mal por un error, se corrige volviendo a llamar a la
  función;
- no hay forma de que el saldo "se desincronice" de los pagos.

Es la misma idea que rehacer la suma de una columna en vez de ir tachando y
corrigiendo el total.

### 5.4 ¿Por qué el código de seguimiento y no el id?

El `id` es 1, 2, 3, 4… Si la pantalla de confirmación fuera
`/comprobante/17`, cualquiera podría escribir `/comprobante/16` y ver el
pago de otra persona. Por eso el pago se abre por un código al azar de ocho
caracteres (`SC-A3F9K2XY`).

El alfabeto del código no tiene `0`, `O`, `1`, `I` ni `L`, porque el código
se dicta por teléfono y se copia de un papel.

### 5.5 ¿Por qué los campos del pago grupal se llaman `dni_1`, `dni_2`?

Porque un checkbox destildado **no se envía**. Si las columnas viajaran como
listas (`dnis[]`, `libretas[]`), la lista de tildes vendría más corta que la
de DNI y quedaría corrida: la libreta de la persona 3 le tocaría a la 2.

Con un nombre por fila eso no puede pasar. El formulario manda además un
campo oculto `cantidad_personas`, y el controlador recorre de 1 hasta ahí:

```python
for numero in range(1, cantidad + 1):
    sufijo = '_' + str(numero)
    request.form.get('dni' + sufijo)
    request.form.get('libreta' + sufijo) == 'si'
```

El JavaScript renumera los campos cada vez que se agrega o se saca una fila
(función `renumerar()` en `cuota.html`).

### 5.6 ¿Por qué el JavaScript manda una cabecera `X-CSRFToken`?

Flask-WTF protege todos los POST con un token. En los formularios normales
el token va en un campo oculto, pero las consultas que hace el JavaScript
(validar el DNI, avisar si el número de operación ya se usó) no pasan por un
formulario.

Por eso el token está en el `<head>` de `base.html`:

```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

y `sistcoop.js` lo lee y lo manda en cada consulta. Si faltara, el servidor
contestaría **400** y las validaciones en vivo dejarían de andar sin avisar.

### 5.7 ¿Cómo se restringe una vista del panel a ciertos roles?

Con el decorador `@requiere_rol(...)` de `app/seguridad/permisos.py`, arriba
de `@login_required`:

```python
@administracion_bp.route('/auditoria')
@requiere_rol('admin', 'tesorera')
@login_required
def auditoria():
    ...
```

Antes cada vista repetía a mano un `if` contra `current_user.rol` al
principio de la función, y era fácil olvidárselo en una vista nueva: quedaba
accesible a cualquier usuario logueado. Con el decorador, una vista sin
`@requiere_rol` es visible a simple vista al leer la lista de rutas.

Sin sesión iniciada, `@requiere_rol` se comporta igual que `@login_required`
(manda al login). Con sesión pero sin ninguno de los roles pasados, avisa por
flash y redirige al portal del aportante. El mensaje del flash es
`'No tenés permisos para hacer eso.'` salvo que se pase uno distinto:
`@requiere_rol('admin', mensaje='...')`.

Toda vista nueva de `controladores/administracion.py` tiene que llevar este
decorador.

### 5.8 ¿Por qué hay un FlaskForm Y `validar_datos()` en el servicio?

`app/formularios/` controla el mismo DNI, CUIT, importe y fecha que antes
sólo controlaba `servicios/pagos.py::validar_datos()`, pero no lo duplica:
cada validador de WTForms (`app/formularios/_comunes.py`) llama a las
mismas funciones de `utilidades/validaciones.py`. La regla de qué es un DNI
válido sigue estando en un solo lugar; lo que cambió es *cuándo* se
controla.

El formulario corta antes: si el aportante escribe mal el DNI, lo ve al
toque, con el mismo mensaje que antes armaba `validar_datos()`.
`validar_datos()` se queda en el servicio porque no todo lo que crea un
pago pasa por un formulario web — un script, una carga masiva, una
integración futura le pueden pasar un diccionario directamente a
`crear_pago_de_cuota()`. El servicio no le delega su propia integridad a
una capa de afuera que podría no estar.

Los controladores le pasan al servicio datos ya tipados (`Decimal` para
importes, `date` para fechas), no strings: el formulario ya los validó, así
que el servicio no tiene que volver a parsear texto.

### 5.9 ¿Por qué las validaciones en vivo del portal están en `controladores/api.py`?

Son cuatro rutas que sólo devuelven JSON (validar DNI, validar CUIT, avisar
si un código de operación ya se usó, consultar el estado de cuota): no son
pantallas, son la API que consulta el JavaScript de los formularios
(`sistcoop.js`) mientras el aportante escribe. Viven en su propio blueprint
(`api_bp`) para no mezclarlas con las vistas que devuelven HTML.

Las URL no cambiaron: `api_bp` se registra con el mismo
`url_prefix='/aportante'` que `aportantes_bp`, así que siguen siendo
`/aportante/api/validar-dni`, etc.

---

## 6. El pago grupal, con números

Una familia transfiere **$70.000** de una sola vez para dos hermanos. La
cuota del año es **$30.000** y ninguno pagó nada todavía.

1. El servicio calcula cuánto le falta a cada uno: $30.000 y $30.000.
   **Total faltante: $60.000.**
2. Como se transfirieron $70.000 y sólo faltan $60.000, se reparten
   $60.000: **$30.000 a cada uno**.
3. Sobran **$10.000**. Ese excedente se asienta como *aporte adicional* a
   nombre de la primera persona del grupo.

¿Por qué no se devuelve? Porque la plata ya entró a la cuenta del banco y la
Cooperadora no maneja devoluciones. Si no lo asentáramos, el fondo mostraría
$60.000 y el extracto $70.000, y la conciliación del mes no cerraría.

Quedan entonces **tres** filas en `pagos`: dos de tipo `cuota_grupal` de
$30.000 y una de tipo `adicional` de $10.000. Las tres nacen `pendiente`.
Cuando la Cooperadora verifica la transferencia, se verifican las tres y
entran los $70.000 completos al fondo.

Si el reparto en partes iguales no sirve para el caso, el formulario tiene
el modo **manual**: quien carga indica cuánto le corresponde a cada uno. Los
dos topes siguen valiendo: la suma no puede superar lo transferido, y a
nadie se le asigna más de lo que debe.

---

## 7. Recetas

**Levantar el proyecto por primera vez**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
flask db upgrade              # crea las tablas (FLASK_APP=run.py)
python scripts/init_db.py     # anotá la contraseña que muestra
python run.py
```

**Antes de subir cualquier cambio**

```bash
pytest
```

Tienen que pasar todos los tests.

**Agregar un campo a una tabla**

1. Agregar la columna en el archivo de `app/modelos/`.
2. Generar la migración y aplicarla:
   ```bash
   flask db migrate -m "Agrega <columna> a <tabla>"
   ```
   Revisar a mano el archivo que queda en `migrations/versions/`: los
   índices y las restricciones con nombre no siempre se detectan solos.
   ```bash
   flask db upgrade
   ```
3. Mostrarla en la plantilla que corresponda.

**Agregar una pantalla nueva**

1. Escribir la función en el controlador del blueprint que corresponda.
2. Crear el `.html` en `app/vistas/`, con `{% extends "base.html" %}`.
3. Si la pantalla modifica datos, la modificación va en un servicio, no en
   el controlador.

**Empezar el ejercicio del año que viene**
Panel → Nuevo ejercicio. Se cierra el anterior y se abre el nuevo con la
cuota que votó la asamblea.

---

## 8. Glosario

| Palabra | Qué significa acá |
| ------- | ----------------- |
| **Aportante** | Quien le transfiere plata a la Cooperadora |
| **Ejercicio** | El año contable, con su cuota |
| **Cuota** | Lo que se paga por año, votado en asamblea. Es voluntaria |
| **Fondo** | Un "bolsillo": el general y uno por carrera |
| **Movimiento** | Un renglón que explica un cambio de saldo de un fondo |
| **Saldo** | Cuánto lleva pagado una persona en un ejercicio |
| **Verificar** | Confirmar contra el banco. Es lo único que acredita |
| **Código de seguimiento** | El `SC-XXXXXXXX` con el que se consulta un pago |
| **Blueprint** | Un grupo de rutas de Flask. Tenemos cinco |
| **Modelo** | Una clase que representa una tabla |
| **Servicio** | Una función que aplica una regla del negocio |
| **Migración** | Cambiarle la estructura a una base que ya tiene datos |
| **CSRF** | Protección contra formularios enviados desde otro sitio |
| **Hash** | Huella de un archivo. Dos archivos iguales dan la misma |

---