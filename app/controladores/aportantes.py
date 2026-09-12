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

import hashlib
from decimal import Decimal

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)

from app.constantes import ANIOS
from app.extensions import db
from app.formularios.adicional import FormularioAporteCarrera, FormularioAporteGeneral
from app.formularios.cuota import FormularioCuotaGrupal, FormularioCuotaIndividual
from app.formularios.solicitudes import FormularioDuplicadoLibreta, FormularioSolicitudFondos
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
from app.utilidades.archivos import ArchivoInvalido, guardar_comprobante, ruta_comprobante
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


def leer_comprobante_o_reusar(campo='comprobante'):
    """Si se adjuntó un archivo nuevo lo procesa; si no, reusa el que ya se
    había guardado en un intento anterior del mismo formulario.

    Evita que un reintento por otro error (código de operación repetido, una
    persona mal cargada, etc.) obligue a volver a elegir el comprobante, y
    evita guardar una segunda copia del mismo archivo en disco.

    La huella nunca se toma del campo oculto que manda el navegador -eso no
    es de confiar-: se recalcula leyendo el archivo real que ya está en
    disco, así que no hay forma de declarar un comprobante que no existe.
    """
    archivo = request.files.get(campo)
    if archivo and archivo.filename:
        datos = leer_comprobante(campo)
        # Sólo para mostrarlo en pantalla si hay que reintentar: el nombre
        # real que la persona le puso al archivo, no el generado al azar
        # con el que se guarda en disco.
        datos['comprobante_nombre_original'] = archivo.filename
        return datos

    nombre_previo = (request.form.get('comprobante_nombre_previo') or '').strip()
    nombre_original_previo = (request.form.get('comprobante_nombre_original_previo') or '').strip()
    ruta = ruta_comprobante(nombre_previo) if nombre_previo else None
    if ruta:
        with open(ruta, 'rb') as comprobante:
            huella = hashlib.sha256(comprobante.read()).hexdigest()
        return {
            'comprobante_nombre': nombre_previo,
            'hash_comprobante': huella,
            'comprobante_nombre_original': nombre_original_previo or nombre_previo,
        }

    raise ArchivoInvalido('Tenés que adjuntar el comprobante de la transferencia.')


def mostrar_errores(error):
    """Manda a pantalla los mensajes de un ErrorDeCarga o de un ArchivoInvalido."""
    mensajes = getattr(error, 'errores', None)
    if not mensajes:
        mensajes = [str(error)]
    for mensaje in mensajes:
        flash(mensaje, 'danger')


def mostrar_errores_de_formulario(formulario):
    """Mismo patrón que mostrar_errores(): un flash por cada mensaje."""
    for errores_campo in formulario.errors.values():
        for mensaje in errores_campo:
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
    formulario = FormularioCuotaIndividual()
    if not formulario.validate_on_submit():
        mostrar_errores_de_formulario(formulario)
        return render_template('aportante/cuota.html', **datos_del_formulario()), 400

    try:
        data = {
            'nombre': formulario.nombre.data,
            'apellido': formulario.apellido.data,
            'dni': formulario.dni.data,
            'carrera_id': formulario.carrera_id.data or None,
            'anio': formulario.anio.data or None,
            'importe': Decimal(formulario.importe.data),
            'fecha': (validaciones.texto_a_fecha(formulario.fecha.data)
                     if formulario.fecha.data else None),
            'codigo_transaccion': formulario.codigo_transaccion.data,
            'observaciones': formulario.observaciones.data,
            'solicita_libreta': formulario.solicita_libreta.data == 'true',
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
    formulario = FormularioCuotaGrupal()

    errores = []

    # 1. Errores del FlaskForm
    formulario.validate_on_submit()

    for errores_campo in formulario.errors.values():
        errores.extend(errores_campo)


    # 2. Fecha
    if not formulario.fecha.data:
        errores.append('Debe ingresar una fecha válida.')


    # 3. Personas
    personas, montos = leer_personas_del_formulario()

    _, errores_personas = servicio_grupales.normalizar_personas(personas)
    errores.extend(errores_personas)

    # 4. Comprobante: se lee (o se reusa el de un intento anterior) ACÁ, antes
    # de saber si alguna otra validación de más abajo falla, para que quede
    # guardado sin importar cuál sea el motivo del rechazo. Así un reintento
    # por cualquier otro error (una persona incompleta, el n° de operación
    # vacío, lo que sea) no lo pierde ni lo vuelve a pedir.
    datos_comprobante = None
    comprobante_nombre_para_mostrar = (request.form.get('comprobante_nombre_previo') or '').strip() or None
    comprobante_nombre_original_para_mostrar = (
        request.form.get('comprobante_nombre_original_previo') or ''
    ).strip() or None
    try:
        datos_comprobante = leer_comprobante_o_reusar('comprobante')
        comprobante_nombre_para_mostrar = datos_comprobante['comprobante_nombre']
        comprobante_nombre_original_para_mostrar = datos_comprobante.get('comprobante_nombre_original')
    except ArchivoInvalido as error:
        errores.append(str(error))

    # 5. N° operación

    if not (formulario.codigo_transaccion.data or '').strip():
        errores.append('El número de operación es obligatorio.')

    if errores:
        for error in errores:
            flash(error, 'danger')

        return render_template(
            'aportante/cuota.html',
            **datos_del_formulario(es_grupal=True,
                                   comprobante_nombre=comprobante_nombre_para_mostrar,
                                   comprobante_nombre_original=comprobante_nombre_original_para_mostrar)
        ), 400

    try:

        data = {
            'codigo_transaccion': formulario.codigo_transaccion.data,
            'importe_total': Decimal(formulario.importe_total.data),
            'fecha': (validaciones.texto_a_fecha(formulario.fecha.data)
                     if formulario.fecha.data else None),
            'personas': personas,
            'tipo_distribucion': formulario.tipo_distribucion.data or 'auto',
            'montos': montos,
        }
        data.update(datos_comprobante)

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
                           **datos_del_formulario(es_grupal=True,
                                                  comprobante_nombre=comprobante_nombre_para_mostrar,
                                                  comprobante_nombre_original=comprobante_nombre_original_para_mostrar)), 400


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
        formulario = FormularioAporteCarrera()
    else:
        destino = 'capital'
        tipo = 'adicional'
        formulario = FormularioAporteGeneral()

    if not formulario.validate_on_submit():
        mostrar_errores_de_formulario(formulario)
        return render_template('aportante/adicional.html',
                               **datos_del_formulario(tab_activa=destino)), 400

    try:
        carrera_id = formulario.carrera_id.data or None if destino == 'carrera' else None
        data = {
            'nombre': formulario.nombre.data,
            'apellido': formulario.apellido.data,
            'dni': formulario.dni.data,
            'cuit': formulario.cuit.data,
            'carrera_id': carrera_id,
            'destino': destino,
            'carrera_destino_id': carrera_id,
            'tipo': tipo,
            'importe': Decimal(formulario.importe.data),
            'fecha': (validaciones.texto_a_fecha(formulario.fecha.data)
                     if formulario.fecha.data else None),
            'codigo_transaccion': formulario.codigo_transaccion.data,
            'observaciones': formulario.observaciones.data,
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
    formulario = FormularioDuplicadoLibreta()
    if not formulario.validate_on_submit():
        mostrar_errores_de_formulario(formulario)
        return render_template('aportante/solicitud.html',
                               **datos_del_formulario(tab_activa='libreta')), 400

    try:
        motivo = formulario.motivo.data or ''
        texto = 'Motivo: ' + MOTIVOS_LIBRETA.get(motivo, 'no especificado')

        aclaracion = (formulario.observaciones.data or '').strip()
        if aclaracion:
            texto = texto + ' | ' + aclaracion

        data = {
            'nombre': formulario.nombre.data,
            'apellido': formulario.apellido.data,
            'dni': formulario.dni.data,
            'carrera_id': formulario.carrera_id.data or None,
            'anio': formulario.anio.data or None,
            'tipo': 'libreta_duplicado',
            'importe': Decimal(formulario.importe.data),
            'fecha': (validaciones.texto_a_fecha(formulario.fecha.data)
                     if formulario.fecha.data else None),
            'codigo_transaccion': formulario.codigo_transaccion.data,
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


def procesar_solicitud_fondos():
    """Pedido de fondos, evento o viaje de un curso o un docente."""
    formulario = FormularioSolicitudFondos()
    if not formulario.validate_on_submit():
        mostrar_errores_de_formulario(formulario)
        return render_template('aportante/solicitud.html', **datos_del_formulario()), 400

    try:
        fecha_estimada = (validaciones.texto_a_fecha(formulario.fecha_estimada.data)
                          if formulario.fecha_estimada.data else None)

        pedido = SolicitudFondo(
            codigo_seguimiento=generar_codigo('SF'),
            responsable=formulario.responsable.data,
            contacto=formulario.contacto.data,
            carrera_id=formulario.carrera_id.data or None,
            curso=formulario.curso.data or None,
            tipo=formulario.tipo.data,
            concepto=formulario.concepto.data,
            importe_estimado=Decimal(str(round(float(formulario.importe.data), 2))),
            fecha_estimada=fecha_estimada,
            justificacion=formulario.justificacion.data
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
        'paginacion':None,
    }

    # El DNI llega por GET (para que el link de "página siguiente" pueda
    # reenviarlo en la URL); el código, por POST, como antes.
    if request.method == 'GET' and not request.args.get('dni'):
        return render_template('aportante/seguimiento.html', **contexto)

    if excede_limite('seguimiento', limite=15, ventana=60):
        flash('Hiciste muchas consultas seguidas. Esperá un minuto y volvé a '
              'intentar.', 'warning')
        return render_template('aportante/seguimiento.html', **contexto)

    if request.method == 'POST' and request.form.get('modo') == 'codigo':
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
        contexto['pagos'] = Pago.query.filter_by(
            aportante_id=pago.aportante_id
        ).order_by(Pago.created_at.desc()).all()
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
    # request.values junta el DNI venga por querystring (GET, para poder
    # paginar) o por formulario (POST, la búsqueda inicial).
    dni = validaciones.limpiar_dni(request.values.get('dni'))
    contexto['dni'] = dni

    if not validaciones.validar_dni(dni):
        flash('Ingresá un DNI válido, sin puntos.', 'warning')
        return render_template('aportante/seguimiento.html', **contexto)

    aportante = Aportante.get_by_dni(dni)
    if not aportante:
        flash('No hay aportes cargados con ese DNI.', 'info')
        return render_template('aportante/seguimiento.html', **contexto)

    pagina = request.values.get('pagina', 1, type=int)
    paginacion = Pago.get_por_aportante(aportante.id, pagina)
    contexto['pagos'] = paginacion.items
    contexto['paginacion'] = paginacion

    ejercicio = Ejercicio.get_ejercicio_vigente()
    if ejercicio:
        contexto['saldo'] = SaldoAportante.get_por_aportante(aportante.id, ejercicio.id)

    return render_template('aportante/seguimiento.html', **contexto)
