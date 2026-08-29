"""Escritura del registro de auditoría (RNF-04).

Una sola función: la llaman todos los servicios y todos los controladores
que hacen algo que después hay que poder explicar.
"""

from app.extensions import db
from app.modelos.auditoria import Auditoria


def registrar(usuario, accion, tabla=None, registro_id=None, detalle=None, request=None):
    """Deja anotado quién hizo qué.

    `usuario` es el id del usuario logueado, o el texto 'portal-publico'
    cuando la acción viene del portal, que no pide inicio de sesión.

    Esta función NO hace commit: el commit lo hace la operación que la llamó,
    así el renglón de auditoría y el cambio real se guardan juntos.
    """
    renglon = Auditoria(
        usuario=usuario,
        accion=accion,
        tabla=tabla,
        registro_id=registro_id,
        detalle=detalle
    )

    if request:
        renglon.ip = request.remote_addr
        renglon.user_agent = request.headers.get('User-Agent', '')

    db.session.add(renglon)
    return renglon
