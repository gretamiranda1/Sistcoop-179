from datetime import date

from app.extensions import db
from app.modelos.solicitudes import SolicitudFondo
from app.servicios import solicitudes as servicio_solicitudes
from app.servicios.solicitudes import ErrorDeResolucion


def _crear_solicitud(db):
    solicitud = SolicitudFondo(
        codigo_seguimiento='SF-TESTQA01',
        responsable='Profe Test', contacto='profe@test.com',
        tipo='fondos', concepto='Insumos de taller',
        importe_estimado=15000, fecha_estimada=date.today(),
        justificacion='Se necesitan materiales para el taller de fin de año.',
    )
    db.session.add(solicitud)
    db.session.commit()
    return solicitud


def test_aprobar_solicitud_completa_la_resolucion(db, admin):
    solicitud = _crear_solicitud(db)

    servicio_solicitudes.aprobar_solicitud(solicitud.id, admin.id, comentario='Dale para adelante')

    assert solicitud.estado == 'aprobada'
    assert solicitud.resolucion == 'Dale para adelante'
    assert solicitud.resuelta_por_id == admin.id
    assert solicitud.fecha_resolucion is not None


def test_rechazar_solicitud_exige_motivo(db, admin):
    solicitud = _crear_solicitud(db)

    try:
        servicio_solicitudes.rechazar_solicitud(solicitud.id, admin.id, '')
        assert False, 'tenía que rechazar sin motivo'
    except ErrorDeResolucion:
        pass

    assert solicitud.estado == 'pendiente'


def test_no_se_puede_resolver_dos_veces(db, admin):
    solicitud = _crear_solicitud(db)
    servicio_solicitudes.aprobar_solicitud(solicitud.id, admin.id)

    try:
        servicio_solicitudes.rechazar_solicitud(solicitud.id, admin.id, 'motivo')
        assert False, 'tenía que rechazar por ya resuelta'
    except ErrorDeResolucion:
        pass


def test_panel_muestra_botones_de_accion(client, db, admin, iniciar_sesion):
    _crear_solicitud(db)
    iniciar_sesion(client, admin)

    resp = client.get('/admin/')

    assert resp.status_code == 200
    assert 'aprobar-solicitud-' in resp.get_data(as_text=True)
