"""Tabla de saldos por aportante y ejercicio.

Igual que en los demás modelos, acá no se modifica nada: el saldo se
recalcula en servicios/saldos.py.
"""

from datetime import datetime

from app.extensions import db
from app.modelos.pagos import Pago

from decimal import Decimal

class SaldoAportante(db.Model):
    """Cómo viene la cuota de una persona en un ejercicio.

    Esta tabla no es la fuente de la verdad: se puede reconstruir entera
    sumando los pagos verificados. La tenemos para no recorrer todos los
    pagos cada vez que hay que mostrar el estado en una pantalla.
    """

    __tablename__ = 'saldos_aportantes'

    id = db.Column(db.Integer, primary_key=True)
    aportante_id = db.Column(db.Integer, db.ForeignKey('aportantes.id'), nullable=False)
    ejercicio_id = db.Column(db.Integer, db.ForeignKey('ejercicios.id'), nullable=False)

    # Ojo: acá van SÓLO los pagos verificados. Lo que se cargó y todavía no
    # se verificó se consulta aparte, con la propiedad en_revision.
    pagado = db.Column(db.Numeric(10, 2), default=0)
    saldo_pendiente = db.Column(db.Numeric(10, 2))
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, al_dia

    libreta_entregada = db.Column(db.Boolean, default=False)
    fecha_libreta = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Una persona no puede tener dos saldos del mismo año
    __table_args__ = (
        db.UniqueConstraint('aportante_id', 'ejercicio_id',
                            name='uq_saldo_aportante_ejercicio'),
    )

    aportante = db.relationship('Aportante', backref='saldos')
    ejercicio = db.relationship('Ejercicio', backref='saldos')

    # ============================================
    # CONSULTAS
    # ============================================

    @classmethod
    def get_por_aportante(cls, aportante_id, ejercicio_id):
        """El saldo de una persona en un ejercicio, o None si todavía no tiene."""
        return cls.query.filter_by(
            aportante_id=aportante_id,
            ejercicio_id=ejercicio_id
        ).first()

    @property
    def en_revision(self):
        """Lo que cargó el aportante y la Cooperadora todavía no verificó.

        Va separado de `pagado` para que nadie confunda "subí el comprobante"
        con "la Cooperadora confirmó que el dinero entró".
        """
        total = Decimal('0')
        for pago in Pago.get_de_cuota(self.aportante_id, self.ejercicio_id, 'pendiente'):
            total = total + pago.importe
        return total

    @property
    def falta_pagar(self):
        """Cuánto le falta para completar la cuota, contando lo que está en revisión.

        Lo usa el reparto del pago grupal, para no pedirle dos veces lo mismo
        a alguien que ya cargó un comprobante y espera la verificación.
        """
        falta = self.ejercicio.cuota - self.pagado - self.en_revision
        if falta < 0:
            return Decimal('0.00')
        return falta

    # ============================================
    # PARA LA BARRA DE AVANCE
    # ============================================

    @property
    def porcentaje_pagado(self):
        cuota_total = float(self.ejercicio.cuota)
        if not cuota_total:
            return 0
        porcentaje = float(self.pagado) / cuota_total * 100
        return min(round(porcentaje), 100)

    @property
    def porcentaje_en_revision(self):
        cuota_total = float(self.ejercicio.cuota)
        if not cuota_total:
            return 0
        porcentaje = self.en_revision / cuota_total * 100
        # Entre lo verificado y lo que está en revisión no se puede pasar del 100%
        disponible = 100 - self.porcentaje_pagado
        return min(round(porcentaje), disponible)

    def __repr__(self):
        return '<Saldo {}: {}/{}>'.format(self.aportante_id, self.pagado, self.ejercicio.cuota)
