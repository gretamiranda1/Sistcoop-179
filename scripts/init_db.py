"""Crea las tablas y carga los datos mínimos para que el sistema funcione.

El usuario administrador se crea con una contraseña al azar que se muestra
una sola vez por consola. No dejamos credenciales fijas escritas en el
repositorio.

Uso:
    python scripts/init_db.py
    python scripts/init_db.py --usuario presidencia --cuota 35000
"""

import os
import sys
import string
import secrets
import argparse
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.modelos.usuarios import Usuario
from app.modelos.carreras import Carrera
from app.modelos.ejercicios import Ejercicio
from app.modelos.fondos import Fondo
from app.data.carreras import CARRERAS


def generar_contrasena(largo=16):
    """Contraseña al azar, sin los caracteres que se confunden al copiarla"""
    letras = string.ascii_letters + string.digits
    for confuso in 'lI1O0':
        letras = letras.replace(confuso, '')

    contrasena = ''
    for i in range(largo):
        contrasena = contrasena + secrets.choice(letras)
    return contrasena


def inicializar(usuario, email, cuota):
    app = create_app('development')

    with app.app_context():
        db.create_all()
        print('Tablas creadas (o ya estaban).')

        # --- usuario administrador ---
        contrasena = None
        if not Usuario.query.filter_by(username=usuario).first():
            contrasena = generar_contrasena()

            admin = Usuario(
                username=usuario,
                email=email,
                nombre='Administración',
                apellido='Cooperadora',
                rol='admin',
                activo=True
            )
            admin.set_password(contrasena)
            db.session.add(admin)
            print('Usuario administrador creado: ' + usuario)
        else:
            print('El usuario "{}" ya existe, no lo tocamos.'.format(usuario))

        # --- carreras ---
        nuevas = 0
        for nombre in CARRERAS:
            if not Carrera.query.filter_by(nombre=nombre).first():
                db.session.add(Carrera(nombre=nombre))
                nuevas = nuevas + 1
        # flush() manda los INSERT a la base y les asigna el id a las filas,
        # pero todavía no confirma nada: eso lo hace el commit del final.
        db.session.flush()
        print('Carreras: {} nuevas, {} en total.'.format(nuevas, len(CARRERAS)))

        # --- ejercicio del año ---
        anio = date.today().year
        if not Ejercicio.query.filter_by(anio=anio).first():
            db.session.add(Ejercicio(anio=anio, cuota=cuota, activo=True, cerrado=False))
            print('Ejercicio {} abierto con una cuota de ${:,.2f}.'.format(anio, cuota))
        else:
            print('El ejercicio {} ya existe, no lo tocamos.'.format(anio))

        # --- fondos ---
        # El fondo arranca en cero. Si le pusiéramos un saldo inicial
        # inventado, el libro banco no coincidiría con la suma de los
        # movimientos, que es justamente lo que hay que poder auditar.
        if not Fondo.query.filter_by(tipo='capital').first():
            db.session.add(Fondo(nombre='Fondo general de la Cooperadora',
                                 tipo='capital', saldo=0))
            print('Fondo general creado, con saldo inicial en cero.')

        db.session.flush()

        nuevos_fondos = 0
        for carrera in Carrera.query.all():
            existe = Fondo.query.filter_by(carrera_id=carrera.id, tipo='carrera').first()
            if not existe:
                db.session.add(Fondo(nombre='Fondo ' + carrera.nombre,
                                     tipo='carrera', carrera_id=carrera.id, saldo=0))
                nuevos_fondos = nuevos_fondos + 1
        print('Fondos por carrera creados: {}.'.format(nuevos_fondos))

        db.session.commit()

        print('\n' + '=' * 62)
        print('BASE DE DATOS LISTA')
        print('=' * 62)

        if contrasena:
            print('\nDatos de acceso (se muestran UNA sola vez):')
            print('   Usuario:    ' + usuario)
            print('   Contraseña: ' + contrasena)
            print('\nAnotalos ahora y cambiá la contraseña antes de cargar')
            print('cualquier dato real de la Cooperadora.')

        print('\nPara levantar el servidor:  python run.py')
        print('=' * 62)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inicializa la base de SistCoop 179')
    parser.add_argument('--usuario', default='cooperadora')
    parser.add_argument('--email', default='cooperadora@isft179.local')
    parser.add_argument('--cuota', type=float, default=30000)
    args = parser.parse_args()

    inicializar(args.usuario, args.email, args.cuota)
