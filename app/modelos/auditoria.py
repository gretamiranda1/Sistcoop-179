"""Tabla de auditoría: qué hizo cada usuario y cuándo.

Los renglones se escriben desde servicios/auditoria.py.
"""

from datetime import datetime

from app.extensions import db


class Auditoria(db.Model):
    """Un renglón por cada operación importante del sistema (RNF-04).

    No se edita ni se borra. Es lo que permite reconstruir qué pasó cuando
    hay una diferencia entre lo que dice el sistema y lo que dice el banco.
    """

    __tablename__ = 'auditoria'

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    tabla = db.Column(db.String(50))
    registro_id = db.Column(db.Integer)
    detalle = db.Column(db.JSON)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_ultimas(cls, pagina=1, por_pagina=50):
        """Las operaciones más nuevas primero, paginadas."""
        return cls.query.order_by(cls.created_at.desc()).paginate(
            page=pagina, per_page=por_pagina, error_out=False)

    def __repr__(self):
        return '<Auditoria {} - {}>'.format(self.id, self.accion)
