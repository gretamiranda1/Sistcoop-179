"""Restricciones de unicidad de fondos y ejercicios (índices únicos parciales).

Un solo fondo de capital activo, un solo fondo por carrera y un solo
ejercicio vigente: la base los rechaza, no sólo el código de la aplicación.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.modelos.ejercicios import Ejercicio
from app.modelos.fondos import Fondo
from app.servicios import ejercicios as servicio_ejercicios


def test_un_solo_fondo_de_capital_activo(db, fondo_capital):
    db.session.add(Fondo(nombre='Otro capital', tipo='capital', activo=True, saldo=0))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_fondo_de_capital_inactivo_no_choca(db, fondo_capital):
    db.session.add(Fondo(nombre='Capital viejo', tipo='capital', activo=False, saldo=0))
    db.session.flush()  # no debe tirar


def test_un_solo_fondo_por_carrera(db, carrera, fondo_carrera):
    db.session.add(Fondo(nombre='Otro de la misma carrera', tipo='carrera',
                         carrera_id=carrera.id, activo=True, saldo=0))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_un_solo_ejercicio_vigente(db, ejercicio):
    db.session.add(Ejercicio(anio=1999, cuota=1000, activo=True, cerrado=False))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_ejercicio_cerrado_no_choca(db, ejercicio):
    db.session.add(Ejercicio(anio=1998, cuota=1000, activo=False, cerrado=True))
    db.session.flush()  # no debe tirar


def test_abrir_ejercicio_cierra_el_anterior_y_no_choca_con_el_indice(db, ejercicio):
    nuevo, anterior = servicio_ejercicios.abrir_ejercicio(ejercicio.anio + 1, 40000)

    assert anterior.id == ejercicio.id
    assert anterior.cerrado is True
    assert anterior.activo is False
    assert nuevo.activo is True
    assert nuevo.cerrado is False

    vigentes = Ejercicio.query.filter_by(activo=True, cerrado=False).count()
    assert vigentes == 1
