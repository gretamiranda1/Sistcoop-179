"""El formulario grupal no puede perder datos ante un error (issue #63)."""
import io
import re
from datetime import date

from app.modelos.pagos import Pago
from app.servicios import pagos as servicio_pagos


def _archivo_valido():
    contenido = b'%PDF-1.4' + b'0' * 1200  # > 1 KB, firma de PDF válida
    return (io.BytesIO(contenido), 'comprobante.pdf')


def test_grupal_conserva_los_datos_de_las_personas_ante_un_error(client, db, ejercicio, fondo_capital):
    resp = client.post('/aportante/cuota', data={
        'es_grupal': 'true',
        'importe_total': '40000',
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPGRUPALQA1',
        'tipo_distribucion': 'auto',
        'cantidad_personas': '2',
        'dni_1': '44111111', 'nombre_1': 'Valentina', 'apellido_1': 'Soto',
        'carrera_1': '', 'anio_1': '',
        'dni_2': '',  # persona 2 incompleta a propósito: dispara el error
        'nombre_2': '', 'apellido_2': '', 'carrera_2': '', 'anio_2': '',
        'comprobante': _archivo_valido(),
    }, content_type='multipart/form-data')

    html = resp.get_data(as_text=True)

    assert resp.status_code == 400
    assert 'value="44111111"' in html
    assert 'Valentina' in html
    assert 'Soto' in html


def test_grupal_no_pide_re_subir_el_comprobante_en_un_reintento(
        client, db, ejercicio, fondo_capital, carrera):
    # Un pago ya cargado con este código de operación, para que el segundo
    # intento del formulario grupal falle DENTRO del try (no en la validación
    # previa): así el comprobante ya se leyó y guardó cuando el error ocurre.
    servicio_pagos.crear_pago_de_cuota({
        'nombre': 'Ya', 'apellido': 'Existe', 'dni': '46000000',
        'carrera_id': carrera.id, 'anio': '1°',
        'importe': 5000, 'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPYAUSADOQA', 'hash_comprobante': 'huella-ya-usada',
    })

    datos_personas = {
        'dni_1': '45111111', 'nombre_1': 'Ana', 'apellido_1': 'Perez',
        'carrera_1': str(carrera.id), 'anio_1': '1°',
        'dni_2': '45222222', 'nombre_2': 'Bea', 'apellido_2': 'Perez',
        'carrera_2': str(carrera.id), 'anio_2': '1°',
    }

    primer_intento = client.post('/aportante/cuota', data={
        'es_grupal': 'true',
        'importe_total': '40000',
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPYAUSADOQA',  # repetido: falla en el servicio
        'tipo_distribucion': 'auto',
        'cantidad_personas': '2',
        **datos_personas,
        'comprobante': _archivo_valido(),
    }, content_type='multipart/form-data')

    assert primer_intento.status_code == 400
    html = primer_intento.get_data(as_text=True)
    assert 'comprobante_nombre_previo' in html
    assert 'comprobante.pdf' in html  # el nombre real, no el generado al azar

    nombre_guardado = re.search(r'name="comprobante_nombre_previo" value="([^"]+)"', html).group(1)

    segundo_intento = client.post('/aportante/cuota', data={
        'es_grupal': 'true',
        'importe_total': '40000',
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPSEGUNDOQA',
        'tipo_distribucion': 'auto',
        'cantidad_personas': '2',
        **datos_personas,
        'comprobante_nombre_previo': nombre_guardado,
        # sin volver a mandar 'comprobante'
    }, content_type='multipart/form-data')

    assert segundo_intento.status_code == 302  # redirige a éxito

    pago = Pago.query.filter_by(comprobante_nombre=nombre_guardado).first()
    assert pago is not None


def test_comprobante_se_preserva_aunque_el_error_sea_una_persona_incompleta(
        client, db, ejercicio, fondo_capital, carrera):
    """Este es el caso real y más común: el error lo detecta la validación
    previa (una persona con un campo vacío), no el servicio. Antes, en ese
    caso el comprobante nunca se llegaba a leer y el reintento lo volvía a
    pedir."""
    primer_intento = client.post('/aportante/cuota', data={
        'es_grupal': 'true',
        'importe_total': '40000',
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPPERSONAINCOMPLETA',
        'tipo_distribucion': 'auto',
        'cantidad_personas': '2',
        'dni_1': '47111111', 'nombre_1': 'Cami', 'apellido_1': 'Ruiz',
        'carrera_1': str(carrera.id), 'anio_1': '1°',
        'dni_2': '47222222', 'nombre_2': '', 'apellido_2': '',  # falta a propósito
        'carrera_2': str(carrera.id), 'anio_2': '1°',
        'comprobante': _archivo_valido(),
    }, content_type='multipart/form-data')

    assert primer_intento.status_code == 400
    html = primer_intento.get_data(as_text=True)
    assert 'comprobante_nombre_previo' in html

    nombre_guardado = re.search(r'name="comprobante_nombre_previo" value="([^"]+)"', html).group(1)

    segundo_intento = client.post('/aportante/cuota', data={
        'es_grupal': 'true',
        'importe_total': '40000',
        'fecha': date.today().isoformat(),
        'codigo_transaccion': 'OPPERSONAINCOMPLETA',
        'tipo_distribucion': 'auto',
        'cantidad_personas': '2',
        'dni_1': '47111111', 'nombre_1': 'Cami', 'apellido_1': 'Ruiz',
        'carrera_1': str(carrera.id), 'anio_1': '1°',
        'dni_2': '47222222', 'nombre_2': 'Dario', 'apellido_2': 'Ruiz',  # corregido
        'carrera_2': str(carrera.id), 'anio_2': '1°',
        'comprobante_nombre_previo': nombre_guardado,
        # sin volver a mandar 'comprobante'
    }, content_type='multipart/form-data')

    assert segundo_intento.status_code == 302

    pago = Pago.query.filter_by(comprobante_nombre=nombre_guardado).first()
    assert pago is not None
