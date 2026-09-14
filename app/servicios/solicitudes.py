from datetime import datetime

from app.extensions import db
from app.modelos.solicitudes import SolicitudFondo
from app.servicios import auditoria
from app.modelos.pagos import generar_codigo


class ErrorDeResolucion(Exception):
    """Una solicitud no se pudo aprobar o rechazar."""


def aprobar_solicitud(solicitud_id, usuario_id, comentario=None, ip=None, user_agent=None):
    solicitud = SolicitudFondo.query.get(solicitud_id)
    if not solicitud:
        raise ErrorDeResolucion('La solicitud no existe.')
    if solicitud.estado != 'pendiente':
        raise ErrorDeResolucion('Esta solicitud ya fue resuelta.')

    solicitud.estado = 'aprobada'
    solicitud.resolucion = (comentario or '').strip() or None
    solicitud.resuelta_por_id = usuario_id
    solicitud.fecha_resolucion = datetime.utcnow()
    db.session.add(solicitud)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='aprobar_solicitud',
        tabla='solicitudes_fondo',
        registro_id=solicitud.id,
        detalle={'codigo_seguimiento': solicitud.codigo_seguimiento,
                 'comentario': solicitud.resolucion},
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return solicitud


def rechazar_solicitud(solicitud_id, usuario_id, motivo, ip=None, user_agent=None):
    solicitud = SolicitudFondo.query.get(solicitud_id)
    if not solicitud:
        raise ErrorDeResolucion('La solicitud no existe.')
    if solicitud.estado != 'pendiente':
        raise ErrorDeResolucion('Esta solicitud ya fue resuelta.')

    motivo = (motivo or '').strip()
    if not motivo:
        raise ErrorDeResolucion('Hay que indicar el motivo del rechazo.')

    solicitud.estado = 'rechazada'
    solicitud.resolucion = motivo
    solicitud.resuelta_por_id = usuario_id
    solicitud.fecha_resolucion = datetime.utcnow()
    db.session.add(solicitud)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='rechazar_solicitud',
        tabla='solicitudes_fondo',
        registro_id=solicitud.id,
        detalle={'codigo_seguimiento': solicitud.codigo_seguimiento, 'motivo': motivo},
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return solicitud


def crear_solicitud_fondos(data, ip=None, user_agent=None):
    """Registra un pedido de fondos, evento o viaje (RF-10).

    A diferencia de un Pago, acá no entra ni sale plata: sólo queda un
    pedido pendiente de que la Cooperadora lo revise (ver
    aprobar_solicitud/rechazar_solicitud).
    """
    solicitud = SolicitudFondo(
        codigo_seguimiento=generar_codigo('SF'),
        responsable=data['responsable'],
        contacto=data['contacto'],
        carrera_id=data.get('carrera_id'),
        curso=data.get('curso'),
        tipo=data['tipo'],
        concepto=data['concepto'],
        importe_estimado=data.get('importe_estimado'),
        fecha_estimada=data.get('fecha_estimada'),
        justificacion=data['justificacion'],
    )
    db.session.add(solicitud)
    db.session.flush()

    auditoria.registrar(
        usuario='portal-publico',
        accion='crear_solicitud_fondos',
        tabla='solicitudes_fondo',
        registro_id=solicitud.id,
        detalle={
            'codigo_seguimiento': solicitud.codigo_seguimiento,
            'tipo': solicitud.tipo,
            'concepto': solicitud.concepto,
        },
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return solicitud