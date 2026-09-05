"""Módulo Aportante — el portal público.

No pide inicio de sesión: el aportante es alguien de afuera que entra una o
dos veces al año a subir un comprobante. Por eso todas las vistas de acá
tienen tres cuidados:

- se valida en el servidor todo lo que llega, aunque el navegador ya lo haya
  validado (RNF-03);
- las pantallas de consulta tienen tope de consultas por IP;
- los pagos se abren por código de seguimiento y no por id, así nadie puede
  leer pagos ajenos cambiando un número.

Un controlador sólo hace tres cosas: leer el formulario, llamar al servicio
que corresponde y mostrar la pantalla. Las reglas de negocio están en
app/servicios/.
"""

from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app)

from app.constantes import ANIOS
from app.extensions import db
from app.modelos.aportantes import Aportante
from app.modelos.carreras import Carrera
from app.modelos.ejercicios import Ejercicio
from app.modelos.pagos import Pago, generar_codigo
from app.modelos.pagos_grupales import PagoGrupal
from app.modelos.saldos import SaldoAportante
from app.modelos.solicitudes import SolicitudFondo
from app.servicios import auditoria
from app.servicios import pagos as servicio_pagos
from app.servicios import pagos_grupales as servicio_grupales
from app.servicios.pagos import ErrorDeCarga
from app.utilidades import validaciones
from app.utilidades.archivos import ArchivoInvalido, guardar_comprobante
from app.utilidades.limite_peticiones import excede_limite
from app.utilidades.peticion import ip_y_user_agent

aportantes_bp = Blueprint('aportantes', __name__)


# ============================================
# FUNCIONES QUE USAN VARIAS VISTAS
# ============================================

def leer_comprobante(campo='comprobante'):
    """Guarda el archivo del formulario y devuelve los datos para el pago."""
    guardado = guardar_comprobante(request.files.get(campo))
    return {
        'comprobante_nombre': guardado['nombre'],
        'hash_comprobante': guardado['hash'],
    }


def mostrar_errores(error):
    """Manda a pantalla los mensajes de un ErrorDeCarga o de un ArchivoInvalido."""
    mensajes = getattr(error, 'errores', None)
    if not mensajes:
        mensajes = [str(error)]
    for mensaje in mensajes:
        flash(mensaje, 'danger')


def datos_del_formulario(**extra):
    """Lo que necesitan todas las plantillas de formulario."""
    datos = {
        'carreras': Carrera.get_carreras_activas(),
        'anios': ANIOS,
        'cuota': Ejercicio.get_cuota_vigente(),
        'data': request.form if request.method == 'POST' else {},
    }
    datos.update(extra)
    return datos


def error_inesperado(mensaje_de_log, mensaje_al_aportante):
    """Deshace lo que quedó a medias y deja el detalle técnico en el log.

    Al aportante no se le muestra el error interno: no lo ayuda y puede
    revelar cómo está armado el sistema por dentro.
    """
    db.session.rollback()
    current_app.logger.exception(mensaje_de_log)
    flash(mensaje_al_aportante, 'danger')


# ============================================
# INICIO
# ============================================

@aportantes_bp.route('/')
def inicio():
    return render_template(
        'aportante/inicio.html',
        cuota=Ejercicio.get_cuota_vigente(),
        ejercicio=Ejercicio.get_ejercicio_vigente()
    )


# ============================================
# CUOTA DE SOCIO (RF-01, RF-02)
# ============================================

@aportantes_bp.route('/cuota', methods=['GET', 'POST'])
def pagar_cuota():
    if request.method == 'GET':
        return render_template('aportante/cuota.html', **datos_del_formulario())

    if request.form.get('es_grupal') == 'true':
        return procesar_cuota_grupal()
    return procesar_cuota_individual()


def procesar_cuota_individual():
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'apellido': request.form.get('apellido'),
            'dni': request.form.get('dni'),
            'carrera_id': request.form.get('carrera_id') or None,
            'anio': request.form.get('anio') or None,
            'importe': request.form.get('importe'),
            'fecha': request.form.get('fecha'),
            'codigo_transaccion': request.form.get('codigo_transaccion'),
            'observaciones': request.form.get('observaciones'),
            'solicita_libreta': request.form.get('solicita_libreta') == 'true',
        }
        data.update(leer_comprobante())

        ip, user_agent = ip_y_user_agent()
        pago, saldo = servicio_pagos.crear_pago_de_cuota(data, ip=ip, user_agent=user_agent)
        return redirect(url_for('aportantes.exito', codigo=pago.codigo_seguimiento))

    except (ErrorDeCarga, ArchivoInvalido) as error:
        mostrar_errores(error)
    except Exception:
        error_inesperado('Error al cargar un pago de cuota',
                         'No pudimos registrar el pago. Probá de nuevo en unos '
                         'minutos o escribile a la Cooperadora.')

    return render_template('aportante/cuota.html', **datos_del_formulario()), 400


def leer_personas_del_formulario():
    """Arma la lista de personas del pago grupal.

    Cada fila del formulario tiene sus campos numerados (dni_1, nombre_1,
    monto_1, y así). El campo oculto cantidad_personas dice hasta qué número
    hay que leer. Lo hacemos con nombres numerados y no con listas porque un
    checkbox destildado no se envía: si fueran listas, las tildes de la
    libreta quedarían corridas respecto de las demás columnas.

    Devuelve (personas, montos).
    """
    try:
        cantidad = int(request.form.get('cantidad_personas', 0))
    except (ValueError, TypeError):
        cantidad = 0

    # Tope de seguridad: nadie manda un pago grupal de 200 personas, y sin
    # tope alguien podría mandar un número enorme para hacer trabajar de más
    # al servidor.
    if cantidad > 50:
        cantidad = 50

    personas = []
    montos = []

    for numero in range(1, cantidad + 1):
        sufijo = '_' + str(numero)
        personas.append({
            'dni': request.form.get('dni' + sufijo, ''),
            'nombre': request.form.get('nombre' + sufijo, ''),
            'apellido': request.form.get('apellido' + sufijo, ''),
            'carrera_id': request.form.get('carrera' + sufijo) or None,
            'anio': request.form.get('anio' + sufijo) or None,
            'solicita_libreta': request.form.get('libreta' + sufijo) == 'si',
        })
        montos.append(request.form.get('monto' + sufijo, ''))

    return personas, montos


def procesar_cuota_grupal():
    try:
        personas, montos = leer_personas_del_formulario()

        data = {
            'codigo_transaccion': request.form.get('codigo_transaccion'),
            'importe_total': request.form.get('importe_total'),
            'fecha': request.form.get('fecha'),
            'personas': personas,
            'tipo_distribucion': request.form.get('tipo_distribucion', 'auto'),
            'montos': montos,
        }
        data.update(leer_comprobante('comprobante'))

        ip, user_agent = ip_y_user_agent()
        grupal, resumen = servicio_grupales.procesar_pago_grupal(data, ip=ip, user_agent=user_agent)
        return redirect(url_for('aportantes.exito_grupal',
                                codigo=grupal.codigo_seguimiento))

    except (ErrorDeCarga, ArchivoInvalido) as error:
        mostrar_errores(error)
    except Exception:
        error_inesperado('Error al cargar un pago grupal',
                         'No pudimos registrar el pago grupal. Probá de nuevo '
                         'en unos minutos.')

    return render_template('aportante/cuota.html',
                           **datos_del_formulario(es_grupal=True)), 400


# ============================================
# APORTES ADICIONALES (RF-11) Y A FONDO DE CARRERA (RF-09)
# ============================================

@aportantes_bp.route('/adicional', methods=['GET', 'POST'])
def aporte_adicional():
    if request.method == 'GET':
        return render_template('aportante/adicional.html', **datos_del_formulario())

    # La solapa que eligió el aportante decide a qué fondo va la plata
    if request.form.get('tipo_aporte') == 'carrera':
        destino = 'carrera'
        tipo = 'aporte_carrera'
    else:
        destino = 'capital'
        tipo = 'adicional'

    try:
        data = {
            'nombre': request.form.get('nombre'),
            'apellido': request.form.get('apellido'),
            'dni': request.form.get('dni'),
            'cuit': request.form.get('cuit'),
            'carrera_id': request.form.get('carrera_id') or None,
            'destino': destino,
            'carrera_destino_id': request.form.get('carrera_id') or None,
            'tipo': tipo,
            'importe': request.form.get('importe'),
            'fecha': request.form.get('fecha'),
            'codigo_transaccion': request.form.get('codigo_transaccion'),
            'observaciones': request.form.get('observaciones'),
        }
        data.update(leer_comprobante())

        ip, user_agent = ip_y_user_agent()
        pago = servicio_pagos.crear_pago_publico(data, ip=ip, user_agent=user_agent)
        return redirect(url_for('aportantes.exito', codigo=pago.codigo_seguimiento))

    except (ErrorDeCarga, ArchivoInvalido) as error:
        mostrar_errores(error)
    except Exception:
        error_inesperado('Error al cargar un aporte adicional',
                         'No pudimos registrar el aporte. Probá de nuevo en '
                         'unos minutos.')

    return render_template('aportante/adicional.html',
                           **datos_del_formulario(tab_activa=destino)), 400


# ============================================
# SOLICITUDES
# ============================================

@aportantes_bp.route('/solicitud', methods=['GET', 'POST'])
def solicitud():
    if request.method == 'GET':
        return render_template('aportante/solicitud.html', **datos_del_formulario())

    if request.form.get('tipo_solicitud') == 'libreta':
        return procesar_solicitud_libreta()
    return procesar_solicitud_fondos()


MOTIVOS_LIBRETA = {
    'extravio': 'Extravío',
    'rotura': 'Rotura',
    'robo': 'Robo',
    'otro': 'Otro',
}


def procesar_solicitud_libreta():
    """Duplicado de libreta.

    Lo guardamos como un Pago porque en la práctica lo es: tiene importe,
    comprobante y número de operación, y la Cooperadora lo tiene que verificar
    igual que cualquier otro ingreso.
    """
    try:
        motivo = request.form.get('motivo', '')
        texto = 'Motivo: ' + MOTIVOS_LIBRETA.get(motivo, 'no especificado')

        aclaracion = (request.form.get('observaciones') or '').strip()
        if aclaracion:
            texto = texto + ' | ' + aclaracion

        data = {
            'nombre': request.form.get('nombre'),
            'apellido': request.form.get('apellido'),
            'dni': request.form.get('dni'),
            'carrera_id': request.form.get('carrera_id') or None,
            'anio': request.form.get('anio') or None,
            'tipo': 'libreta_duplicado',
            'importe': request.form.get('importe'),
            'fecha': request.form.get('fecha'),
            'codigo_transaccion': request.form.get('codigo_transaccion'),
            'observaciones': texto,
            'solicita_libreta': True,
        }
        data.update(leer_comprobante())

        ip, user_agent = ip_y_user_agent()
        pago = servicio_pagos.crear_pago_publico(data, ip=ip, user_agent=user_agent)
        return redirect(url_for('aportantes.exito', codigo=pago.codigo_seguimiento))

    except (ErrorDeCarga, ArchivoInvalido) as error:
        mostrar_errores(error)
    except Exception:
        error_inesperado('Error al registrar una solicitud de libreta',
                         'No pudimos registrar la solicitud. Probá de nuevo en '
                         'unos minutos.')

    return render_template('aportante/solicitud.html',
                           **datos_del_formulario(tab_activa='libreta')), 400


def validar_solicitud_de_fondos():
    """Controla el formulario de pedido de fondos. Devuelve la lista de errores."""
    errores = []

    if not (request.form.get('responsable') or '').strip():
        errores.append('Falta el nombre del responsable.')
    if not (request.form.get('contacto') or '').strip():
        errores.append('Falta un teléfono o correo de contacto.')
    if not (request.form.get('concepto') or '').strip():
        errores.append('Falta el concepto de la solicitud.')

    justificacion = (request.form.get('justificacion') or '').strip()
    if len(justificacion) < 20:
        errores.append('La justificación tiene que explicar el pedido: escribí '
                       'al menos un par de renglones.')

    if request.form.get('tipo') not in ('fondos', 'evento', 'viaje'):
        errores.append('Elegí qué estás solicitando.')

    importe_ok, mensaje = validaciones.validar_importe(request.form.get('importe'))
    if not importe_ok:
        errores.append(mensaje)

    if request.form.get('fecha_estimada'):
        fecha_ok, mensaje = validaciones.validar_fecha(request.form['fecha_estimada'])
        if not fecha_ok:
            errores.append(mensaje)

    return errores


def procesar_solicitud_fondos():
    """Pedido de fondos, evento o viaje de un curso o un docente."""
    try:
        errores = validar_solicitud_de_fondos()
        if errores:
            raise ErrorDeCarga(errores)

        fecha_estimada = request.form.get('fecha_estimada')
        if fecha_estimada:
            fecha = datetime.strptime(fecha_estimada, '%Y-%m-%d').date()
        else:
            fecha = None

        pedido = SolicitudFondo(
            codigo_seguimiento=generar_codigo('SF'),
            responsable=request.form['responsable'].strip(),
            contacto=request.form['contacto'].strip(),
            carrera_id=request.form.get('carrera_id') or None,
            curso=(request.form.get('curso') or '').strip() or None,
            tipo=request.form['tipo'],
            concepto=request.form['concepto'].strip(),
            importe_estimado=round(float(request.form['importe']), 2),
            fecha_estimada=fecha,
            justificacion=request.form['justificacion'].strip()
        )
        db.session.add(pedido)
        # flush() manda el INSERT a la base y le asigna el id a la fila, pero
        # todavía no confirma nada: eso lo hace el commit del final.
        db.session.flush()

        ip, user_agent = ip_y_user_agent()
        auditoria.registrar(
            usuario='portal-publico',
            accion='cargar_solicitud_fondos',
            tabla='solicitudes_fondo',
            registro_id=pedido.id,
            detalle={'codigo_seguimiento': pedido.codigo_seguimiento,
                     'tipo': pedido.tipo},
            ip=ip,
            user_agent=user_agent
        )
        db.session.commit()

        return redirect(url_for('aportantes.exito_solicitud',
                                codigo=pedido.codigo_seguimiento))

    except ErrorDeCarga as error:
        mostrar_errores(error)
    except Exception:
        error_inesperado('Error al registrar una solicitud de fondos',
                         'No pudimos registrar la solicitud. Probá de nuevo en '
                         'unos minutos.')

    return render_template('aportante/solicitud.html', **datos_del_formulario()), 400


# ============================================
# PANTALLAS DE CONFIRMACIÓN (RF-19)
# ============================================

@aportantes_bp.route('/comprobante/<codigo>')
def exito(codigo):
    """Confirmación de la carga, buscada por código de seguimiento.

    Antes esta ruta recibía el id del pago. Como el id es correlativo,
    cualquiera podía ir cambiando el número y ver pagos de otras personas.
    """
    pago = Pago.get_by_codigo_seguimiento(codigo)
    if not pago:
        flash('No encontramos ese comprobante. Revisá el código.', 'warning')
        return redirect(url_for('aportantes.inicio'))

    saldo = None
    if pago.ejercicio_id:
        saldo = SaldoAportante.get_por_aportante(pago.aportante_id, pago.ejercicio_id)

    return render_template('aportante/ok.html', pago=pago, saldo=saldo)


@aportantes_bp.route('/comprobante-grupal/<codigo>')
def exito_grupal(codigo):
    grupal = PagoGrupal.get_by_codigo_seguimiento(codigo)
    if not grupal:
        flash('No encontramos esa transferencia. Revisá el código.', 'warning')
        return redirect(url_for('aportantes.inicio'))
    return render_template('aportante/ok_grupal.html', pago=grupal)


@aportantes_bp.route('/solicitud/<codigo>')
def exito_solicitud(codigo):
    pedido = SolicitudFondo.get_by_codigo_seguimiento(codigo)
    if not pedido:
        flash('No encontramos esa solicitud. Revisá el código.', 'warning')
        return redirect(url_for('aportantes.inicio'))
    return render_template('aportante/ok_solicitud.html', solicitud=pedido)


# ============================================
# SEGUIMIENTO
# ============================================

@aportantes_bp.route('/seguimiento', methods=['GET', 'POST'])
def seguimiento():
    """Consulta del estado de los aportes.

    Se puede buscar de dos formas: por código de seguimiento, que no expone
    ningún dato, o por DNI, que es lo que pidió el cliente para ver todo el
    historial. La búsqueda tiene tope de consultas, porque si no alguien
    podría ir probando documentos para ver quién pagó (RNF-02).
    """
    contexto = {
        'pagos': [], 'saldo': None, 'dni': None, 'codigo': None,
        'pago_unico': None, 'grupal': None, 'solicitud': None,
    }

    if request.method == 'GET':
        return render_template('aportante/seguimiento.html', **contexto)

    if excede_limite('seguimiento', limite=15, ventana=60):
        flash('Hiciste muchas consultas seguidas. Esperá un minuto y volvé a '
              'intentar.', 'warning')
        return render_template('aportante/seguimiento.html', **contexto)

    if request.form.get('modo') == 'codigo':
        return buscar_por_codigo(contexto)
    return buscar_por_dni(contexto)


def buscar_por_codigo(contexto):
    codigo = (request.form.get('codigo') or '').strip().upper()
    contexto['codigo'] = codigo

    pago = Pago.get_by_codigo_seguimiento(codigo)
    if pago:
        contexto['pago_unico'] = pago
        if pago.ejercicio_id:
            contexto['saldo'] = SaldoAportante.get_por_aportante(
                pago.aportante_id, pago.ejercicio_id)
        return render_template('aportante/seguimiento.html', **contexto)

    grupal = PagoGrupal.get_by_codigo_seguimiento(codigo)
    if grupal:
        contexto['grupal'] = grupal
        return render_template('aportante/seguimiento.html', **contexto)

    pedido = SolicitudFondo.get_by_codigo_seguimiento(codigo)
    if pedido:
        contexto['solicitud'] = pedido
        return render_template('aportante/seguimiento.html', **contexto)

    flash('No encontramos nada con ese código. Fijate que esté completo.', 'warning')
    return render_template('aportante/seguimiento.html', **contexto)


def buscar_por_dni(contexto):
    dni = validaciones.limpiar_dni(request.form.get('dni'))
    contexto['dni'] = dni

    if not validaciones.validar_dni(dni):
        flash('Ingresá un DNI válido, sin puntos.', 'warning')
        return render_template('aportante/seguimiento.html', **contexto)

    aportante = Aportante.get_by_dni(dni)
    if not aportante:
        flash('No hay aportes cargados con ese DNI.', 'info')
        return render_template('aportante/seguimiento.html', **contexto)

    contexto['pagos'] = Pago.query.filter_by(
        aportante_id=aportante.id
    ).order_by(Pago.created_at.desc()).all()

    ejercicio = Ejercicio.get_ejercicio_vigente()
    if ejercicio:
        contexto['saldo'] = SaldoAportante.get_por_aportante(aportante.id, ejercicio.id)

    return render_template('aportante/seguimiento.html', **contexto)


# ============================================
# RUTAS QUE USA EL JAVASCRIPT DE LOS FORMULARIOS
# ============================================
#
# Son todas POST, así que Flask-WTF les pide el token CSRF. El JavaScript lo
# manda en la cabecera X-CSRFToken (ver sistcoop.js). Si no lo mandara, el
# servidor contestaría 400 y ninguna validación en vivo funcionaría.

@aportantes_bp.route('/api/validar-dni', methods=['POST'])
def api_validar_dni():
    """Dice si el DNI tiene formato válido.

    No devuelve ningún dato de la persona. La versión anterior devolvía
    nombre, apellido y carrera de cualquier DNI, así que probando números se
    podía armar un padrón de alumnos (RNF-02).
    """
    if excede_limite('api_dni', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    valido = validaciones.validar_dni(datos.get('dni', ''))

    return jsonify({
        'valido': valido,
        'mensaje': '' if valido else 'El DNI tiene que tener 7 u 8 dígitos, sin puntos.'
    })


@aportantes_bp.route('/api/validar-cuit', methods=['POST'])
def api_validar_cuit():
    if excede_limite('api_cuit', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    cuit = datos.get('cuit', '')
    valido = validaciones.validar_cuit(cuit)

    return jsonify({
        'valido': valido,
        'formateado': validaciones.formatear_cuit(cuit) if valido else None,
        'mensaje': 'CUIT válido' if valido
                   else 'El CUIT no es válido. Revisá el dígito verificador.'
    })


@aportantes_bp.route('/api/validar-transaccion', methods=['POST'])
def api_validar_transaccion():
    """Avisa si el número de operación ya se usó (RF-04)."""
    if excede_limite('api_transaccion', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    en_uso = servicio_pagos.codigo_transaccion_en_uso((datos.get('codigo') or '').strip())

    return jsonify({
        'disponible': not en_uso,
        'mensaje': 'Ese número ya fue cargado en otro pago.' if en_uso
                   else 'El número no figura cargado.'
    })


@aportantes_bp.route('/api/estado-cuota', methods=['POST'])
def api_estado_cuota():
    """Cómo viene la cuota del DNI en el ejercicio vigente.

    Alimenta el cuadro que el aportante ve antes de mandar el formulario.
    Devuelve importes, nunca datos personales.
    """
    if excede_limite('api_estado', limite=20, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    dni = datos.get('dni', '')

    if not validaciones.validar_dni(dni):
        return jsonify({'disponible': False})

    estado = servicio_pagos.estado_de_cuota(dni)
    if not estado:
        return jsonify({'disponible': False})

    estado['disponible'] = True
    return jsonify(estado)
