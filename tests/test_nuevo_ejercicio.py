def test_fecha_asamblea_invalida_no_rompe_el_servidor(client, db, admin, iniciar_sesion):
    iniciar_sesion(client, admin)

    respuesta = client.post('/admin/nuevo-ejercicio', data={
        'anio': '2030',
        'cuota': '30000',
        'fecha_asamblea': 'no-es-una-fecha',
    })

    assert respuesta.status_code == 302