from datetime import datetime

from app.extensions import db
from app.modelos.solicitudes import SolicitudFondo
from app.servicios import auditoria


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