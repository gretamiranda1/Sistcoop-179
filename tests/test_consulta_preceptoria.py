"""Consulta de sólo lectura para Preceptoría (issue #23, RF-13)."""
from app.extensions import db
from app.modelos.usuarios import Usuario


def _crear_preceptoria(db):
    usuario = Usuario(username='preceptoria_test', email='preceptoria_test@isft179.local',
                      nombre='Preceptoria', apellido='Test', rol='preceptoria', activo=True)
    usuario.set_password('clave-de-prueba-1234')
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_preceptoria_puede_ver_la_consulta_de_solo_lectura(client, db, iniciar_sesion):
    preceptoria = _crear_preceptoria(db)
    iniciar_sesion(client, preceptoria)

    resp = client.get('/admin/consulta-preceptoria')

    assert resp.status_code == 200
    assert 'Registrar la entrega' not in resp.get_data(as_text=True)


def test_preceptoria_ya_no_entra_a_libretas(client, db, iniciar_sesion):
    preceptoria = _crear_preceptoria(db)
    iniciar_sesion(client, preceptoria)

    resp = client.get('/admin/libretas', follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/aportante/'


def test_preceptoria_no_puede_entregar_libreta(client, db, iniciar_sesion):
    preceptoria = _crear_preceptoria(db)
    iniciar_sesion(client, preceptoria)

    resp = client.post('/admin/libretas/1/entregar', follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/aportante/'
