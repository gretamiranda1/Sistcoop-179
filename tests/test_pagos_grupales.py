"""Pago grupal (servicios/pagos_grupales.py): el reparto tiene que cerrar."""
from datetime import date

from app.servicios import pagos_grupales as servicio_grupales


def test_pago_grupal_reparte_el_importe_y_la_suma_cierra(db, ejercicio, fondo_capital):
    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OP-GRUPAL-1',
        'hash_comprobante': 'huella-grupal-1',
        'comprobante_nombre': 'grupal.png',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '36111111', 'nombre': 'Ana', 'apellido': 'Gómez'},
            {'dni': '36222222', 'nombre': 'Beto', 'apellido': 'Gómez'},
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
