"""Formularios de los aportes adicionales (RF-09, RF-11).

Mismos campos y mensajes que controlaba antes servicios/pagos.validar_datos()
para cada una de las dos solapas de app/vistas/aportante/adicional.html.
"""

from flask_wtf import FlaskForm
from wtforms import StringField

from app.formularios._comunes import (
    cuit_valido_si_hay, dni_valido, fecha_transferencia_valida_si_hay,
    importe_valido, nombre_valido, quitar_espacios,
)


class FormularioAporteGeneral(FlaskForm):
    """Solapa "Aporte a la Cooperadora": va al fondo general (tipo='adicional').

    El apellido es opcional acá: puede firmarlo una empresa o alguien que no
    quiere dar más datos que el DNI (mismo motivo que hoy tiene
    crear_pago_publico(data, pide_apellido=(tipo != 'adicional')) en el
    servicio).
    """
    nombre = StringField(filters=[quitar_espacios], validators=[nombre_valido('nombre')])
    apellido = StringField(filters=[quitar_espacios],
                           validators=[nombre_valido('apellido', requerido=False)])
    dni = StringField(filters=[quitar_espacios], validators=[dni_valido])
    cuit = StringField(filters=[quitar_espacios], validators=[cuit_valido_si_hay])
    importe = StringField(validators=[importe_valido])
    fecha = StringField(validators=[fecha_transferencia_valida_si_hay])
    codigo_transaccion = StringField()
    observaciones = StringField()


class FormularioAporteCarrera(FlaskForm):
    """Solapa "Aporte a una carrera": va al fondo propio de la carrera elegida.

    Acá el apellido si es obligatorio, porque tipo='aporte_carrera' y
    pide_apellido=(tipo != 'adicional') da True.
    """
    carrera_id = StringField()
    nombre = StringField(filters=[quitar_espacios], validators=[nombre_valido('nombre')])
    apellido = StringField(filters=[quitar_espacios], validators=[nombre_valido('apellido')])
    dni = StringField(filters=[quitar_espacios], validators=[dni_valido])
    cuit = StringField(filters=[quitar_espacios], validators=[cuit_valido_si_hay])
    importe = StringField(validators=[importe_valido])
    fecha = StringField(validators=[fecha_transferencia_valida_si_hay])
    codigo_transaccion = StringField()
    observaciones = StringField()
