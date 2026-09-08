"""Paginación de listados grandes (issue #3).

Cubre los dos frentes que tocó el fix: el panel de administración
(Pago.get_pendientes / PagoGrupal.get_pendientes) y el portal público de
seguimiento por DNI, que ahora busca por GET para poder paginar.
"""
from datetime import date

from app.modelos.aportantes import Aportante
from app.modelos.pagos import Pago, generar_codigo
from app.modelos.usuarios import Usuario


def _crear_aportante_con_pagos(db, fondo_capital, cantidad, dni='30111222'):
    aportante = Aportante(nombre='Persona', apellido='De Prueba', dni=dni)
    db.session.add(aportante)
    db.session.commit()

    for i in range(cantidad):
        pago = Pago(
            codigo_seguimiento=generar_codigo(),
            tipo='adicional',
            importe=1000 + i,
            fecha=date.today(),
            codigo_transaccion='OP-{}-{:04d}'.format(dni, i),
            estado='pendiente',
            aportante_id=aportante.id,
            fondo_id=fondo_capital.id,
        )
        db.session.add(pago)
    db.session.commit()
    return aportante


# ============================================
# Portal público: buscar por DNI
# ============================================

def test_buscar_por_dni_pagina_1_por_get(client, db, fondo_capital):
    _crear_aportante_con_pagos(db, fondo_capital, 25)

    resp = client.get('/aportante/seguimiento?dni=30111222')

    assert resp.status_code == 200
    texto = resp.get_data(as_text=True)
    assert 'Página 1 de 2' in texto
    assert 'Siguiente' in texto
    assert 'Anterior' not in texto


def test_buscar_por_dni_pagina_2_via_link_de_siguiente(client, db, fondo_capital):
    _crear_aportante_con_pagos(db, fondo_capital, 25)

    resp = client.get('/aportante/seguimiento?dni=30111222&pagina=2')

    assert resp.status_code == 200
    texto = resp.get_data(as_text=True)
    assert 'Página 2 de 2' in texto
    assert 'Anterior' in texto
    assert 'Siguiente' not in texto


def test_buscar_por_dni_con_pocos_pagos_no_muestra_paginado(client, db, fondo_capital):
    _crear_aportante_con_pagos(db, fondo_capital, 3)

    resp = client.get('/aportante/seguimiento?dni=30111222')

    assert resp.status_code == 200
    texto = resp.get_data(as_text=True)
    assert 'Página' not in texto


def test_buscar_por_codigo_sigue_funcionando_por_post(client, db, fondo_capital):
    aportante = _crear_aportante_con_pagos(db, fondo_capital, 1, dni='30111333')
    pago = Pago.query.filter_by(aportante_id=aportante.id).first()

    resp = client.post('/aportante/seguimiento', data={
        'modo': 'codigo', 'codigo': pago.codigo_seguimiento,
    })

    assert resp.status_code == 200
    assert pago.codigo_seguimiento in resp.get_data(as_text=True)


def test_buscar_por_codigo_tambien_lista_los_demas_pagos_del_aportante(client, db, fondo_capital):
    aportante = _crear_aportante_con_pagos(db, fondo_capital, 3, dni='30111444')
    pagos = Pago.query.filter_by(aportante_id=aportante.id).all()

    resp = client.post('/aportante/seguimiento', data={
        'modo': 'codigo', 'codigo': pagos[0].codigo_seguimiento,
    })

    texto = resp.get_data(as_text=True)
    for pago in pagos:
        assert pago.codigo_seguimiento in texto


# ============================================
# Panel de administración
# ============================================

def test_panel_admin_renderiza_con_pendientes_paginados(client, db, admin, fondo_capital, iniciar_sesion):
    _crear_aportante_con_pagos(db, fondo_capital, 25)
    iniciar_sesion(client, admin)

    resp = client.get('/admin/')

    assert resp.status_code == 200
    texto = resp.get_data(as_text=True)
    assert 'Página 1 de 2' in texto


def test_panel_admin_pagina_fuera_de_rango_no_rompe(client, db, admin, iniciar_sesion):
    iniciar_sesion(client, admin)

    resp = client.get('/admin/?pagina_pendientes=99&pagina_grupales=99')

    assert resp.status_code == 20