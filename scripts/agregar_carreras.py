"""Sincronizar las carreras del instituto y sus fondos.

Agrega las carreras de seeds/carreras.py que todavía no estén en la base
y le crea el fondo propio a cada una. No borra ni desactiva nada.

Uso:
    python scripts/agregar_carreras.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                    # noqa: E402
from app.extensions import db                 # noqa: E402
from app.modelos.carreras import Carrera      # noqa: E402
from app.modelos.fondos import Fondo          # noqa: E402
from seeds.carreras import CARRERAS           # noqa: E402


def sincronizar():
    app = create_app('development')
    with app.app_context():
        nuevas = 0
        for nombre in CARRERAS:
            if not Carrera.query.filter_by(nombre=nombre).first():
                db.session.add(Carrera(nombre=nombre))
                print('  + carrera: ' + nombre)
                nuevas = nuevas + 1
        # flush() manda los INSERT a la base y les asigna el id a las filas,
        # pero todavía no confirma nada: eso lo hace el commit del final.
        db.session.flush()

        fondos = 0
        for carrera in Carrera.query.all():
            if not Fondo.query.filter_by(carrera_id=carrera.id, tipo='carrera').first():
                db.session.add(Fondo(nombre='Fondo ' + carrera.nombre,
                                     tipo='carrera', carrera_id=carrera.id, saldo=0))
                print('  + fondo: ' + carrera.nombre)
                fondos = fondos + 1

        db.session.commit()
        print('\n{} carrera(s) y {} fondo(s) agregados.'.format(nuevas, fondos))


if __name__ == '__main__':
    sincronizar()
