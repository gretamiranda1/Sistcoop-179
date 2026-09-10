"""Un código de transacción no se puede reusar cruzando pago individual y grupal.

codigo_transaccion_en_uso() (servicios/pagos.py) ya mira las dos tablas antes
de aceptar un alta, en cualquiera de los dos sentidos.
"""
from datetime import date

import pytest

from app.servicios import pagos as servicio_pagos
from app.servicios import pagos_grupales as servicio_grupales
from app.servicios.pagos import ErrorDeCarga

MENSAJE_REPETIDO = ('Ese número de operación ya fue cargado en otro pago. '
                    'Si creés que es un error, escribile a la Cooperadora.')


def _datos_grupal(codigo, huella, dni_1, dni_2, carrera):
    return {
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': codigo,
        'hash_comprobante': huella,
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': dni_1, 'nombre': 'Persona', 'apellido': 'Uno', 'carrera_id': carrera.id,'anio': 1,},
            {'dni': dni_2, 'nombre': 'Persona', 'apellido': 'Dos', 'carrera_id': carrera.id,'anio': 1,},
        ],
    }


def test_codigo_de_pago_individual_bloquea_un_pago_grupal(db, ejercicio, fondo_capital, datos_de_cuota, carrera):
    servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('30111111', 5000, 'OPCRUZADO1', 'huella-cruzada-1'))

    with pytest.raises(ErrorDeCarga) as excinfo:
        servicio_grupales.procesar_pago_grupal(
            _datos_grupal('OPCRUZADO1', 'huella-cruzada-2', '30222222', '30333333', carrera))

    assert excinfo.value.errores == [MENSAJE_REPETIDO]


def test_codigo_de_pago_grupal_bloquea_un_pago_individual(db, ejercicio, fondo_capital, datos_de_cuota, carrera):
    servicio_grupales.procesar_pago_grupal(
        _datos_grupal('OPCRUZADO2', 'huella-cruzada-3', '30444444', '30555555', carrera))

    with pytest.raises(ErrorDeCarga) as excinfo:
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('30666666', 5000, 'OPCRUZADO2', 'huella-cruzada-4'))

    assert excinfo.value.errores == [MENSAJE_REPETIDO]
