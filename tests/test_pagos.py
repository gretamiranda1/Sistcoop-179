"""Circuito de un pago individual (servicios/pagos.py).

La regla central del sistema (cargar NO acredita, verificar SÍ) y los dos
controles de duplicado del RF-04.
"""
import pytest

from app.modelos.saldos import SaldoAportante
from app.servicios import pagos as servicio_pagos
from app.servicios.pagos import ErrorDeCarga


def test_pago_nace_pendiente_y_no_mueve_ningun_saldo(
        db, ejercicio, fondo_capital, datos_de_cuota):
    saldo_fondo_inicial = float(fondo_capital.saldo)

    pago, saldo = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('31111111', 15000, 'OPTEST0001', 'huella-0001'))

    assert pago.estado == 'pendiente'
    assert pago.codigo_seguimiento.startswith('SC-')
    assert float(saldo.pagado) == 0
    assert saldo.en_revision == 15000
    assert float(fondo_capital.saldo) == saldo_fondo_inicial


def test_verificar_un_pago_impacta_el_saldo_del_aportante(
        db, ejercicio, fondo_capital, admin, datos_de_cuota):
    saldo_fondo_inicial = float(fondo_capital.saldo)

    pago, saldo = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('31111112', 15000, 'OPTEST0002', 'huella-0002'))

    servicio_pagos.verificar_pago(pago.id, admin.id, numero_recibo='0001')

    assert pago.estado == 'verificado'
    assert float(saldo.pagado) == 15000
    assert saldo.en_revision == 0
    assert float(fondo_capital.saldo) == saldo_fondo_inicial + 15000
    assert fondo_capital.movimientos.count() == 1

    saldo_recargado = SaldoAportante.get_por_aportante(saldo.aportante_id, saldo.ejercicio_id)
    assert float(saldo_recargado.saldo_pendiente) == 30000 - 15000


def test_codigo_de_transaccion_repetido_se_rechaza(db, ejercicio, fondo_capital, datos_de_cuota):
    servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('32222222', 30000, 'OPREPETIDO', 'huella-a'))

    with pytest.raises(ErrorDeCarga):
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('33222222', 30000, 'OPREPETIDO', 'huella-b'))


def test_comprobante_con_el_mismo_hash_se_rechaza(db, ejercicio, fondo_capital, datos_de_cuota):
    servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('34222222', 30000, 'OPTEST0003', 'huella-repetida'))

    with pytest.raises(ErrorDeCarga):
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('35222222', 30000, 'OPTEST0004', 'huella-repetida'))


def test_no_se_puede_reverificar_un_pago_rechazado(
        db, ejercicio, fondo_capital, admin, datos_de_cuota):
    pago, _ = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('36222222', 15000, 'OPTEST0005', 'huella-0005'))

    servicio_pagos.rechazar_pago(pago.id, admin.id, 'no figura en el extracto')

    with pytest.raises(ErrorDeCarga):
        servicio_pagos.verificar_pago(pago.id, admin.id)
