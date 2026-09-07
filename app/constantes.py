"""Valores compartidos por más de un módulo.

Antes de agregar algo acá: si sólo lo usa un archivo, va en ese archivo.
"""

TAMANIO_MAXIMO_COMPROBANTE = 16 * 1024 * 1024   # 16 MB
TAMANIO_MINIMO_COMPROBANTE = 1024               # 1 KB: menos que esto no es un comprobante

ANIOS = ['1°', '2°', '3°']

# Formatos que aceptamos para un comprobante, con la extensión con la que se
# guardan. La clave es la firma: los primeros bytes que tiene todo archivo de
# ese tipo.
FIRMAS_ARCHIVO = [
    (b'\xff\xd8\xff', '.jpg'),
    (b'\x89PNG\r\n\x1a\n', '.png'),
    (b'%PDF-', '.pdf'),
]
