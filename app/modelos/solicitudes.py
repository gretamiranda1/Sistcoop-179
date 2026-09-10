from app.extensions import db
from datetime import datetime

TIPOS_LEGIBLES = {
    'fondos': 'Fondos de la carrera',
    'evento': 'Autorización de evento',
    'viaje': 'Viaje o proyecto',
}

ESTADOS_LEGIBLES = {
    'pendiente': 'Pendiente de resolución',
    'aprobada': 'Aprobada',
    'rechazada': 'Rechazada',
}


class SolicitudFondo(db.Model):
    """Pedido de fondos, evento o viaje que presenta un curso o un docente.

    Hasta el Incremento 2 este formulario no guardaba nada: contestaba
    "solicitud enviada" y el pedido se perdía. Ahora queda registrado con su
    código de seguimiento.

    TODO (Incremento 3): la Cooperadora todavía no puede aprobar ni rechazar
    desde el panel. Los campos de resolución ya están.
    """

    __tablename__ = 'solicitudes_fondo'

    id = db.Column(db.Integer, primary_key=True)
    codigo_seguimiento = db.Column(db.String(20), unique=True, index=True)

    responsable = db.Column(db.String(120), nullable=False)
    contacto = db.Column(db.String(120), nullable=False)
    carrera_id = db.Column(db.Integer, db.ForeignKey('carreras.id'), nullable=False)
    curso = db.Column(db.String(50))

    tipo = db.Column(db.String(20), nullable=False)  # fondos, evento, viaje
    concepto = db.Column(db.String(200), nullable=False)
    importe_estimado = db.Column(db.Numeric(12, 2))
    fecha_estimada = db.Column(db.Date)
    justificacion = db.Column(db.Text, nullable=False)

    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    resolucion = db.Column(db.Text)
    resuelta_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_resolucion = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Los valores admitidos salen de TIPOS_LEGIBLES y ESTADOS_LEGIBLES: no hay
    # una segunda lista escrita a mano acá, sólo el SQL armado a partir de esas.
    __table_args__ = (
        db.CheckConstraint(
            'tipo IN ({})'.format(', '.join(repr(v) for v in TIPOS_LEGIBLES)),
            name='ck_solicitudes_fondo_tipo'
        ),
        db.CheckConstraint(
            'estado IN ({})'.format(', '.join(repr(v) for v in ESTADOS_LEGIBLES)),
            name='ck_solicitudes_fondo_estado'
        ),
    )

    carrera = db.relationship('Carrera', backref='solicitudes')

    @classmethod
    def get_by_codigo_seguimiento(cls, codigo):
        if not codigo:
            return None
        return cls.query.filter_by(codigo_seguimiento=codigo.strip().upper()).first()

    @property
    def tipo_legible(self):
        return TIPOS_LEGIBLES.get(self.tipo, self.tipo)

    @property
    def estado_legible(self):
        return ESTADOS_LEGIBLES.get(self.estado, self.estado)

    def __repr__(self):
        return '<SolicitudFondo {} - {}>'.format(self.codigo_seguimiento, self.tipo)
