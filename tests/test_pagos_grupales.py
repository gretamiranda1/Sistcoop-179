"""Pago grupal (servicios/pagos_grupales.py): el reparto tiene que cerrar."""
from datetime import date
from unittest.mock import patch
import pytest

from app.servicios import pagos_grupales as servicio_grupales
from app.servicios import pagos as servicio_pagos

from decimal import Decimal


def test_verificar_pago_grupal_hace_rollback_si_falla(
    db, ejercicio, fondo_capital, carrera, admin
):
    grupal, _ = servicio_grupales.procesar_pago_grupal({
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPROLLBACK1',
        'hash_comprobante': 'huella-rollback-1',
        'comprobante_nombre': 'rollback.png',
        'tipo_distribucion': 'auto',
        'personas': [
            {
                'dni': '45111111',
                'nombre': 'Ana',
                'apellido': 'Test',
                'carrera_id': carrera.id,
                'anio': '1°',
            },
            {
                'dni': '45222222',
                'nombre': 'Beto',
                'apellido': 'Test',
                'carrera_id': carrera.id,
                'anio': '1°',
            },
        ],
    })

    verificar_original = servicio_pagos.verificar_pago
    llamadas = {'cantidad': 0}

    def verificar_con_falla(*args, **kwargs):
        llamadas['cantidad'] += 1

        if llamadas['cantidad'] == 2:
            raise RuntimeError('Falla simulada')

        return verificar_original(*args, **kwargs)

    with patch(
        'app.servicios.pagos.verificar_pago',
        side_effect=verificar_con_falla
    ):
        with pytest.raises(RuntimeError):
            servicio_grupales.verificar_pago_grupal(
                grupal.id,
                admin.id
            )

    db.session.rollback()

    grupal = type(grupal).query.get(grupal.id)

    assert grupal.estado == 'pendiente'

    for detalle in grupal.detalles.all():
        assert detalle.estado == 'pendiente'

    for pago in grupal.pagos.all():
        assert pago.estado == 'pendiente'

def test_pago_grupal_reparte_el_importe_y_la_suma_cierra(db, ejercicio, fondo_capital, carrera):
    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPGRUPAL1',
        'hash_comprobante': 'huella-grupal-1',
        'comprobante_nombre': 'grupal.png',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '36111111', 'nombre': 'Ana', 'apellido': 'Gómez', 'carrera_id': carrera.id , 'anio': 1,},
            {'dni': '36222222', 'nombre': 'Beto', 'apellido': 'Gómez', 'carrera_id': carrera.id ,'anio': 1,},
        ],
    })

    assert grupal.estado == 'pendiente'
    assert len(resumen['asignaciones']) == 2
    assert grupal.pagos.count() == 2

    suma_asignada = sum(persona['monto'] for persona in resumen['asignaciones'])
    assert suma_asignada + resumen['excedente'] == 40000

    # A cada una le falta pagar $30.000 (total $60.000) y sólo se transfirieron
    # $40.000: se reparten los $40.000 enteros, $20.000 a cada una, sin
    # excedente.
    assert resumen['asignaciones'][0]['monto'] == 20000
    assert resumen['excedente'] == 0


def test_repartir_a_mano_funciona_con_decimal_y_redondea_bien():
    personas = [{'falta': Decimal('100.00')}]

    personas, excedente = servicio_grupales.repartir_a_mano(
        personas, Decimal('2.68'), ['2.675']
    )

    assert personas[0]['monto_asignado'] == Decimal('2.68')


def test_repartir_en_partes_iguales_funciona_con_decimal():
    personas = [
        {'falta': Decimal('100.00')},
        {'falta': Decimal('100.00')},
        {'falta': Decimal('100.00')},
    ]

    personas, excedente = servicio_grupales.repartir_en_partes_iguales(
        personas, Decimal('10.00')
    )

    total_asignado = sum(p['monto_asignado'] for p in personas)
    assert total_asignado + excedente == Decimal('10.00')
