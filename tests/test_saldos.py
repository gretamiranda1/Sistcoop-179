from datetime import date
from decimal import Decimal

from app.modelos.aportantes import Aportante
from app.modelos.pagos import Pago
from app.modelos.saldos import SaldoAportante
from app.servicios import pagos as servicio_pagos, saldos as servicio_saldos


def test_en_revision_suma_sin_error_de_punto_flotante(db, ejercicio, fondo_capital, datos_de_cuota):
    for i, importe in enumerate([Decimal('10.10'), Decimal('10.20'), Decimal('10.30')]):
        servicio_pagos.crear_pago_de_cuota(
            datos_de_cuota('37111111', importe, 'OPFLOTANTE{}'.format(i),
                           'huella-flotante-{}'.format(i))
        )

    aportante = Aportante.get_by_dni('37111111')
    saldo = SaldoAportante.get_por_aportante(aportante.id, ejercicio.id)

    assert saldo.en_revision == Decimal('30.60')


def test_recalcular_saldo_suma_sin_error_de_punto_flotante(db, ejercicio, fondo_capital):
    aportante = Aportante(nombre='Persona', apellido='De Prueba', dni='39111111')
    db.session.add(aportante)
    db.session.commit()

    saldo = SaldoAportante(aportante_id=aportante.id, ejercicio_id=ejercicio.id,
                           pagado=0, saldo_pendiente=ejercicio.cuota)
    db.session.add(saldo)

    for i, importe in enumerate([Decimal('10.10'), Decimal('10.20'), Decimal('10.30')]):
        pago = Pago(
            codigo_seguimiento='SC{}'.format(i), aportante_id=aportante.id, tipo='cuota',
            importe=importe, fecha=date.today(), medio_pago='transferencia',
            codigo_transaccion='OPSALDO{}'.format(i), hash_comprobante='huella-{}'.format(i),
            fondo_id=fondo_capital.id, ejercicio_id=ejercicio.id, estado='verificado'
        )
        db.session.add(pago)
    db.session.commit()

    servicio_saldos.recalcular_saldo(saldo)

    assert saldo.pagado == Decimal('30.60')