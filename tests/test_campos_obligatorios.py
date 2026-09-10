"""Campos que el HTML marca como obligatorios tienen que serlo también en el
servidor, para cuando alguien manda el POST sin pasar por el formulario
(issue #70)."""
import pytest
from datetime import date
from app.servicios import pagos as servicio_pagos
from app.servicios.pagos import ErrorDeCarga


@pytest.fixture
def datos_de_cuota(carrera):
    def _fabrica(dni, importe, codigo_transaccion, huella, **extra):
        datos = {
            'nombre': 'Persona',
            'apellido': 'De Prueba',
            'dni': dni,
            'importe': importe,
            'fecha': date.today().isoformat(),
            'codigo_transaccion': codigo_transaccion,
            'hash_comprobante': huella,
            'comprobante_nombre': 'comprobante-' + huella + '.png',
            'carrera_id': carrera.id,
            'anio': 1,
        }
        datos.update(extra)
        return datos

    return _fabrica

def test_libreta_duplicado_sin_carrera_se_rechaza(db, fondo_capital, datos_de_cuota):
    data = datos_de_cuota('43111111', 5000, 'OPLIBRETAQA1', 'huella-libreta-1')
    data['tipo'] = 'libreta_duplicado'
    data['carrera_id'] = None
    data['anio'] = '1°'

    with pytest.raises(ErrorDeCarga) as excinfo:
        servicio_pagos.crear_pago_publico(data)

    assert any('carrera' in e.lower() for e in excinfo.value.errores)


def test_libreta_duplicado_sin_anio_se_rechaza(db, fondo_capital, datos_de_cuota, carrera):
    data = datos_de_cuota('43222222', 5000, 'OPLIBRETAQA2', 'huella-libreta-2')
    data['tipo'] = 'libreta_duplicado'
    data['carrera_id'] = carrera.id
    data['anio'] = None

    with pytest.raises(ErrorDeCarga) as excinfo:
        servicio_pagos.crear_pago_publico(data)

    assert any('año' in e.lower() for e in excinfo.value.errores)


def test_libreta_duplicado_con_carrera_y_anio_se_acepta(db, fondo_capital, datos_de_cuota, carrera):
    data = datos_de_cuota('43333333', 5000, 'OPLIBRETAQA3', 'huella-libreta-3')
    data['tipo'] = 'libreta_duplicado'
    data['carrera_id'] = carrera.id
    data['anio'] = '1°'

    pago = servicio_pagos.crear_pago_publico(data)

    assert pago.tipo == 'libreta_duplicado'