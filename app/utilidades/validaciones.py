"""Validaciones que usamos en todo el sistema.

Son funciones sueltas: se importan y se llaman, sin crear ningún objeto.

    from app.utilidades import validaciones
    validaciones.validar_dni('30123456')

Todo esto se vuelve a controlar en el servidor aunque el navegador ya lo
haya controlado, porque el HTML se puede editar y el formulario se puede
mandar sin pasar por la pantalla (RNF-03).
"""

import re
from datetime import datetime, date, timedelta

# Una transferencia no puede ser de hace más de este tiempo. Cuando aparece
# una fecha más vieja, casi siempre es un error de tipeo en el año.
DIAS_MAXIMOS_HACIA_ATRAS = 400


# ============================================
# DNI
# ============================================

def limpiar_dni(dni):
    """Deja solamente los números: saca puntos, espacios y guiones."""
    texto = str(dni or '')
    limpio = ''
    for caracter in texto:
        if caracter.isdigit():
            limpio = limpio + caracter
    return limpio


def validar_dni(dni):
    """DNI argentino: 7 u 8 dígitos."""
    limpio = limpiar_dni(dni)

    if len(limpio) < 7 or len(limpio) > 8:
        return False

    # 00000000 o 11111111 son datos de relleno, no un documento
    if len(set(limpio)) == 1:
        return False

    return True


# ============================================
# CUIT
# ============================================

def limpiar_cuit(cuit):
    """Deja solamente los números del CUIT."""
    return limpiar_dni(cuit)


def validar_cuit(cuit):
    """CUIT argentino: 11 dígitos, y el último tiene que ser el verificador.

    El dígito verificador se calcula multiplicando los primeros diez dígitos
    por una serie fija, sumando todo y sacando el resto de dividir por 11.
    """
    limpio = limpiar_cuit(cuit)

    if len(limpio) != 11:
        return False

    serie = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = 0
    for i in range(10):
        suma = suma + int(limpio[i]) * serie[i]

    resto = suma % 11

    if resto == 0:
        verificador = 0
    elif resto == 1:
        verificador = 9
    else:
        verificador = 11 - resto

    return int(limpio[10]) == verificador


def formatear_cuit(cuit):
    """Devuelve el CUIT como XX-XXXXXXXX-X."""
    limpio = limpiar_cuit(cuit)
    if len(limpio) != 11:
        return cuit
    return limpio[0:2] + '-' + limpio[2:10] + '-' + limpio[10]


# ============================================
# NOMBRES
# ============================================

def validar_nombre(nombre):
    """Nombre o apellido válido.

    Acepta acentos, apóstrofes y guiones, porque "D'Angelo", "Ñúñez" y
    "Sáenz-Peña" son apellidos reales.
    """
    texto = (nombre or '').strip()
    if len(texto) < 2:
        return False

    patron = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'\-\. ]*$"
    return re.match(patron, texto) is not None


# ============================================
# IMPORTES
# ============================================

IMPORTE_MINIMO = 1
IMPORTE_MAXIMO = 1000000


def validar_importe(importe):
    """Devuelve (es_valido, mensaje_de_error).

    Un importe válido debe estar dentro de los rangos permitidos.
    """
    if importe is None or importe == '':
        return False, 'Falta el importe.'

    try:
        valor = float(importe)
    except (ValueError, TypeError):
        return False, 'El importe no es un número válido.'

    if valor < IMPORTE_MINIMO:
        return False, f'El importe debe ser mayor o igual a ${IMPORTE_MINIMO}.'

    if valor > IMPORTE_MAXIMO:
        return False, f'El importe debe ser menor o igual a ${IMPORTE_MAXIMO}.'

    return True, None


# ============================================
# FECHAS
# ============================================

def validar_fecha(fecha_texto):
    """Fecha en formato AAAA-MM-DD. Devuelve (es_valida, mensaje_de_error)."""
    try:
        fecha = datetime.strptime(fecha_texto, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return False, 'La fecha no tiene un formato válido.'

    if fecha.year < 1900 or fecha.year > 2100:
        return False, 'El año de la fecha no es razonable.'

    return True, None


def validar_fecha_transferencia(fecha_texto):
    """Fecha de una transferencia que ya se hizo.

    No puede ser de mañana (todavía no pasó) ni de hace más de un año, porque
    el pago terminaría imputado a un ejercicio que no corresponde.
    """
    valida, mensaje = validar_fecha(fecha_texto)
    if not valida:
        return False, mensaje

    fecha = datetime.strptime(fecha_texto, '%Y-%m-%d').date()
    hoy = date.today()

    if fecha > hoy:
        return False, 'La fecha de la transferencia no puede ser futura.'

    if fecha < hoy - timedelta(days=DIAS_MAXIMOS_HACIA_ATRAS):
        return False, ('La fecha de la transferencia es demasiado vieja. '
                       'Fijate que el año esté bien escrito.')

    return True, None


def texto_a_fecha(fecha_texto):
    """Pasa un 'AAAA-MM-DD' a fecha. Si no se puede, devuelve la de hoy."""
    try:
        return datetime.strptime(fecha_texto, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return date.today()
