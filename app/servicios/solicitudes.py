"""Reglas de negocio de las solicitudes de fondos, evento o viaje."""

from app.extensions import db
from app.modelos.pagos import generar_codigo
from app.modelos.solicitudes import SolicitudFondo
from app.servicios import auditoria
from app.servicios.pagos import ErrorDeCarga


def crear_solicitud_fondos(data, ip=None, user_agent=None):
    """Registra un pedido de fondos, evento o viaje.

    Sin carrera_id la solicitud queda huérfana: nadie puede saber después
    a qué carrera corresponde el pedido, ni a qué fondo debería imputarse
    si se aprueba.
    """
    if not data.get('carrera_id'):
        raise ErrorDeCarga('Debe seleccionar una carrera.')

    pedido = SolicitudFondo(
        codigo_seguimiento=generar_codigo('SF'),
        responsable=data.get('responsable'),
        contacto=data.get('contacto'),
        carrera_id=data.get('carrera_id'),
        curso=data.get('curso'),
        tipo=data.get('tipo'),
        concepto=data.get('concepto'),
        importe_estimado=data.get('importe_estimado'),
        fecha_estimada=data.get('fecha_estimada'),
        justificacion=data.get('justificacion'),
    )
    db.session.add(pedido)
    # flush() manda el INSERT y asigna el id, pero todavía no confirma nada:
    # necesitamos el id para la auditoría, antes del commit final.
    db.session.flush()

    auditoria.registrar(
        usuario='portal-publico',
        accion='cargar_solicitud_fondos',
        tabla='solicitudes_fondo',
        registro_id=pedido.id,
        detalle={'codigo_seguimiento': pedido.codigo_seguimiento, 'tipo': pedido.tipo},
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()
    return pedido