from app.servicios import pagos as servicio_pagos


def test_pago_rechazado_no_bloquea_el_cambio_de_cuota(db, ejercicio, fondo_capital, admin, datos_de_cuota):
    pago, _ = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('35111111', 15000, 'OPCUOTA0001', 'huella-cuota-0001')
    )
    servicio_pagos.rechazar_pago(pago.id, admin.id, 'no figura en el extracto')

    se_puede, motivo = ejercicio.admite_cambio_de_cuota()

    assert se_puede is True
    assert motivo is None


def test_pago_verificado_si_bloquea_el_cambio_de_cuota(db, ejercicio, fondo_capital, admin, datos_de_cuota):
    pago, _ = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('35222222', 15000, 'OPCUOTA0002', 'huella-cuota-0002')
    )
    servicio_pagos.verificar_pago(pago.id, admin.id)

    se_puede, motivo = ejercicio.admite_cambio_de_cuota()

    assert se_puede is False