"""Pone al día una base de datos creada con una versión anterior del sistema.

Hace cuatro cosas, sin borrar nada de lo que ya está:

  1. agrega las columnas y las tablas que le falten a la base;
  2. les pone código de seguimiento a los pagos que no tengan;
  3. imputa los pagos de cuota viejos al ejercicio vigente;
  4. recalcula los saldos desde los pagos verificados.

El paso 4 hace falta porque la versión anterior acreditaba el dinero apenas
se cargaba el comprobante, sin esperar la verificación de la Cooperadora, así
que los saldos que quedaron en la base están inflados.

No hay una lista escrita a mano de qué columnas agregar: el script compara
los modelos con lo que hay en la base. Así, cuando en el Incremento 3
agreguemos una columna nueva, este mismo script ya la va a saber agregar.

Se puede correr las veces que haga falta.

Uso:
    python scripts/migrar_incremento2.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.modelos.pagos import Pago, TIPOS_DE_CUOTA, generar_codigo
from app.modelos.pagos_grupales import PagoGrupal
from app.modelos.ejercicios import Ejercicio
from app.modelos.fondos import Fondo
from app.modelos.saldos import SaldoAportante
from app.servicios.fondos import registrar_movimiento
from app.servicios.saldos import recalcular_saldo


# ============================================
# 1. ESTRUCTURA DE LA BASE
# ============================================

def valor_por_defecto(columna):
    """El valor por defecto que el modelo le da a una columna.

    Sirve para que las filas que ya estaban no queden en NULL. Devuelve None
    si la columna no tiene valor por defecto, o si lo calcula una función
    (como datetime.utcnow), que no se puede escribir en un UPDATE.
    """
    if columna.default is None:
        return None
    if not columna.default.is_scalar:
        return None

    valor = columna.default.arg
    if isinstance(valor, bool):
        return 1 if valor else 0
    return valor


def agregar_columnas():
    """Agrega las columnas que el modelo tiene y la tabla de la base no.

    Las columnas se agregan sin restricciones: SQLite no deja agregar una
    columna NOT NULL ni UNIQUE a una tabla que ya tiene filas. Los índices
    únicos se crean aparte, en crear_indices().
    """
    inspector = inspect(db.engine)
    tablas_de_la_base = inspector.get_table_names()
    agregadas = 0

    for tabla in db.metadata.sorted_tables:
        if tabla.name not in tablas_de_la_base:
            print('   la tabla {} todavía no existe, la crea db.create_all()'.format(
                tabla.name))
            continue

        nombres_en_la_base = []
        for columna in inspector.get_columns(tabla.name):
            nombres_en_la_base.append(columna['name'])

        for columna in tabla.columns:
            if columna.name in nombres_en_la_base:
                continue

            tipo = columna.type.compile(db.engine.dialect)
            db.session.execute(text('ALTER TABLE {} ADD COLUMN {} {}'.format(
                tabla.name, columna.name, tipo)))
            print('   + {}.{}'.format(tabla.name, columna.name))
            agregadas = agregadas + 1

            relleno = valor_por_defecto(columna)
            if relleno is not None:
                db.session.execute(
                    text('UPDATE {} SET {} = :valor WHERE {} IS NULL'.format(
                        tabla.name, columna.name, columna.name)),
                    {'valor': relleno}
                )

    db.session.commit()
    return agregadas


def crear_indices():
    """Crea los índices que el modelo define y la base todavía no tiene.

    Es lo que devuelve el control de duplicados: sin el índice único sobre
    codigo_seguimiento, la base dejaría repetir un código.
    """
    inspector = inspect(db.engine)
    tablas_de_la_base = inspector.get_table_names()
    creados = 0

    for tabla in db.metadata.sorted_tables:
        if tabla.name not in tablas_de_la_base:
            continue

        nombres_en_la_base = []
        for indice in inspector.get_indexes(tabla.name):
            nombres_en_la_base.append(indice['name'])

        for indice in tabla.indexes:
            if indice.name in nombres_en_la_base:
                continue
            try:
                with db.engine.begin() as conexion:
                    indice.create(bind=conexion)
                print('   + índice {}'.format(indice.name))
                creados = creados + 1
            except Exception as error:
                # Si no se puede crear (por ejemplo, porque hay valores
                # repetidos de antes) avisamos y seguimos: el sistema
                # funciona igual, sólo queda un control menos en la base.
                print('   no se pudo crear el índice {}: {}'.format(indice.name, error))

    return creados


# ============================================
# 2. DATOS QUE HAY QUE COMPLETAR
# ============================================

def poner_codigos():
    """Les pone código de seguimiento a los registros que no lo tengan."""
    total = 0

    for modelo, prefijo in ((Pago, 'SC'), (PagoGrupal, 'SG')):
        sin_codigo = modelo.query.filter(
            (modelo.codigo_seguimiento.is_(None)) | (modelo.codigo_seguimiento == '')
        ).all()

        for registro in sin_codigo:
            codigo = generar_codigo(prefijo)
            # Muy poco probable, pero por las dudas nos aseguramos de que
            # no se repita
            while modelo.query.filter_by(codigo_seguimiento=codigo).first():
                codigo = generar_codigo(prefijo)

            registro.codigo_seguimiento = codigo
            total = total + 1

    db.session.commit()
    return total


def imputar_ejercicio():
    """Vincula los pagos de cuota viejos con el ejercicio vigente.

    Sin ejercicio_id no se puede recalcular el saldo, porque no hay forma de
    saber a qué año corresponde el pago.
    """
    ejercicio = Ejercicio.get_ejercicio_vigente()
    if not ejercicio:
        print('   no hay ejercicio vigente, se saltea este paso')
        return 0

    sin_ejercicio = Pago.query.filter(
        Pago.ejercicio_id.is_(None),
        Pago.tipo.in_(TIPOS_DE_CUOTA)
    ).all()

    for pago in sin_ejercicio:
        pago.ejercicio_id = ejercicio.id

    db.session.commit()
    return len(sin_ejercicio)


# ============================================
# 3. SALDOS
# ============================================

def recalcular_saldos():
    """Vuelve a calcular el saldo de cada persona desde sus pagos verificados."""
    saldos = SaldoAportante.query.all()
    for saldo in saldos:
        recalcular_saldo(saldo)

    db.session.commit()
    return len(saldos)


def recalcular_fondos():
    """Vuelve a calcular el saldo de cada fondo desde los pagos verificados.

    Mismo problema que con los saldos de las personas: la versión anterior le
    sumaba al fondo apenas se cargaba el comprobante, así que el saldo que hay
    en la base es más alto que la plata que realmente entró.

    Como hasta el Incremento 2 lo único que mueve un fondo son los pagos, el
    saldo correcto es la suma de los pagos verificados. La diferencia se
    asienta como un movimiento más, para no dejar un saldo que no se pueda
    explicar mirando el libro.

    Se puede correr de nuevo sin problema: la segunda vez la diferencia da
    cero y no se asienta nada.
    """
    corregidos = 0

    for fondo in Fondo.query.all():
        pagos = Pago.query.filter_by(fondo_id=fondo.id, estado='verificado').all()

        correcto = 0
        for pago in pagos:
            correcto = correcto + float(pago.importe)

        diferencia = round(correcto - float(fondo.saldo or 0), 2)
        if diferencia == 0:
            continue

        registrar_movimiento(
            fondo,
            monto=diferencia,
            motivo='Ajuste de la migración al Incremento 2'
        )
        print('   {}: ${:,.2f} -> ${:,.2f}'.format(
            fondo.nombre, correcto - diferencia, correcto))
        corregidos = corregidos + 1

    db.session.commit()
    return corregidos


# ============================================

def migrar():
    app = create_app('development')

    with app.app_context():
        print('1. Creando las tablas que falten')
        db.create_all()
        print('   listo\n')

        print('2. Agregando las columnas que falten')
        print('   {} columna(s) agregada(s)\n'.format(agregar_columnas()))

        print('3. Creando los índices que falten')
        print('   {} índice(s) creado(s)\n'.format(crear_indices()))

        print('4. Poniendo códigos de seguimiento')
        print('   {} registro(s) actualizado(s)\n'.format(poner_codigos()))

        print('5. Imputando los pagos de cuota al ejercicio vigente')
        print('   {} pago(s)\n'.format(imputar_ejercicio()))

        print('6. Recalculando los saldos de las personas')
        print('   {} saldo(s)\n'.format(recalcular_saldos()))

        print('7. Recalculando los saldos de los fondos')
        print('   {} fondo(s) corregido(s)\n'.format(recalcular_fondos()))

        print('=' * 62)
        print('MIGRACIÓN TERMINADA')
        print('=' * 62)
        print('\nRevisá el panel: los saldos ahora reflejan sólo lo verificado,')
        print('tanto los de las personas como los de los fondos.')
        print('\nOJO: los comprobantes que estaban en app/static/uploads/comprobantes')
        print('hay que moverlos a mano a instance/comprobantes. Ya no se sirven')
        print('desde una carpeta pública.')


if __name__ == '__main__':
    migrar()
