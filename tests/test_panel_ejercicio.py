"""Selector de ejercicio contable en el panel (issue #65)."""
from datetime import date

from app.extensions import db
from app.modelos.aportantes import Aportante
from app.modelos.ejercicios import Ejercicio
from app.modelos.pagos import Pago, generar_codigo


def _crear_pago_de_ejercicio(fondo_capital, ejercicio, dni, codigo):
    aportante = Aportante(nombre='Persona', apellido='De Prueba', dni=dni)
    db.session.add(aportante)
    db.session.flush()

    pago = Pago(
        codigo_seguimiento=generar_codigo(),
        tipo='cuota',
        importe=15000,
        fecha=date.today(),
        codigo_transaccion=codigo,
        estado='pendiente',
        aportante_id=aportante.id,
        fondo_id=fondo_capital.id,
        ejercicio_id=ejercicio.id,
    )
    db.session.add(pago)
    db.session.commit()
    return pago


def test_panel_preselecciona_el_ejercicio_vigente(client, db, admin, ejercicio, fondo_capital, iniciar_sesion):
    iniciar_sesion(client, admin)

    resp = client.get('/admin/')

    assert resp.status_code == 200
    assert 'selected' in resp.get_data(as_text=True)


def test_panel_filtra_pendientes_por_ejercicio_seleccionado(
        client, db, admin, ejercicio, fondo_capital, iniciar_sesion):
    ejercicio_viejo = Ejercicio(anio=ejercicio.anio - 1, cuota=20000, activo=False, cerrado=True)
    db.session.add(ejercicio_viejo)
    db.session.commit()

    pago_viejo = _crear_pago_de_ejercicio(fondo_capital, ejercicio_viejo, '50111111', 'OPVIEJOQA')
    pago_vigente = _crear_pago_de_ejercicio(fondo_capital, ejercicio, '50222222', 'OPVIGENTEQA')

    iniciar_sesion(client, admin)

    resp_viejo = client.get('/admin/?ejercicio_id={}'.format(ejercicio_viejo.id))
    texto_viejo = resp_viejo.get_data(as_text=True)
    assert pago_viejo.codigo_seguimiento in texto_viejo
    assert pago_vigente.codigo_seguimiento not in texto_viejo

    resp_todos = client.get('/admin/?ejercicio_id=0')
    texto_todos = resp_todos.get_data(as_text=True)
    assert pago_viejo.codigo_seguimiento in texto_todos
    assert pago_vigente.codigo_seguimiento in texto_todos