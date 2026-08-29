from datetime import datetime

from app.extensions import db
from app.modelos.pagos import Pago


class Ejercicio(db.Model):
    """Un año contable de la Cooperadora, con el importe de la cuota.

    La cuota se fija en la asamblea anual y no se puede cambiar durante el
    ejercicio (Propuesta, sección 6). Ver admite_cambio_de_cuota.
    """

    __tablename__ = 'ejercicios'

    id = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False, unique=True)
    cuota = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_asamblea = db.Column(db.Date)
    activo = db.Column(db.Boolean, default=True)
    cerrado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_ejercicio_vigente(cls):
        """El ejercicio abierto, contra el que se imputan los pagos"""
        return cls.query.filter_by(activo=True, cerrado=False).first()

    @classmethod
    def get_cuota_vigente(cls):
        """Importe de la cuota del ejercicio vigente, o 0 si no hay ninguno"""
        ejercicio = cls.get_ejercicio_vigente()
        if not ejercicio:
            return 0
        return float(ejercicio.cuota)

    def admite_cambio_de_cuota(self):
        """¿Todavía se puede corregir el importe de la cuota?

        Sólo mientras no haya ningún pago imputado: si ya hay pagos, cambiar
        la cuota le modificaría el saldo hacia atrás a todos los aportantes.
        Después de eso lo que corresponde es cerrar el ejercicio y abrir uno
        nuevo.

        Devuelve (se_puede, motivo).
        """
        if self.cerrado:
            return False, 'El ejercicio está cerrado.'

        cantidad = Pago.query.filter(
            Pago.ejercicio_id == self.id,
            Pago.estado != 'anulado'
        ).count()

        if cantidad > 0:
            motivo = (
                'El ejercicio {} ya tiene {} pago(s) cargado(s). La cuota se fija '
                'en asamblea y no se puede modificar durante el ejercicio vigente.'
            ).format(self.anio, cantidad)
            return False, motivo

        return True, None

    def __repr__(self):
        return '<Ejercicio {}>'.format(self.anio)
