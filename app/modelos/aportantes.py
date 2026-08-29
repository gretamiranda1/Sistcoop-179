"""Tabla de aportantes."""

from datetime import datetime

from app.extensions import db
from app.utilidades import validaciones


class Aportante(db.Model):
    """Persona o empresa que le transfiere plata a la Cooperadora.

    Se identifica por DNI. El registro se crea solo la primera vez que
    alguien carga un pago: no hay un padrón cargado de antemano, porque la
    propuesta pide que el sistema conviva con el papel durante la transición
    (RNF-10).
    """

    __tablename__ = 'aportantes'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    dni = db.Column(db.String(15), nullable=False, unique=True, index=True)
    anio = db.Column(db.String(5))
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    carrera_id = db.Column(db.Integer, db.ForeignKey('carreras.id'))
    pagos = db.relationship('Pago', backref='aportante', lazy='dynamic')

    def nombre_completo(self):
        return self.apellido + ', ' + self.nombre

    @classmethod
    def get_by_dni(cls, dni):
        """Busca por DNI, limpiando antes puntos y espacios.

        Si no lo limpiáramos, "33.123.456" y "33123456" terminarían siendo dos
        personas distintas, cada una con su saldo.
        """
        limpio = validaciones.limpiar_dni(dni)
        if not limpio:
            return None
        return cls.query.filter_by(dni=limpio).first()

    def __repr__(self):
        return '<Aportante {}>'.format(self.dni)
