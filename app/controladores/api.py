"""Validaciones en vivo que consume el JavaScript de los formularios del portal.

Son todas POST, así que Flask-WTF les pide el token CSRF. El JavaScript lo
manda en la cabecera X-CSRFToken (ver sistcoop.js). Si no lo mandara, el
servidor contestaría 400 y ninguna validación en vivo funcionaría.

Antes vivían en controladores/aportantes.py; se separaron a su propio
blueprint porque no son pantallas (no devuelven HTML) sino la API que
consultan las pantallas del portal.
"""

from flask import Blueprint, jsonify, request

from app.servicios import pagos as servicio_pagos
from app.utilidades import validaciones
from app.utilidades.limite_peticiones import excede_limite

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/validar-dni', methods=['POST'])
def api_validar_dni():
    """Dice si el DNI tiene formato válido.

    No devuelve ningún dato de la persona. La versión anterior devolvía
    nombre, apellido y carrera de cualquier DNI, así que probando números se
    podía armar un padrón de alumnos (RNF-02).
    """
    if excede_limite('api_dni', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    valido = validaciones.validar_dni(datos.get('dni', ''))

    return jsonify({
        'valido': valido,
        'mensaje': '' if valido else 'El DNI tiene que tener 7 u 8 dígitos, sin puntos.'
    })


@api_bp.route('/api/validar-cuit', methods=['POST'])
def api_validar_cuit():
    if excede_limite('api_cuit', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    cuit = datos.get('cuit', '')
    valido = validaciones.validar_cuit(cuit)

    return jsonify({
        'valido': valido,
        'formateado': validaciones.formatear_cuit(cuit) if valido else None,
        'mensaje': 'CUIT válido' if valido
                   else 'El CUIT no es válido. Revisá el dígito verificador.'
    })


@api_bp.route('/api/validar-transaccion', methods=['POST'])
def api_validar_transaccion():
    """Avisa si el número de operación ya se usó (RF-04)."""
    if excede_limite('api_transaccion', limite=30, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    en_uso = servicio_pagos.codigo_transaccion_en_uso((datos.get('codigo') or '').strip())

    return jsonify({
        'disponible': not en_uso,
        'mensaje': 'Ese número ya fue cargado en otro pago.' if en_uso
                   else 'El número no figura cargado.'
    })


@api_bp.route('/api/estado-cuota', methods=['POST'])
def api_estado_cuota():
    """Cómo viene la cuota del DNI en el ejercicio vigente.

    Alimenta el cuadro que el aportante ve antes de mandar el formulario.
    Devuelve importes, nunca datos personales.
    """
    if excede_limite('api_estado', limite=20, ventana=60):
        return jsonify({'error': 'Demasiadas consultas seguidas.'}), 429

    datos = request.get_json(silent=True) or {}
    dni = datos.get('dni', '')

    if not validaciones.validar_dni(dni):
        return jsonify({'disponible': False})

    estado = servicio_pagos.estado_de_cuota(dni)
    if not estado:
        return jsonify({'disponible': False})

    estado['disponible'] = True
    return jsonify(estado)
