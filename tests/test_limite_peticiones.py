from app.modelos.limitador import ConsultaLimitada
from app.utilidades import limite_peticiones


def test_excede_limite_guarda_el_conteo_en_la_base(app, db):
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '190.1.2.3'}):
        for _ in range(3):
            limite_peticiones.excede_limite('prueba', limite=10, ventana=60)

    cantidad = ConsultaLimitada.query.filter_by(clave='prueba:190.1.2.3').count()
    assert cantidad == 3


def test_excede_limite_bloquea_al_llegar_al_limite(app, db):
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '190.1.2.4'}):
        for _ in range(3):
            bloqueado = limite_peticiones.excede_limite('prueba', limite=3, ventana=60)
        assert bloqueado is False

        bloqueado = limite_peticiones.excede_limite('prueba', limite=3, ventana=60)
        assert bloqueado is True