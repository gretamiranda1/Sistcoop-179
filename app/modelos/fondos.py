"""Tablas de fondos y de movimientos de fondo.

El saldo de un fondo se cambia únicamente desde servicios/fondos.py, con la
función registrar_movimiento. Acá sólo están las tablas y las consultas.
"""

from datetime import datetime

from app.extensions import db


class Fondo(db.Model):
    """Cada "bolsillo" de la Cooperadora.

    Hay uno general (tipo capital) y uno por cada carrera, para que la plata
    de una carrera no se mezcle con la general (RF-09).
    """

    __tablename__ = 'fondos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # capital, carrera, evento
    saldo = db.Column(db.Numeric(12, 2), default=0)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    carrera_id = db.Column(db.Integer, db.ForeignKey('carreras.id'), nullable=True)

    pagos = db.relationship('Pago', backref='fondo', lazy='dynamic')
    movimientos = db.relationship('MovimientoFondo', backref='fondo', lazy='dynamic')

    @classmethod
    def get_capital(cls):
        """El fondo general de la Cooperadora."""
        return cls.query.filter_by(tipo='capital', activo=True).first()

    @classmethod
    def get_de_carrera(cls, carrera_id):
        """El fondo propio de una carrera (RF-09)."""
        if not carrera_id:
            return None
        return cls.query.filter_by(carrera_id=carrera_id, tipo='carrera',
                                   activo=True).first()

    @classmethod
    def get_activos(cls):
        """Todos los fondos activos, con el general primero."""
        capital = cls.query.filter_by(tipo='capital', activo=True).all()
        resto = cls.query.filter(
            cls.activo == True,
            cls.tipo != 'capital'
        ).order_by(cls.nombre).all()
        return capital + resto

    def __repr__(self):
        return '<Fondo {}>'.format(self.nombre)


class MovimientoFondo(db.Model):
    """Cada vez que el saldo de un fondo cambia queda un renglón acá.

    No se edita ni se borra nunca. Si hay que corregir algo, se agrega un
    movimiento al revés. Es lo que permite explicar el saldo de un fondo
    sumando los movimientos, que es lo que se audita (RNF-04).
    """

    __tablename__ = 'movimientos_fondo'

    id = db.Column(db.Integer, primary_key=True)
    fondo_id = db.Column(db.Integer, db.ForeignKey('fondos.id'), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)   # negativo si el saldo baja
    saldo_anterior = db.Column(db.Numeric(12, 2))
    saldo_resultante = db.Column(db.Numeric(12, 2), nullable=False)
    motivo = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<MovimientoFondo fondo={} monto={}>'.format(self.fondo_id, self.monto)
