"""Contador de solicitudes por IP y pantalla, para el limitador de tasa.

Reemplaza el diccionario en memoria de utilidades/limite_peticiones.py:
ese vivía en el proceso de Python, así que con más de un worker de
Gunicorn cada uno llevaba su propia cuenta por separado.
"""

from datetime import datetime

from app.extensions import db


class ConsultaLimitada(db.Model):
    """Un renglón por cada consulta hecha a una pantalla con límite de tasa.

    `clave` es "pantalla:ip" (por ejemplo "login:190.191.0.1"). Los renglones
    vencidos se van borrando solos cada vez que se consulta la misma clave;
    esta tabla no acumula historial para siempre.
    """

    __tablename__ = 'consultas_limitadas'

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(150), nullable=False, index=True)
    momento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return '<ConsultaLimitada {}>'.format(self.clave)