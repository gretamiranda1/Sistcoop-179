"""Formularios de las dos solapas de app/vistas/aportante/solicitud.html.

Mismos campos y mensajes que controlaban antes, cada uno en su controlador:
validar_solicitud_de_fondos() para el pedido de fondos, y
servicios/pagos.validar_datos() para el duplicado de libreta.
"""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import ValidationError

from app.formularios._comunes import (
    dni_valido, fecha_transferencia_valida_si_hay, fecha_valida_si_hay,
    importe_valido, nombre_valido, quitar_espacios,
)

TIPOS_SOLICITUD_FONDOS = ('fondos', 'evento', 'viaje')


def _requerido(mensaje):
    def _validador(form, field):
        if not (field.data or '').strip():
            raise ValidationError(mensaje)
    return _validador


def _tipo_valido(form, field):
    if field.data not in TIPOS_SOLICITUD_FONDOS:
        raise ValidationError('Elegí qué estás solicitando.')


def _justificacion_valida(form, field):
    texto = (field.data or '').strip()
    if len(texto) < 20:
        raise ValidationError('La justificación tiene que explicar el pedido: escribí '
                              'al menos un par de renglones.')


class FormularioSolicitudFondos(FlaskForm):
    """Pedido de fondos, evento o viaje de un curso o un docente."""

    responsable = StringField(filters=[quitar_espacios],
                              validators=[_requerido('Falta el nombre del responsable.')])
    contacto = StringField(filters=[quitar_espacios],
                           validators=[_requerido('Falta un teléfono o correo de contacto.')])
    carrera_id = StringField()
    curso = StringField(filters=[quitar_espacios])
    tipo = StringField(validators=[_tipo_valido])
    importe = StringField(validators=[importe_valido])
    concepto = StringField(filters=[quitar_espacios],
                           validators=[_requerido('Falta el concepto de la solicitud.')])
    fecha_estimada = StringField(validators=[fecha_valida_si_hay])
    justificacion = StringField(filters=[quitar_espacios], validators=[_justificacion_valida])


class FormularioDuplicadoLibreta(FlaskForm):
    """Duplicado de libreta: se guarda como un Pago (ver servicios/pagos.py).

    El apellido acá es obligatorio: la llamada a crear_pago_publico() para
    este flujo usa tipo='libreta_duplicado', y pide_apellido=(tipo !=
    'adicional') da True.
    """

    dni = StringField(filters=[quitar_espacios], validators=[dni_valido])
    nombre = StringField(filters=[quitar_espacios], validators=[nombre_valido('nombre')])
    apellido = StringField(filters=[quitar_espacios], validators=[nombre_valido('apellido')])
    carrera_id = StringField()
    anio = StringField()
    motivo = StringField()
    importe = StringField(validators=[importe_valido])
    fecha = StringField(validators=[fecha_transferencia_valida_si_hay])
    codigo_transaccion = StringField()
    observaciones = StringField()
