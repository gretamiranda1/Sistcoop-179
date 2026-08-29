"""Prueba del circuito de pagos sobre una base en memoria.

Recorre lo que no se puede romper nunca:

  1. cargar un comprobante NO acredita plata;
  2. verificar SÍ acredita, en el fondo y en el saldo;
  3. rechazar un pago verificado devuelve todo a como estaba;
  4. el mismo comprobante no se puede cargar dos veces;
  5. un pago grupal se reparte y acredita a cada persona.

No prueba las pantallas: eso se controla a mano con la lista de
docs/PRUEBAS-MANUALES.md.

Uso:
    python scripts/prueba_flujo.py
"""

import os
import sys
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                                   # noqa: E402
from app.extensions import db                                # noqa: E402
from app.modelos.carreras import Carrera                     # noqa: E402
from app.modelos.ejercicios import Ejercicio                 # noqa: E402
from app.modelos.fondos import Fondo                         # noqa: E402
from app.modelos.pagos import Pago                           # noqa: E402
from app.modelos.usuarios import Usuario                     # noqa: E402
from app.servicios import pagos as servicio_pagos            # noqa: E402
from app.servicios import pagos_grupales as servicio_grupales  # noqa: E402
from app.servicios.pagos import ErrorDeCarga                 # noqa: E402

CUOTA = 30000.0

bien = 0
mal = 0


def comprobar(descripcion, condicion):
    """Anota si el control dio bien o mal y lo muestra por consola."""
    global bien, mal
    if condicion:
        bien = bien + 1
        print('   OK   ' + descripcion)
    else:
        mal = mal + 1
        print('   MAL  ' + descripcion)


def preparar_base():
    """Deja la base con lo mínimo: una carrera, un ejercicio, los fondos y un admin."""
    db.create_all()

    carrera = Carrera(nombre='Análisis de Sistemas')
    db.session.add(carrera)

    ejercicio = Ejercicio(anio=date.today().year, cuota=CUOTA, activo=True, cerrado=False)
    db.session.add(ejercicio)

    admin = Usuario(username='prueba', email='prueba@isft179.local',
                    nombre='Prueba', apellido='Automática', rol='admin', activo=True)
    admin.set_password('prueba-1234')
    db.session.add(admin)
    # flush() les asigna el id a las filas para poder usarlo abajo
    db.session.flush()

    db.session.add(Fondo(nombre='Fondo general', tipo='capital', saldo=0))
    db.session.add(Fondo(nombre='Fondo ' + carrera.nombre, tipo='carrera',
                         carrera_id=carrera.id, saldo=0))
    db.session.commit()

    return admin.id


def datos_de_cuota(dni, importe, transaccion, huella):
    """Un formulario de cuota ya completado, para no repetirlo en cada prueba."""
    return {
        'nombre': 'Persona',
        'apellido': 'De Prueba ' + dni[-2:],
        'dni': dni,
        'importe': importe,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': transaccion,
        'hash_comprobante': huella,
        'comprobante_nombre': 'comprobante-' + huella + '.png',
    }


def probar_carga_y_verificacion(admin_id):
    print('\n1. Carga y verificación de un pago de cuota')

    fondo = Fondo.get_capital()
    saldo_inicial = float(fondo.saldo)

    pago, saldo = servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('31111111', 15000, 'OP-0001', 'huella-0001'))

    comprobar('el pago queda pendiente', pago.estado == 'pendiente')
    comprobar('tiene código de seguimiento', pago.codigo_seguimiento.startswith('SC-'))
    comprobar('NO se acreditó en el saldo del aportante', float(saldo.pagado) == 0)
    comprobar('figura como "en revisión"', saldo.en_revision == 15000)
    comprobar('NO se acreditó en el fondo', float(fondo.saldo) == saldo_inicial)

    servicio_pagos.verificar_pago(pago.id, admin_id, numero_recibo='0001')

    comprobar('después de verificar, el pago queda verificado',
              pago.estado == 'verificado')
    comprobar('el saldo del aportante suma', float(saldo.pagado) == 15000)
    comprobar('ya no figura en revisión', saldo.en_revision == 0)
    comprobar('el fondo suma', float(fondo.saldo) == saldo_inicial + 15000)
    comprobar('queda el movimiento del fondo', fondo.movimientos.count() == 1)
    comprobar('el saldo pendiente baja', float(saldo.saldo_pendiente) == CUOTA - 15000)

    return pago, saldo, fondo


def probar_rechazo(admin_id, pago, saldo, fondo):
    print('\n2. Rechazo de un pago ya verificado')

    saldo_antes = float(fondo.saldo)
    servicio_pagos.rechazar_pago(pago.id, admin_id, 'No figura en el extracto')

    comprobar('el pago queda rechazado', pago.estado == 'rechazado')
    comprobar('guarda el motivo', pago.motivo_rechazo == 'No figura en el extracto')
    comprobar('el saldo del aportante vuelve a cero', float(saldo.pagado) == 0)
    comprobar('el fondo se revierte', float(fondo.saldo) == saldo_antes - 15000)
    comprobar('la reversión queda asentada', fondo.movimientos.count() == 2)


def probar_duplicados():
    print('\n3. Controles de duplicado (RF-04)')

    servicio_pagos.crear_pago_de_cuota(
        datos_de_cuota('32222222', 30000, 'OP-0002', 'huella-0002'))

    try:
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('33222222', 30000, 'OP-0002', 'huella-0003'))
        comprobar('rechaza el número de operación repetido', False)
    except ErrorDeCarga:
        comprobar('rechaza el número de operación repetido', True)

    try:
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('34222222', 30000, 'OP-0004', 'huella-0002'))
        comprobar('rechaza el mismo comprobante subido de nuevo', False)
    except ErrorDeCarga:
        comprobar('rechaza el mismo comprobante subido de nuevo', True)

    try:
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('123', 30000, 'OP-0005', 'huella-0005'))
        comprobar('rechaza un DNI inválido', False)
    except ErrorDeCarga:
        comprobar('rechaza un DNI inválido', True)

    try:
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('35222222', -100, 'OP-0006', 'huella-0006'))
        comprobar('rechaza un importe negativo', False)
    except ErrorDeCarga:
        comprobar('rechaza un importe negativo', True)


def probar_pago_grupal(admin_id):
    print('\n4. Pago grupal')

    fondo = Fondo.get_capital()
    saldo_antes = float(fondo.saldo)

    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 40000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OP-GRUPAL-1',
        'hash_comprobante': 'huella-grupal-1',
        'comprobante_nombre': 'grupal.png',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '36111111', 'nombre': 'Ana', 'apellido': 'Gómez'},
            {'dni': '36222222', 'nombre': 'Beto', 'apellido': 'Gómez'},
        ],
    })

    comprobar('la transferencia queda pendiente', grupal.estado == 'pendiente')
    comprobar('se repartió entre las dos personas', len(resumen['asignaciones']) == 2)
    comprobar('a cada una le tocó la mitad',
              resumen['asignaciones'][0]['monto'] == 20000)
    comprobar('no hay excedente', resumen['excedente'] == 0)
    comprobar('se creó un pago por persona', grupal.pagos.count() == 2)
    comprobar('todavía no se acreditó nada', float(fondo.saldo) == saldo_antes)

    servicio_grupales.verificar_pago_grupal(grupal.id, admin_id)

    comprobar('al verificar, la transferencia queda verificada',
              grupal.estado == 'verificado')
    comprobar('el fondo suma el total transferido',
              float(fondo.saldo) == saldo_antes + 40000)

    for pago in grupal.pagos.all():
        comprobar('el pago de {} quedó verificado'.format(pago.codigo_seguimiento),
                  pago.estado == 'verificado')

    try:
        servicio_grupales.procesar_pago_grupal({
            'importe_total': 10000,
            'fecha': date.today().isoformat(),
            'codigo_transaccion': 'OP-GRUPAL-2',
            'hash_comprobante': 'huella-grupal-2',
            'tipo_distribucion': 'auto',
            'personas': [
                {'dni': '37111111', 'nombre': 'Uno', 'apellido': 'Solo'},
            ],
        })
        comprobar('rechaza un pago grupal de una sola persona', False)
    except ErrorDeCarga:
        comprobar('rechaza un pago grupal de una sola persona', True)


def probar_excedente(admin_id):
    print('\n5. Excedente de un pago grupal')

    grupal, resumen = servicio_grupales.procesar_pago_grupal({
        'importe_total': 70000,
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OP-GRUPAL-3',
        'hash_comprobante': 'huella-grupal-3',
        'tipo_distribucion': 'auto',
        'personas': [
            {'dni': '38111111', 'nombre': 'Caro', 'apellido': 'Díaz'},
            {'dni': '38222222', 'nombre': 'Dario', 'apellido': 'Díaz'},
        ],
    })

    # Cada una debe $30.000, así que se reparten $60.000 y sobran $10.000
    comprobar('a cada una se le asigna lo que debe',
              resumen['asignaciones'][0]['monto'] == CUOTA)
    comprobar('el excedente se calcula bien', resumen['excedente'] == 10000)
    comprobar('el excedente queda asentado como aporte adicional',
              grupal.pagos.filter_by(tipo='adicional').count() == 1)

    fondo = Fondo.get_capital()
    saldo_antes = float(fondo.saldo)
    servicio_grupales.verificar_pago_grupal(grupal.id, admin_id)

    comprobar('al verificar entra al fondo TODO lo transferido',
              float(fondo.saldo) == saldo_antes + 70000)


def probar_estado_de_cuota():
    print('\n6. Consulta del estado de cuota')

    estado = servicio_pagos.estado_de_cuota('38111111')
    comprobar('devuelve la cuota del ejercicio', estado['cuota_total'] == CUOTA)
    comprobar('marca a la persona como al día', estado['al_dia'] is True)
    comprobar('no devuelve datos personales', 'nombre' not in estado)

    estado = servicio_pagos.estado_de_cuota('99999999')
    comprobar('con un DNI que no existe devuelve la cuota entera',
              estado['saldo_pendiente'] == CUOTA)


def probar_rutas(app):
    print('\n7. Las pantallas responden')

    with app.test_client() as navegador:
        for direccion in ['/aportante/', '/aportante/cuota', '/aportante/adicional',
                          '/aportante/solicitud', '/aportante/seguimiento',
                          '/auth/login', '/salud']:
            respuesta = navegador.get(direccion)
            comprobar('{} responde bien'.format(direccion), respuesta.status_code == 200)

        respuesta = navegador.get('/admin/')
        comprobar('/admin/ pide iniciar sesión', respuesta.status_code == 302)


def main():
    app = create_app('testing')

    with app.app_context():
        admin_id = preparar_base()

        pago, saldo, fondo = probar_carga_y_verificacion(admin_id)
        probar_rechazo(admin_id, pago, saldo, fondo)
        probar_duplicados()
        probar_pago_grupal(admin_id)
        probar_excedente(admin_id)
        probar_estado_de_cuota()
        probar_rutas(app)

    print('\n' + '=' * 62)
    print('RESULTADO: {} bien, {} mal'.format(bien, mal))
    print('=' * 62)

    if mal > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
