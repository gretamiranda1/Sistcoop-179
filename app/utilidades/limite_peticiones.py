"""Límite de solicitudes por IP, para pantallas públicas sensibles (RNF-02, RNF-03).

El contador vive en la base de datos, no en memoria del proceso: así
funciona igual sin importar cuántos workers de Gunicorn estén corriendo.
"""

from datetime import datetime, timedelta

from flask import request

from app.extensions import db
from app.modelos.limitador import ConsultaLimitada


def excede_limite(pantalla, limite=10, ventana=60):
    """Devuelve True si esta IP ya hizo demasiadas consultas seguidas.

    Lo usamos en las pantallas públicas de consulta. Sin esto, alguien podría
    ir probando DNI uno por uno para averiguar quién está registrado y cuánto
    pagó, que es justamente lo que pide evitar RNF-02.
    """
    ip = request.remote_addr or 'desconocida'
    clave = pantalla + ':' + ip
    ahora = datetime.utcnow()
    desde = ahora - timedelta(seconds=ventana)

    # Los renglones fuera de la ventana ya no sirven para nada: se borran acá
    ConsultaLimitada.query.filter(
        ConsultaLimitada.clave == clave,
        ConsultaLimitada.momento <= desde
    ).delete()

    cantidad = ConsultaLimitada.query.filter(
        ConsultaLimitada.clave == clave,
        ConsultaLimitada.momento > desde
    ).count()

    if cantidad >= limite:
        db.session.commit()
        return True

    db.session.add(ConsultaLimitada(clave=clave, momento=ahora))
    db.session.commit()
    return False


def limpiar_limites():
    """Vacía el contador. Sólo lo usamos en las pruebas."""
    ConsultaLimitada.query.delete()
    db.session.commit()