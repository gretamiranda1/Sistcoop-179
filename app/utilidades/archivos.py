"""Guardado y control de los comprobantes de transferencia.

Los comprobantes NO se guardan dentro de app/static/. Todo lo que está en
static lo puede bajar cualquiera que adivine la URL, y un comprobante tiene
el nombre, el banco y el importe de una persona. Se guardan en
instance/comprobantes y se abren por una ruta que pide sesión iniciada
(RNF-02).
"""

import os
import uuid
import hashlib
from datetime import datetime

from flask import current_app

# Formatos que aceptamos, con la extensión con la que los guardamos.
# La clave es la firma: los primeros bytes que tiene todo archivo de ese tipo.
FIRMAS = [
    (b'\xff\xd8\xff', '.jpg'),
    (b'\x89PNG\r\n\x1a\n', '.png'),
    (b'%PDF-', '.pdf'),
]

TAMANIO_MAXIMO = 16 * 1024 * 1024   # 16 MB
TAMANIO_MINIMO = 1024               # 1 KB: menos que esto no es un comprobante


class ArchivoInvalido(Exception):
    """El comprobante que subieron no sirve.

    El mensaje de la excepción es el que se le muestra al aportante, así que
    tiene que estar escrito para que lo entienda cualquiera.
    """


def detectar_extension(cabecera):
    """Devuelve la extensión que le corresponde al archivo, o None.

    Miramos los primeros bytes del contenido y no la extensión del nombre,
    porque la extensión la elige quien sube el archivo: se puede llamar
    "comprobante.pdf" y ser cualquier otra cosa.
    """
    for firma, extension in FIRMAS:
        if cabecera.startswith(firma):
            return extension
    return None


def carpeta_comprobantes():
    """Carpeta donde se guardan los comprobantes. La crea si no existe."""
    carpeta = current_app.config['UPLOAD_FOLDER']
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def guardar_comprobante(archivo):
    """Controla el archivo subido y lo guarda.

    Devuelve un diccionario con el nombre con el que quedó guardado y su
    huella SHA-256.

    La huella es lo que nos permite darnos cuenta de que alguien vuelve a
    subir el mismo comprobante con otro nombre (RF-04): dos archivos con el
    mismo contenido dan siempre la misma huella.
    """
    if not archivo or not archivo.filename:
        raise ArchivoInvalido('Tenés que adjuntar el comprobante de la transferencia.')

    contenido = archivo.read()
    tamanio = len(contenido)

    if tamanio > TAMANIO_MAXIMO:
        raise ArchivoInvalido('El comprobante pesa más de 16 MB. Probá sacarle '
                              'una foto con menos resolución.')
    if tamanio < TAMANIO_MINIMO:
        raise ArchivoInvalido('El archivo está vacío o dañado. Volvé a adjuntarlo.')

    extension = detectar_extension(contenido[:16])
    if not extension:
        raise ArchivoInvalido('El archivo tiene que ser una imagen JPG o PNG, o '
                              'un PDF. Una foto o una captura del comprobante sirve.')

    huella = hashlib.sha256(contenido).hexdigest()

    # Le ponemos un nombre nuevo: así no se pisan dos archivos con el mismo
    # nombre, y no conservamos el original, que muchas veces trae el nombre
    # y el DNI de la persona.
    momento = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = momento + '_' + uuid.uuid4().hex[:12] + extension

    ruta = os.path.join(carpeta_comprobantes(), nombre)
    with open(ruta, 'wb') as destino:
        destino.write(contenido)

    return {'nombre': nombre, 'hash': huella}


def ruta_comprobante(nombre):
    """Ruta completa de un comprobante guardado, o None si no existe.

    Rechazamos cualquier nombre con barras o que empiece con un punto, para
    que nadie pueda pedir un archivo de otra carpeta del servidor mandando
    algo como "../../.env".
    """
    if not nombre:
        return None
    if '/' in nombre or '\\' in nombre or nombre.startswith('.'):
        return None

    ruta = os.path.join(carpeta_comprobantes(), nombre)
    if os.path.exists(ruta):
        return ruta
    return None
