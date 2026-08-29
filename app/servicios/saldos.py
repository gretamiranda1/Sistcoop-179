"""Cálculo del saldo de cuota de cada aportante.

REGLA: el saldo se RECALCULA, no se acumula. Cada vez que algo cambia
volvemos a sumar los pagos verificados desde cero. Así, si un pago se
rechaza o se anula, el saldo se arregla solo, y un saldo mal calculado se
corrige volviendo a llamar a recalcular_saldo.
"""

from datetime import datetime

from app.extensions import db
from app.modelos.pagos import Pago, TIPOS_DE_CUOTA
from app.modelos.saldos import SaldoAportante


def buscar_o_crear_saldo(aportante_id, ejercicio_id, cuota_total):
    """Devuelve el saldo de esa persona para ese ejercicio; si no existe lo crea en cero.

    Crear el saldo NO acredita nada: nace con pagado = 0 y con toda la cuota
    pendiente.
    """
    saldo = SaldoAportante.get_por_aportante(aportante_id, ejercicio_id)

    if not saldo:
        saldo = SaldoAportante(
            aportante_id=aportante_id,
            ejercicio_id=ejercicio_id,
            cuota_total=cuota_total,
            pagado=0,
            saldo_pendiente=cuota_total,
            estado='pendiente'
        )
        db.session.add(saldo)
        # flush() manda el INSERT a la base y le asigna el id a la fila, pero
        # todavía no confirma nada: eso lo hace el commit del final.
        db.session.flush()
        return saldo

    # Si la cuota del ejercicio se corrigió, el saldo se realinea
    if float(saldo.cuota_total) != float(cuota_total):
        saldo.cuota_total = cuota_total
        recalcular_saldo(saldo)

    return saldo


def recalcular_saldo(saldo):
    """Vuelve a sumar los pagos verificados de ese aportante y ese ejercicio.

    No hace commit: lo hace la operación que llamó a esta función.
    """
    pagos = Pago.get_de_cuota(saldo.aportante_id, saldo.ejercicio_id, 'verificado')

    total = 0
    for pago in pagos:
        total = total + float(pago.importe)

    saldo.pagado = total
    pendiente = float(saldo.cuota_total) - total

    if pendiente <= 0:
        saldo.saldo_pendiente = 0
        saldo.estado = 'al_dia'
    else:
        saldo.saldo_pendiente = pendiente
        saldo.estado = 'pendiente'

    saldo.updated_at = datetime.utcnow()
    db.session.add(saldo)
    return saldo


def recalcular_saldo_de_pago(pago):
    """Recalcula el saldo que le corresponde a un pago, si es que le corresponde alguno.

    Un aporte adicional o un duplicado de libreta no bajan la cuota de nadie,
    así que no tienen saldo que recalcular.
    """
    if pago.tipo not in TIPOS_DE_CUOTA:
        return None
    if not pago.ejercicio_id:
        return None

    saldo = SaldoAportante.get_por_aportante(pago.aportante_id, pago.ejercicio_id)
    if saldo:
        recalcular_saldo(saldo)
    return saldo


def entregar_libreta(saldo):
    """Deja registrado que se entregó la libreta.

    No se controla si la cuota está paga: la cuota es voluntaria y el sistema
    no puede retener documentación académica (RF-13).
    """
    saldo.libreta_entregada = True
    saldo.fecha_libreta = datetime.utcnow()
    saldo.updated_at = datetime.utcnow()
    db.session.add(saldo)
    return saldo
