"""Movimientos de los fondos de la Cooperadora.

REGLA: el saldo de un fondo se cambia SÓLO con registrar_movimiento. Si en
algún lado se hiciera `fondo.saldo = otra_cosa`, el saldo dejaría de poder
explicarse sumando los movimientos, y eso es justamente lo que audita la
Comisión Revisora de Cuentas (RF-08, RNF-04).
"""

from datetime import datetime

from app.extensions import db
from app.modelos.fondos import Fondo, MovimientoFondo


def registrar_movimiento(fondo, monto, motivo):
    """Cambia el saldo del fondo y deja el asiento del movimiento.

    `monto` va positivo cuando entra plata y negativo cuando se revierte algo.
    No hace commit: lo hace la operación que llamó a esta función.
    """
    saldo_anterior = float(fondo.saldo or 0)
    saldo_nuevo = saldo_anterior + float(monto)

    fondo.saldo = saldo_nuevo
    fondo.updated_at = datetime.utcnow()
    db.session.add(fondo)

    movimiento = MovimientoFondo(
        fondo_id=fondo.id,
        monto=monto,
        saldo_anterior=saldo_anterior,
        saldo_resultante=saldo_nuevo,
        motivo=motivo
    )
    db.session.add(movimiento)
    return movimiento


def buscar_fondo(destino, carrera_id=None):
    """Decide a qué fondo entra la plata.

    `destino` vale 'carrera' o 'capital'. Si el aporte es para una carrera
    tiene que caer en el fondo de esa carrera y no en el general (RF-09).

    Devuelve (fondo, error). Si el fondo no existe, `fondo` viene en None y
    `error` trae el mensaje para mostrarle al aportante.
    """
    if destino == 'carrera':
        fondo = Fondo.get_de_carrera(carrera_id)
        if not fondo:
            return None, ('La carrera que elegiste todavía no tiene un fondo '
                          'configurado. Avisale a la Cooperadora.')
        return fondo, None

    fondo = Fondo.get_capital()
    if not fondo:
        return None, 'No hay un fondo de capital configurado en el sistema.'
    return fondo, None
