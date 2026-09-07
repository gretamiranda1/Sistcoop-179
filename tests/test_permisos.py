"""El decorador @requiere_rol (app/seguridad/permisos.py) sobre una vista real."""


def test_vista_de_admin_rechaza_a_usuario_sin_el_rol_correspondiente(
        app, client, tesorera, iniciar_sesion):
    # panel() sólo admite 'admin' y 'asistente'; tesorera no está en la lista.
    iniciar_sesion(client, tesorera)

    respuesta = client.get('/admin/', follow_redirects=False)

    assert respuesta.status_code == 302
    assert respuesta.headers['Location'] == '/aportante/'


def test_vista_de_admin_deja_pasar_al_rol_correcto(app, client, admin, iniciar_sesion):
    iniciar_sesion(client, admin)

    respuesta = client.get('/admin/', follow_redirects=False)

    assert respuesta.status_code == 200
