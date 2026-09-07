"""Formularios del panel de administración: cuota y apertura de ejercicio.

Estos dos controles NO pasan por validaciones.validar_importe(): ya usaban
antes una regla más simple y un mensaje genérico (round/float/mayor a cero),
distinto del que ve el aportante en los formularios públicos. Se mantiene
así para no cambiar el mensaje que ve la Cooperadora.
"""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import ValidationError


def _importe_positivo(mensaje):
    def _validador(form, field):
        try:
            monto = round(float(field.data), 2)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError(mensaje)
    return _validador


class FormularioEditarCuota(FlaskForm):
    cuota = StringField(validators=[_importe_positivo('El monto de la cuota no es válido.')])


class FormularioNuevoEjercicio(FlaskForm):
    anio = StringField()
    cuota = StringField()
    fecha_asamblea = StringField()

    def validate(self, extra_validators=None):
        """anio y cuota se controlan juntos, con un solo mensaje (como hoy)."""
        if not super().validate(extra_validators=extra_validators):
            return False

        try:
            int(self.anio.data)
            monto = round(float(self.cuota.data), 2)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            self.cuota.errors.append('Año o cuota inválidos.')
            return False

        return True
