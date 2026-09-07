"""Datos de la petición HTTP en curso que hace falta guardar en auditoría."""

from flask import request


def ip_y_user_agent():
    """IP y User-Agent del pedido actual, listos para pasarle a un servicio.

    Los servicios de app/servicios/ no dependen de Flask: por eso esta
    extracción vive acá y no en ellos, y quien llama a un servicio le pasa
    ip y user_agent ya resueltos.
    """
    return request.remote_addr, request.headers.get('User-Agent', '')
