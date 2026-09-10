"""Los fondos no se mezclan (RF-09): general y de carrera son bolsillos aparte."""
from datetime import date
from app.servicios import pagos as servicio_pagos


def test_fondos_de_cooperadora_y_de_carrera_no_se_mezclan(
        db, ejercicio, fondo_capital, fondo_carrera, carrera, admin):
    saldo_capital_inicial = float(fondo_capital.saldo)
    saldo_carrera_inicial = float(fondo_carrera.saldo)

    # Aporte adicional al fondo general
    pago_general = servicio_pagos.crear_pago_publico({
        'nombre': 'Sponsor', 'apellido': 'General', 'dni': '40111111',
        'destino': 'capital', 'tipo': 'adicional', 'importe': 5000,
        'codigo_transaccion': 'OPGENERAL', 'hash_comprobante': 'huella-general',
        'fecha': date.today().isoformat(),
    })
    servicio_pagos.verificar_pago(pago_general.id, admin.id)

    assert float(fondo_capital.saldo) == saldo_capital_inicial + 5000
    assert float(fondo_carrera.saldo) == saldo_carrera_inicial

    # Aporte al fondo propio de la carrera
    pago_carrera = servicio_pagos.crear_pago_publico({
        'nombre': 'Sponsor', 'apellido': 'Carrera', 'dni': '40222222',
        'destino': 'carrera', 'carrera_destino_id': carrera.id,
        'tipo': 'aporte_carrera', 'importe': 3000,
        'codigo_transaccion': 'OPCARRERA', 'hash_comprobante': 'huella-carrera',
        'fecha': date.today().isoformat(),
    })
    servicio_pagos.verificar_pago(pago_carrera.id, admin.id)

    assert float(fondo_carrera.saldo) == saldo_carrera_inicial + 3000
    # El aporte a la carrera no le sumó nada al fondo general
    assert float(fondo_capital.saldo) == saldo_capital_inicial + 5000
