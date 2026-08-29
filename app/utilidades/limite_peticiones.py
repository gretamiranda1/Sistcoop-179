import time
from flask import request

# Guardamos, por cada IP y cada pantalla, la hora de las últimas consultas.
# La clave es "nombre_de_la_pantalla:ip" y el valor una lista de horarios.
#
# Esto vive en la memoria del proceso. Alcanza para desarrollo y para un
# servidor con un solo proceso. Si en producción se levantan varios, cada
# uno va a llevar su propia cuenta y habría que pasarlo a Redis.
_consultas = {}


def excede_limite(pantalla, limite=10, ventana=60):
    """Devuelve True si esta IP ya hizo demasiadas consultas seguidas.

    Lo usamos en las pantallas públicas de consulta. Sin esto, alguien podría
    ir probando DNI uno por uno para averiguar quién está registrado y cuánto
    pagó, que es justamente lo que pide evitar RNF-02.
    """
    ip = request.remote_addr or 'desconocida'
    clave = pantalla + ':' + ip
    ahora = time.time()

    # Nos quedamos sólo con las consultas que entran en la ventana de tiempo
    anteriores = _consultas.get(clave, [])
    anteriores = [momento for momento in anteriores if momento > ahora - ventana]

    if len(anteriores) >= limite:
        _consultas[clave] = anteriores
        return True

    anteriores.append(ahora)
    _consultas[clave] = anteriores
    return False


def limpiar_limites():
    """Vacía el contador. Sólo lo usamos en las pruebas."""
    _consultas.clear()
