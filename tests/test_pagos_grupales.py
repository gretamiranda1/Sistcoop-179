"""Pago grupal (servicios/pagos_grupales.py): el reparto tiene que cerrar."""
from datetime import date

from app.servicios import pagos_grupales as servicio_grupales
from app.servicios import pagos as servicio_pagos

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


def test_reparto_en_partes_iguales_no_asigna_mas_de_lo_transferido(db, ejercicio, fondo_capital, carrera):
    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 100,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPCENTAVOSQA1',
        'hash_comprobante': 'huella-centavos-1',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '40111111', 'nombre': 'Ana', 'apellido': 'Lopez',
             'carrera_id': carrera.id, 'anio': '1°'},
            {'dni': '40222222', 'nombre': 'Bea', 'apellido': 'Lopez',
             'carrera_id': carrera.id, 'anio': '1°'},
            {'dni': '40333333', 'nombre': 'Cami', 'apellido': 'Lopez',
             'carrera_id': carrera.id, 'anio': '1°'},
        ],
    })
    suma_asignada = sum(persona['monto'] for persona in resumen['asignaciones'])
    assert suma_asignada <= 100
    assert round(suma_asignada + resumen['excedente'], 2) == 100


def test_reparto_con_siete_personas_no_supera_lo_transferido(db, ejercicio, fondo_capital, carrera):
    nombres = ['Ana', 'Bea', 'Cami', 'Dana', 'Eli', 'Fer', 'Gaby']
    personas = [
        {'dni': '41{:06d}'.format(i), 'nombre': nombres[i - 1], 'apellido': 'Test',
         'carrera_id': carrera.id, 'anio': '1°'}
        for i in range(1, 8)
    ]
    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 100,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPCENTAVOSQA2',
        'hash_comprobante': 'huella-centavos-2',
        'tipo_distribucion': 'auto',
        'personas': personas,
    })
    suma_asignada = sum(persona['monto'] for persona in resumen['asignaciones'])
    assert suma_asignada <= 100


def test_reparto_no_falla_si_alguien_del_grupo_ya_completo_la_cuota(
        db, ejercicio, fondo_capital, carrera, admin):
    pago_previo, _ = servicio_pagos.crear_pago_de_cuota({
        'nombre': 'Diego', 'apellido': 'YaPago', 'dni': '42111111',
        'carrera_id': carrera.id, 'anio': '1°',
        'importe': ejercicio.cuota, 'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPPREVIOQA', 'hash_comprobante': 'huella-previo',
    })
    servicio_pagos.verificar_pago(pago_previo.id, admin.id)

    # Diego entra a un pago grupal junto con alguien que sí debe: no tiene
    # que romper aunque él ya esté al día.
    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 15000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPGRUPALDIEGO',
        'hash_comprobante': 'huella-grupal-diego',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '42111111', 'nombre': 'Diego', 'apellido': 'YaPago',
             'carrera_id': carrera.id, 'anio': '1°'},
            {'dni': '42222222', 'nombre': 'Elena', 'apellido': 'Debe',
             'carrera_id': carrera.id, 'anio': '1°'},
        ],
    })

    # A Diego no se le asigna nada; sólo aparece Elena en el resumen.
    assert len(resumen['asignaciones']) == 1
    assert resumen['asignaciones'][0]['dni'] == '42222222'