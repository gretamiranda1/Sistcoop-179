"""Borra los datos de prueba y deja la configuración base.

Elimina pagos, pagos grupales, aportantes, saldos, solicitudes, movimientos y
auditoría, deja los fondos en cero y borra los comprobantes que se hayan
subido.

Conserva usuarios, carreras y ejercicios, así que después de correrlo se
puede entrar con la misma contraseña de siempre y seguir probando.

Nunca correrlo sobre datos reales de la Cooperadora.

Uso:
    python scripts/limpiar_datos.py --confirmar
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                                       # noqa: E402
from app.extensions import db                                    # noqa: E402
from app.modelos.aportantes import Aportante                     # noqa: E402
from app.modelos.auditoria import Auditoria                      # noqa: E402
from app.modelos.fondos import Fondo, MovimientoFondo            # noqa: E402
from app.modelos.pagos import Pago                               # noqa: E402
from app.modelos.pagos_grupales import (PagoGrupal,              # noqa: E402
                                        PagoGrupalDetalle)
from app.modelos.saldos import SaldoAportante                    # noqa: E402
from app.modelos.solicitudes import SolicitudFondo               # noqa: E402

# El orden importa: primero las tablas que apuntan a otras, después las
# apuntadas. Si borráramos al revés, quedarían filas señalando a un id que
# ya no existe.
EN_ORDEN = [
    PagoGrupalDetalle, Pago, PagoGrupal, SaldoAportante,
    SolicitudFondo, MovimientoFondo, Auditoria, Aportante,
]


def borrar_comprobantes(carpeta):
    """Borra los archivos de comprobante que quedaron en instance/.

    Si no los borráramos, la carpeta seguiría llena de imágenes de pagos que
    ya no existen en la base, y encima el control de comprobante repetido
    volvería a aceptarlos, porque ese control mira la base y no el disco.
    """
    if not os.path.isdir(carpeta):
        return 0

    borrados = 0
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        if os.path.isfile(ruta):
            os.remove(ruta)
            borrados = borrados + 1
    return borrados


def limpiar():
    app = create_app('development')

    with app.app_context():
        for modelo in EN_ORDEN:
            borrados = modelo.query.delete()
            print('  {:<24} {} registro(s)'.format(modelo.__tablename__, borrados))

        for fondo in Fondo.query.all():
            fondo.saldo = 0
        print('  {:<24} saldos vueltos a cero'.format('fondos'))

        db.session.commit()

        archivos = borrar_comprobantes(app.config['UPLOAD_FOLDER'])
        print('  {:<24} {} archivo(s)'.format('comprobantes', archivos))

        print('\n' + '=' * 62)
        print('BASE LIMPIA')
        print('=' * 62)
        print('\nQuedaron los usuarios, las carreras y el ejercicio, así que')
        print('podés entrar con la misma contraseña y seguir probando.')
        print('\nPara levantar el servidor:  python run.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirmar', action='store_true',
                        help='requerido: confirma que querés borrar los datos')
    args = parser.parse_args()

    if not args.confirmar:
        print('Este script borra TODOS los pagos, aportantes y comprobantes.')
        print('Si estás seguro, volvé a correrlo con --confirmar')
        sys.exit(1)

    limpiar()
