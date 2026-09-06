"""Reglas de negocio de los pagos individuales.

REGLA PRINCIPAL DEL MÓDULO: cargar un comprobante NO acredita plata.
El pago nace 'pendiente' y no toca ningún saldo. Recién impacta cuando la
Cooperadora lo verifica contra el movimiento real del banco (RF-03), y ahí
sí suma al fondo (RF-08) y al saldo de cuota del aportante.

Son funciones sueltas. Cada una que modifica datos termina con un
db.session.commit(), así se ve dónde empieza y dónde termina la operación.
"""

import uuid
from datetime import datetime

from app.extensions import db
from app.modelos.aportantes import Aportante
from app.modelos.ejercicios import Ejercicio
from app.modelos.pagos import Pago, generar_codigo
from app.modelos.pagos_grupales import PagoGrupal
from app.modelos.saldos import SaldoAportante
from app.servicios import auditoria, fondos, saldos
from app.utilidades import validaciones


class ErrorDeCarga(Exception):
    """Un pago no se pudo registrar.

    Guarda la lista de mensajes que hay que mostrarle al aportante. El
    servicio no arma HTML ni redirige: sólo avisa qué salió mal, y el
    controlador decide cómo mostrarlo.
    """

    def __init__(self, errores):
        if isinstance(errores, str):
            errores = [errores]
        self.errores = errores
        super().__init__(' / '.join(errores))


# ============================================
# NÚMERO DE OPERACIÓN Y COMPROBANTE
# ============================================

def generar_codigo_transaccion():
    """Número interno, para cuando el aportante no informa el del banco."""
    fecha = datetime.now().strftime('%Y%m%d')
    return 'SIST-' + fecha + '-' + uuid.uuid4().hex[:8].upper()


def codigo_transaccion_en_uso(codigo):
    """¿Este número de operación ya se cargó?

    Hay que mirar las DOS tablas donde puede estar: los pagos individuales y
    las transferencias grupales. Si sólo miráramos una, el mismo comprobante
    se podría cargar dos veces alternando el tipo de pago (RF-04).
    """
    if not codigo:
        return False
    if Pago.get_by_transaccion(codigo):
        return True
    if PagoGrupal.get_by_transaccion(codigo):
        return True
    return False


def comprobante_ya_usado(huella):
    """Devuelve el pago que ya usó este mismo archivo, o None (RF-04)."""
    if not huella:
        return None
    pago = Pago.get_by_hash_comprobante(huella)
    if pago:
        return pago
    return PagoGrupal.get_by_hash_comprobante(huella)


# ============================================
# VALIDACIONES DEL FORMULARIO
# ============================================

def validar_datos(data, pide_apellido=True):
    """Controles comunes a cualquier alta de pago. Devuelve la lista de errores."""
    errores = []

    nombre = (data.get('nombre') or '').strip()

    if not nombre:
        errores.append('Falta el nombre.')
    elif not validaciones.validar_nombre(nombre):
        errores.append('El nombre solo admite caracteres alfabéticos.')

    apellido = (data.get('apellido') or '').strip()

    if pide_apellido:
        if not apellido:
            errores.append('Falta el apellido.')
        elif not validaciones.validar_nombre(apellido):
            errores.append('El apellido solo admite caracteres alfabéticos.')

    dni = (data.get('dni') or '').strip()
    if not dni:
        errores.append('Falta el DNI.')
    elif not validaciones.validar_dni(dni):
        errores.append('El DNI no es válido: tiene que tener 7 u 8 dígitos, sin puntos.')

    importe_ok, mensaje = validaciones.validar_importe(data.get('importe'))
    if not importe_ok:
        errores.append(mensaje)

    if not data.get('fecha'):
        errores.append('Falta la fecha.')
    else:
        fecha_ok, mensaje = validaciones.validar_fecha_transferencia(data['fecha'])
        if not fecha_ok:
            errores.append(mensaje)

    cuit = (data.get('cuit') or '').strip()
    if cuit and not validaciones.validar_cuit(cuit):
        errores.append('El CUIT no es válido. Revisá el número, incluido el '
                       'dígito verificador.')

    if data.get('destino') == 'carrera':
        if not data.get('carrera_destino_id'):
            errores.append('Debe seleccionar una carrera.')
        
    return errores


def validar_operacion_y_comprobante(data):
    """Controla que no se estén cargando dos veces la misma transferencia."""
    errores = []

    codigo = (data.get('codigo_transaccion') or '').strip()

    if not codigo:
        errores.append(
            'El número de operación es obligatorio.'
        )
    else:
        data['codigo_transaccion'] = codigo

        if not codigo.isalnum():
            errores.append(
                'El número de operación sólo puede contener letras y números.'
            )

        elif len(codigo) < 8 or len(codigo) > 30:
            errores.append(
                'El número de operación debe tener entre 8 y 30 caracteres.'
            )

        elif codigo_transaccion_en_uso(codigo):
            errores.append(
                'Ese número de operación ya fue cargado en otro pago. '
                'Si creés que es un error, escribile a la Cooperadora.'
            )

    if comprobante_ya_usado(data.get('hash_comprobante')):
        errores.append(
            'Ese comprobante ya fue cargado en el sistema. Cada '
            'transferencia se carga una sola vez.'
        )

    return errores

def buscar_o_crear_aportante(data):
    """Busca la persona por DNI y, si no está, la crea.

    Cuando ya existe completamos sólo lo que falta: no pisamos lo que ya está
    cargado, porque la Cooperadora puede haberlo corregido a mano.
    """
    dni = validaciones.limpiar_dni(data.get('dni'))
    aportante = Aportante.get_by_dni(dni)

    if not aportante:
        aportante = Aportante(
            nombre=(data.get('nombre') or '').strip(),
            apellido=(data.get('apellido') or '').strip(),
            dni=dni,
            anio=data.get('anio') or None,
            carrera_id=data.get('carrera_id') or None
        )
        db.session.add(aportante)
        # flush() manda el INSERT a la base y le asigna el id a la fila, pero
        # todavía no confirma nada: eso lo hace el commit del final.
        db.session.flush()
        return aportante

    if data.get('anio') and not aportante.anio:
        aportante.anio = data['anio']
    if data.get('carrera_id') and not aportante.carrera_id:
        aportante.carrera_id = data['carrera_id']
    db.session.add(aportante)

    return aportante


# ============================================
# ALTA DE PAGOS
# ============================================

def crear_pago_de_cuota(data, request=None):
    """Registra un pago de la cuota de socio (RF-01, RF-02).

    Devuelve (pago, saldo). El saldo se devuelve para poder mostrarle al
    aportante cómo viene, pero este pago NO se le suma todavía: figura como
    "en revisión" hasta que la Cooperadora lo verifique.
    """
    errores = validar_datos(data)
    errores = errores + validar_operacion_y_comprobante(data)
    if errores:
        raise ErrorDeCarga(errores)

    ejercicio = Ejercicio.get_ejercicio_vigente()
    if not ejercicio:
        raise ErrorDeCarga('No hay un ejercicio abierto. Avisale a la Cooperadora.')

    fondo, error_fondo = fondos.buscar_fondo(data.get('destino'),
                                             data.get('carrera_destino_id'))
    if error_fondo:
        raise ErrorDeCarga(error_fondo)

    aportante = buscar_o_crear_aportante(data)

    pago = Pago(
        codigo_seguimiento=generar_codigo('SC'),
        aportante_id=aportante.id,
        tipo='cuota',
        importe=data['importe'],
        fecha=validaciones.texto_a_fecha(data.get('fecha')),
        medio_pago='transferencia',
        codigo_transaccion=data['codigo_transaccion'],
        hash_comprobante=data.get('hash_comprobante'),
        comprobante_nombre=data.get('comprobante_nombre'),
        fondo_id=fondo.id,
        ejercicio_id=ejercicio.id,
        estado='pendiente',
        observaciones=(data.get('observaciones') or '').strip() or None,
        cuit=(data.get('cuit') or '').strip() or None,
        solicita_libreta=bool(data.get('solicita_libreta'))
    )
    db.session.add(pago)
    # flush() manda el INSERT a la base y le asigna el id a la fila, pero
    # todavía no confirma nada: eso lo hace el commit del final.
    db.session.flush()

    # Creamos el saldo si todavía no existía, pero no le sumamos nada
    saldo = saldos.buscar_o_crear_saldo(aportante.id, ejercicio.id, ejercicio.cuota)

    auditoria.registrar(
        usuario='portal-publico',
        accion='cargar_pago_cuota',
        tabla='pagos',
        registro_id=pago.id,
        detalle={
            'codigo_seguimiento': pago.codigo_seguimiento,
            'importe': str(pago.importe),
            'solicita_libreta': pago.solicita_libreta,
        },
        request=request
    )

    db.session.commit()
    return pago, saldo


def crear_pago_publico(data, request=None):
    """Registra un aporte que no es cuota de socio (RF-09, RF-11).

    Sirve para donaciones, sponsors, aportes al fondo de una carrera y el
    duplicado de libreta. Como no es cuota, va sin ejercicio: entra plata,
    pero no le baja la cuota a nadie.
    """
    tipo = data.get('tipo', 'adicional')

    # En un aporte adicional el apellido es opcional: puede firmarlo una
    # empresa o alguien que no quiere dar más datos que el DNI.
    errores = validar_datos(data, pide_apellido=(tipo != 'adicional'))
    errores = errores + validar_operacion_y_comprobante(data)
    if errores:
        raise ErrorDeCarga(errores)

    fondo, error_fondo = fondos.buscar_fondo(data.get('destino'),
                                             data.get('carrera_destino_id'))
    if error_fondo:
        raise ErrorDeCarga(error_fondo)

    aportante = buscar_o_crear_aportante(data)

    pago = Pago(
        codigo_seguimiento=generar_codigo('SC'),
        aportante_id=aportante.id,
        tipo=tipo,
        importe=data['importe'],
        fecha=validaciones.texto_a_fecha(data.get('fecha')),
        medio_pago='transferencia',
        codigo_transaccion=data['codigo_transaccion'],
        hash_comprobante=data.get('hash_comprobante'),
        comprobante_nombre=data.get('comprobante_nombre'),
        fondo_id=fondo.id,
        ejercicio_id=None,
        estado='pendiente',
        observaciones=(data.get('observaciones') or '').strip() or None,
        cuit=(data.get('cuit') or '').strip() or None,
        solicita_libreta=bool(data.get('solicita_libreta'))
    )
    db.session.add(pago)
    # flush() manda el INSERT a la base y le asigna el id a la fila, pero
    # todavía no confirma nada: eso lo hace el commit del final.
    db.session.flush()

    auditoria.registrar(
        usuario='portal-publico',
        accion='cargar_aporte',
        tabla='pagos',
        registro_id=pago.id,
        detalle={
            'codigo_seguimiento': pago.codigo_seguimiento,
            'tipo': pago.tipo,
            'importe': str(pago.importe),
            'fondo': fondo.nombre,
        },
        request=request
    )

    db.session.commit()
    return pago


# ============================================
# VERIFICACIÓN Y RECHAZO (panel de la Cooperadora)
# ============================================

def verificar_pago(pago_id, usuario_id, numero_recibo=None, serie_recibo=None,
                   request=None):
    """La Cooperadora confirma que el dinero entró (RF-03).

    Este es el ÚNICO momento en que un pago suma. Pasan tres cosas, en este
    orden: cambia el estado, entra al fondo y se recalcula el saldo.
    """
    pago = Pago.query.get(pago_id)
    if not pago:
        raise ErrorDeCarga('El pago no existe.')
    if pago.estado == 'verificado':
        raise ErrorDeCarga('El pago ya está verificado.')
    if pago.estado == 'anulado':
        raise ErrorDeCarga('No se puede verificar un pago anulado.')

    # 1. El pago pasa a verificado
    pago.estado = 'verificado'
    pago.fecha_verificacion = datetime.utcnow()
    pago.verificado_por_id = usuario_id
    pago.motivo_rechazo = None
    if numero_recibo:
        pago.numero_recibo = numero_recibo
    if serie_recibo:
        pago.serie_recibo = serie_recibo
    db.session.add(pago)

    # 2. La plata entra al fondo
    fondos.registrar_movimiento(
        pago.fondo,
        monto=pago.importe,
        motivo='Verificación del pago ' + pago.codigo_seguimiento
    )

    # 3. Se recalcula el saldo de cuota del aportante
    saldos.recalcular_saldo_de_pago(pago)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='verificar_pago',
        tabla='pagos',
        registro_id=pago.id,
        detalle={
            'codigo_seguimiento': pago.codigo_seguimiento,
            'importe': str(pago.importe),
            'numero_recibo': numero_recibo,
        },
        request=request
    )

    db.session.commit()
    return pago


def rechazar_pago(pago_id, usuario_id, motivo, request=None):
    """El pago no coincide con el extracto del banco.

    Si ya estaba verificado hay que dar marcha atrás con el movimiento del
    fondo, si no el saldo del fondo queda inflado para siempre.
    """
    pago = Pago.query.get(pago_id)
    if not pago:
        raise ErrorDeCarga('El pago no existe.')

    motivo = (motivo or '').strip()
    if not motivo:
        raise ErrorDeCarga('Hay que indicar el motivo del rechazo.')

    estaba_verificado = (pago.estado == 'verificado')

    pago.estado = 'rechazado'
    pago.fecha_verificacion = datetime.utcnow()
    pago.verificado_por_id = usuario_id
    pago.motivo_rechazo = motivo
    db.session.add(pago)

    if estaba_verificado:
        fondos.registrar_movimiento(
            pago.fondo,
            monto=-float(pago.importe),
            motivo='Reversión por rechazo del pago ' + pago.codigo_seguimiento
        )

    saldos.recalcular_saldo_de_pago(pago)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='rechazar_pago',
        tabla='pagos',
        registro_id=pago.id,
        detalle={'codigo_seguimiento': pago.codigo_seguimiento, 'motivo': motivo},
        request=request
    )

    db.session.commit()
    return pago


# ============================================
# CONSULTA DE ESTADO
# ============================================

def estado_de_cuota(dni):
    """Cómo viene la cuota de un DNI en el ejercicio vigente.

    Es lo que alimenta el cuadro que el aportante ve mientras completa el
    formulario. Devuelve sólo importes, nunca datos personales.
    """
    ejercicio = Ejercicio.get_ejercicio_vigente()
    if not ejercicio:
        return None

    cuota = float(ejercicio.cuota)

    # Respuesta para quien todavía no cargó nada: le mostramos la cuota entera
    estado = {
        'registrado': False,
        'cuota_total': cuota,
        'pagado': 0.0,
        'en_revision': 0.0,
        'saldo_pendiente': cuota,
        'al_dia': False,
    }

    aportante = Aportante.get_by_dni(dni)
    if not aportante:
        return estado

    estado['registrado'] = True

    saldo = SaldoAportante.get_por_aportante(aportante.id, ejercicio.id)
    if not saldo:
        return estado

    estado['cuota_total'] = float(saldo.cuota_total)
    estado['pagado'] = float(saldo.pagado)
    estado['en_revision'] = saldo.en_revision
    estado['saldo_pendiente'] = float(saldo.saldo_pendiente)
    estado['al_dia'] = (saldo.estado == 'al_dia')
    return estado
