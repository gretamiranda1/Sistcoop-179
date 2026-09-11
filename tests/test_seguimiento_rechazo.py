"""El motivo del rechazo tiene que verse en la consulta pública (issue #64)."""
from datetime import date

from app.servicios import pagos as servicio_pagos
from app.servicios import pagos_grupales as servicio_grupales

MOTIVO = 'La transferencia no figura en el extracto del período.'


def test_motivo_de_rechazo_aparece_al_buscar_por_dni(
        client, db, admin, ejercicio, fondo_capital, carrera, iniciar_sesion):
    pago, _ = servicio_pagos.crear_pago_de_cuota({
        'nombre': 'Persona', 'apellido': 'De Prueba', 'dni': '60111111',
        'carrera_id': carrera.id, 'anio': '1°',
        'importe': 15000, 'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPRECHAZOQA', 'hash_comprobante': 'huella-rechazo-1',
    })
    servicio_pagos.rechazar_pago(pago.id, admin.id, MOTIVO)

    resp = client.get('/aportante/seguimiento?dni=60111111')

    assert MOTIVO in resp.get_data(as_text=True)


def test_motivo_de_rechazo_aparece_en_transferencia_grupal(
        client, db, admin, ejercicio, fondo_capital, carrera, iniciar_sesion):
    grupal, _ = servicio_grupales.procesar_pago_grupal({
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPGRUPALRECHAZOQA',
        'hash_comprobante': 'huella-rechazo-grupal',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '60222222', 'nombre': 'Ana', 'apellido': 'Perez',
             'carrera_id': carrera.id, 'anio': '1°'},
            {'dni': '60333333', 'nombre': 'Bea', 'apellido': 'Perez',
             'carrera_id': carrera.id, 'anio': '1°'},
        ],
    })
    servicio_grupales.rechazar_pago_grupal(grupal.id, admin.id, MOTIVO)

    resp = client.post('/aportante/seguimiento', data={'modo': 'codigo', 'codigo': grupal.codigo_seguimiento})

    assert MOTIVO in resp.get_data(as_text=True)
