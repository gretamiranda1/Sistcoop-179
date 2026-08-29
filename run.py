"""Punto de entrada del servidor de desarrollo.

En producción la aplicación se sirve con Gunicorn detrás de Nginx, no con
este archivo: el servidor de desarrollo de Flask no está pensado para
atender tráfico real.
"""

import os

from app import create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # host 127.0.0.1: el servidor de desarrollo sólo escucha en esta
    # máquina. Exponerlo en 0.0.0.0 lo deja accesible desde toda la red.
    app.run(debug=True, host='127.0.0.1', port=5000)
