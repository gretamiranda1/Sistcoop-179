"""Tablas del pago grupal.

Una transferencia grupal se guarda en tres lugares:

  PagoGrupal          la transferencia que llegó al banco (una sola)
  PagoGrupalDetalle   cuánto le tocó a cada persona (para poder mostrarlo)
  Pago                el asiento contable de cada persona (uno por persona)

Se procesa en servicios/pagos_grupales.py.
"""

from datetime import datetime

from app.extensions import db


class PagoGrupal(db.Model):
    """Una sola transferencia que cubre a varias personas.

    Caso que salió del relevamiento: una familia o un grupo de compañeros
    manda un único importe.
    """

    __tablename__ = 'pagos_grupales'

    id = db.Column(db.Integer, primary_key=True)
    codigo_seguimiento = db.Column(db.String(20), unique=True, index=True)
    codigo_transaccion = db.Column(db.String(100), unique=True, nullable=False)
    importe_total = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    comprobante_nombre = db.Column(db.String(255))
    hash_comprobante = db.Column(db.String(64), index=True)
    estado = db.Column(db.String(20), default='pendiente')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    detalles = db.relationship('PagoGrupalDetalle', backref='pago_grupal', lazy='dynamic')
    pagos = db.relationship('Pago', backref='pago_grupal', lazy='dynamic')

    @classmethod
    def get_by_transaccion(cls, codigo):
        if not codigo:
            return None
        return cls.query.filter_by(codigo_transaccion=codigo).first()

    @classmethod
    def get_by_codigo_seguimiento(cls, codigo):
        if not codigo:
            return None
        return cls.query.filter_by(codigo_seguimiento=codigo.strip().upper()).first()

    @classmethod
    def get_by_hash_comprobante(cls, huella):
        if not huella:
            return None
        return cls.query.filter_by(hash_comprobante=huella).first()

    @classmethod
    def get_pendientes(cls, pagina=1, por_pagina=20):
        return cls.query.filter_by(estado='pendiente').order_by(cls.created_at.asc()).paginate(
            page=pagina, per_page=por_pagina, error_out=False)

    def __repr__(self):
        return '<PagoGrupal {}: ${}>'.format(self.codigo_seguimiento, self.importe_total)


class PagoGrupalDetalle(db.Model):
    """Cuánto de la transferencia grupal le corresponde a cada persona."""

    __tablename__ = 'pagos_grupales_detalle'

    id = db.Column(db.Integer, primary_key=True)
    pago_grupal_id = db.Column(db.Integer, db.ForeignKey('pagos_grupales.id'), nullable=False)
    aportante_id = db.Column(db.Integer, db.ForeignKey('aportantes.id'), nullable=False)
    monto_asignado = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')
    solicita_libreta = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    aportante = db.relationship('Aportante', backref='pagos_grupales_detalle')

    def __repr__(self):
        return '<PagoGrupalDetalle {}: ${}>'.format(self.id, self.monto_asignado)
