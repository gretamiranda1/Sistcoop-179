import pytest

from app.servicios import solicitudes as servicio_solicitudes
from app.servicios.pagos import ErrorDeCarga

import pytest

from app.servicios import solicitudes as servicio_solicitudes
from app.servicios.pagos import ErrorDeCarga

from sqlalchemy.exc import IntegrityError

from app.modelos.solicitudes import SolicitudFondo


def test_solicitud_sin_carrera_no_se_registra(db):
    data = {
        'responsable': 'Juan Pérez',
        'contacto': 'juan@example.com',
        'carrera_id': None,
        'curso': None,
        'tipo': 'evento',
        'concepto': 'Fiesta de fin de año',
        'importe_estimado': 5000,
        'fecha_estimada': None,
        'justificacion': 'Se necesita financiar el evento de cierre de año.',
    }

    with pytest.raises(ErrorDeCarga):
        servicio_solicitudes.crear_solicitud_fondos(data)


def test_carrera_id_es_obligatorio_a_nivel_de_base(db):
    pedido = SolicitudFondo(
        codigo_seguimiento='SF00000002',
        responsable='Responsable',
        contacto='contacto@test.com',
        carrera_id=None,
        tipo='evento',
        concepto='Concepto de prueba',
        justificacion='Justificación de prueba con más de veinte caracteres.',
    )
    db.session.add(pedido)

    with pytest.raises(IntegrityError):
        db.session.commit()