"""Fixtures compartidas por todos los tests.

Cada test corre contra una base SQLite en memoria (TestingConfig), nueva y
vacía: `db.create_all()` antes del test y `db.drop_all()` después, así
ningún test depende de datos que dejó otro.
"""
import os
from datetime import date

import pytest

os.environ.setdefault('SECRET_KEY', 'clave-de-pruebas')

from app import create_app
from app.extensions import db as _db
from app.modelos.carreras import Carrera
from app.modelos.ejercicios import Ejercicio
from app.modelos.fondos import Fondo
from app.modelos.usuarios import Usuario

CUOTA = 30000.0


@pytest.fixture
def app():
    """La aplicación, en TestingConfig (SQLite en memoria, CSRF apagado)."""
    application = create_app('testing')

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Alias corto: los tests usan `db.session` para armar sus datos."""
    return _db


@pytest.fixture
def carrera(db):
    registro = Carrera(nombre='Análisis de Sistemas')
    db.session.add(registro)
    db.session.commit()
    return registro


@pytest.fixture
def ejercicio(db):
    registro = Ejercicio(anio=date.today().year, cuota=CUOTA, activo=True, cerrado=False)
    db.session.add(registro)
    db.session.commit()
    return registro


@pytest.fixture
def fondo_capital(db):
    registro = Fondo(nombre='Fondo general de la Cooperadora', tipo='capital', saldo=0)
    db.session.add(registro)
    db.session.commit()
    return registro


@pytest.fixture
def fondo_carrera(db, carrera):
    registro = Fondo(nombre='Fondo ' + carrera.nombre, tipo='carrera',
                     carrera_id=carrera.id, saldo=0)
    db.session.add(registro)
    db.session.commit()
    return registro


def _crear_usuario(db, username, rol):
    usuario = Usuario(username=username, email=username + '@isft179.local',
                      nombre=username.capitalize(), apellido='Test',
                      rol=rol, activo=True)
    usuario.set_password('clave-de-prueba-1234')
    db.session.add(usuario)
    db.session.commit()
    return usuario


@pytest.fixture
def admin(db):
    return _crear_usuario(db, 'admin_test', 'admin')


@pytest.fixture
def tesorera(db):
    return _crear_usuario(db, 'tesorera_test', 'tesorera')


@pytest.fixture
def iniciar_sesion():
    """Loguea a un usuario en un client sin pasar por la pantalla de login."""
    def _iniciar(client, usuario):
        with client.session_transaction() as sesion:
            sesion['_user_id'] = str(usuario.id)
            sesion['_fresh'] = True
    return _iniciar


@pytest.fixture
def datos_de_cuota(carrera):
    """Un formulario de cuota ya completado, listo para el servicio."""
    def _fabrica(dni, importe, codigo_transaccion, huella, **extra):
        datos = {
            'nombre': 'Persona',
            'apellido': 'De Prueba',
            'dni': dni,
            'importe': importe,
            'fecha': date.today().isoformat(),
            'codigo_transaccion': codigo_transaccion,
            'hash_comprobante': huella,
            'comprobante_nombre': 'comprobante-' + huella + '.png',
            'carrera_id': carrera.id,
            'anio': '1',
        }
        datos.update(extra)
        return datos
    return _fabrica