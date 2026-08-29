"""Servicios: las reglas de negocio.

Regla del proyecto: los modelos describen las tablas y saben responder
consultas; TODO lo que modifica datos está acá. Así, para entender qué pasa
cuando se verifica un pago, alcanza con leer una función.

Se importan por módulo, para que se vea de dónde sale cada función:

    from app.servicios import pagos
    pagos.verificar_pago(pago_id, usuario_id)
"""
