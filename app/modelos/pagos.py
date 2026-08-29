"""Tabla de pagos.

Un modelo en este proyecto describe una tabla y sabe responder preguntas
sobre ella (los métodos que empiezan con `get_`). Todo lo que MODIFICA datos
está en app/servicios/. Así, para saber qué le pasa a un pago cuando se
verifica, se lee una sola función: servicios/pagos.py -> verificar_pago.
"""

import secrets
from datetime import datetime

from app.extensions import db

# Alfabeto sin los caracteres que se confunden entre sí (0 y O, 1 e I y L),
# porque el código se dicta por teléfono y se copia de un papel.
LETRAS_CODIGO = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'

# Tipos de pago que cuentan para la cuota del año. Un aporte adicional entra
# plata igual, pero no le baja la cuota a nadie.
TIPOS_DE_CUOTA = ['cuota', 'cuota_grupal']

ESTADOS_LEGIBLES = {
    'pendiente': 'Pendiente de verificación',
    'verificado': 'Verificado',
    'rechazado': 'Rechazado',
    'anulado': 'Anulado',
}

TIPOS_LEGIBLES = {
    'cuota': 'Cuota de socio',
    'cuota_grupal': 'Cuota de socio (pago grupal)',
    'adicional': 'Aporte adicional',
    'aporte_carrera': 'Aporte a fondo de carrera',
    'libreta_duplicado': 'Duplicado de libreta',
}


def generar_codigo(prefijo='SC'):
    """Arma un código de seguimiento, tipo SC-A3F9K2XY.

    Lo usamos como identificador público del pago en lugar del id, que es
    correlativo: con el id, alguien podría entrar a /comprobante/1, después
    al 2, al 3, y ver los pagos de otras personas.
    """
    cuerpo = ''
    for i in range(8):
        cuerpo = cuerpo + secrets.choice(LETRAS_CODIGO)
    return prefijo + '-' + cuerpo


class Pago(db.Model):
    """Un ingreso de dinero a la Cooperadora.

    IMPORTANTE: un pago nace en estado 'pendiente' y NO mueve ningún saldo.
    Recién impacta cuando la Cooperadora lo verifica contra el movimiento
    real del banco (RF-03). Si algún día alguien acredita antes de eso, se
    rompe la regla central del sistema.
    """

    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)

    # Identificador público (ver generar_codigo)
    codigo_seguimiento = db.Column(db.String(20), unique=True, index=True)

    # cuota, cuota_grupal, adicional, aporte_carrera, libreta_duplicado
    tipo = db.Column(db.String(30), nullable=False)
    importe = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    medio_pago = db.Column(db.String(50))

    # Número de operación del banco. Es único en toda la tabla, para que el
    # mismo comprobante no se pueda cargar dos veces (RF-04).
    codigo_transaccion = db.Column(db.String(100), unique=True)

    # Huella SHA-256 del archivo, para detectar el mismo comprobante aunque
    # le hayan cambiado el nombre
    hash_comprobante = db.Column(db.String(64), index=True)

    # pendiente, verificado, rechazado, anulado
    estado = db.Column(db.String(20), default='pendiente')

    # Nombre del archivo guardado. No es una URL: los comprobantes se sirven
    # por una ruta que pide sesión iniciada.
    comprobante_nombre = db.Column(db.String(255))

    observaciones = db.Column(db.Text)
    motivo_rechazo = db.Column(db.Text)

    numero_recibo = db.Column(db.String(20))
    serie_recibo = db.Column(db.String(5))

    fecha_verificacion = db.Column(db.DateTime)
    verificado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    cuit = db.Column(db.String(13))
    solicita_libreta = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Claves foráneas
    aportante_id = db.Column(db.Integer, db.ForeignKey('aportantes.id'), nullable=False)
    fondo_id = db.Column(db.Integer, db.ForeignKey('fondos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    ejercicio_id = db.Column(db.Integer, db.ForeignKey('ejercicios.id'))
    pago_grupal_id = db.Column(db.Integer, db.ForeignKey('pagos_grupales.id'))

    # ============================================
    # CONSULTAS
    # ============================================

    @classmethod
    def get_by_transaccion(cls, codigo):
        """Busca un pago por el número de operación del banco."""
        if not codigo:
            return None
        return cls.query.filter_by(codigo_transaccion=codigo).first()

    @classmethod
    def get_by_codigo_seguimiento(cls, codigo):
        """Busca un pago por su código público (SC-XXXXXXXX)."""
        if not codigo:
            return None
        return cls.query.filter_by(codigo_seguimiento=codigo.strip().upper()).first()

    @classmethod
    def get_by_hash_comprobante(cls, huella):
        """Busca un pago que ya haya usado este mismo archivo (RF-04)."""
        if not huella:
            return None
        return cls.query.filter(
            cls.hash_comprobante == huella,
            cls.estado != 'anulado'
        ).first()

    @classmethod
    def get_pendientes(cls):
        """Pagos esperando verificación, del más viejo al más nuevo."""
        return cls.query.filter_by(estado='pendiente').order_by(cls.created_at.asc()).all()

    @classmethod
    def get_de_cuota(cls, aportante_id, ejercicio_id, estado):
        """Pagos de cuota de una persona en un ejercicio, con un estado dado.

        Lo usan el cálculo del saldo (con estado 'verificado') y el cuadro de
        "en revisión" (con estado 'pendiente').
        """
        return cls.query.filter(
            cls.aportante_id == aportante_id,
            cls.ejercicio_id == ejercicio_id,
            cls.estado == estado,
            cls.tipo.in_(TIPOS_DE_CUOTA)
        ).all()

    # ============================================
    # PARA MOSTRAR EN PANTALLA
    # ============================================

    @property
    def estado_legible(self):
        return ESTADOS_LEGIBLES.get(self.estado, self.estado)

    @property
    def tipo_legible(self):
        return TIPOS_LEGIBLES.get(self.tipo, self.tipo)

    def __repr__(self):
        return '<Pago {} - {}>'.format(self.codigo_seguimiento, self.estado)
