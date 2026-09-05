"""Validadores de WTForms que envuelven las funciones de utilidades/validaciones.py.

Ningún formulario de app/formularios/ duplica la lógica de DNI, CUIT, importe
ni fecha: todos llaman a estas mismas funciones, que a su vez llaman a
validaciones.py. Así la regla queda escrita en un solo lugar, la use un
formulario web o validar_datos() del lado del servicio.
"""

from wtforms.validators import ValidationError

from app.utilidades import validaciones


def quitar_espacios(valor):
    """Filtro de WTForms: recorta espacios, igual que hace cada servicio hoy."""
    return (valor or '').strip()


def nombre_valido(etiqueta, requerido=True):
    """Nombre o apellido: primero que no falte (si corresponde), después el formato.

    Mismos mensajes que usa hoy servicios/pagos.validar_datos(): "Falta el
    {etiqueta}." o "El {etiqueta} solo admite caracteres alfabéticos."
    """
    def _validador(form, field):
        texto = field.data or ''
        if not texto:
            if requerido:
                raise ValidationError('Falta el {}.'.format(etiqueta))
            return
        if not validaciones.validar_nombre(texto):
            raise ValidationError('El {} solo admite caracteres alfabéticos.'.format(etiqueta))
    return _validador


def dni_valido(form, field):
    """Mismos mensajes que usa hoy validar_datos() para el DNI."""
    texto = field.data or ''
    if not texto:
        raise ValidationError('Falta el DNI.')
    if not validaciones.validar_dni(texto):
        raise ValidationError('El DNI no es válido: tiene que tener 7 u 8 dígitos, sin puntos.')


def cuit_valido_si_hay(form, field):
    """El CUIT es opcional: sólo se valida el formato si vino completo."""
    if field.data and not validaciones.validar_cuit(field.data):
        raise ValidationError('El CUIT no es válido. Revisá el número, incluido el '
                              'dígito verificador.')


def importe_valido(form, field):
    ok, mensaje = validaciones.validar_importe(field.data)
    if not ok:
        raise ValidationError(mensaje)


def fecha_valida_si_hay(form, field):
    """Fecha en formato AAAA-MM-DD, sin más controles que el formato y el año.

    La fecha es opcional a este nivel: si no vino, el llamador decide qué
    hacer (ver validaciones.texto_a_fecha).
    """
    if not field.data:
        return
    ok, mensaje = validaciones.validar_fecha(field.data)
    if not ok:
        raise ValidationError(mensaje)


def fecha_transferencia_valida_si_hay(form, field):
    """Fecha de una transferencia ya hecha: ni futura ni demasiado vieja.

    También opcional a este nivel, por el mismo motivo que fecha_valida_si_hay.
    """
    if not field.data:
        return
    ok, mensaje = validaciones.validar_fecha_transferencia(field.data)
    if not ok:
        raise ValidationError(mensaje)
