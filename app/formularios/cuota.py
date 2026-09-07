"""Formularios del pago de cuota del portal público (RF-01, RF-02).

Mismos campos y mismos mensajes que controlaba antes
servicios/pagos.validar_datos(): esto no agrega ninguna regla nueva, sólo
mueve el control de formato a esta capa para mostrarlo en pantalla antes de
llamar al servicio.
"""

from flask_wtf import FlaskForm
from wtforms import StringField

from app.formularios._comunes import (
    dni_valido, fecha_transferencia_valida_si_hay, importe_valido,
    nombre_valido, quitar_espacios,
)


class FormularioCuotaIndividual(FlaskForm):
    nombre = StringField(filters=[quitar_espacios], validators=[nombre_valido('nombre')])
    apellido = StringField(filters=[quitar_espacios], validators=[nombre_valido('apellido')])
    dni = StringField(filters=[quitar_espacios], validators=[dni_valido])
    carrera_id = StringField()
    anio = StringField()
    importe = StringField(validators=[importe_valido])
    fecha = StringField(validators=[fecha_transferencia_valida_si_hay])
    codigo_transaccion = StringField()
    observaciones = StringField()
    solicita_libreta = StringField()


class FormularioCuotaGrupal(FlaskForm):
    """Sólo los campos de la transferencia en sí.

    Las personas del grupo (dni_1, nombre_1, ...) son filas dinámicas que
    agrega o saca el JavaScript: servicios/pagos_grupales.normalizar_personas()
    ya valida cada una con las mismas funciones de validaciones.py, así que
    esa parte no pasa por un FlaskForm.
    """
    importe_total = StringField(validators=[importe_valido])
    fecha = StringField(validators=[fecha_transferencia_valida_si_hay])
    codigo_transaccion = StringField()
    tipo_distribucion = StringField()
