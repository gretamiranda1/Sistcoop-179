import re
from pathlib import Path
from datetime import datetime

import pdfplumber
import easyocr


_reader = None


def get_ocr_reader():
    """
    Inicializa EasyOCR una sola vez.
    """
    global _reader

    if _reader is None:
        _reader = easyocr.Reader(["es"])

    return _reader


def extraer_texto_pdf(ruta_archivo):
    """
    Extrae texto directamente desde PDFs.
    """
    texto = ""

    with pdfplumber.open(ruta_archivo) as pdf:
        for pagina in pdf.pages:
            contenido = pagina.extract_text()

            if contenido:
                texto += contenido + "\n"

    return texto.strip()


def extraer_texto_imagen(ruta_archivo):
    """
    Extrae texto usando OCR.
    """
    reader = get_ocr_reader()

    resultado = reader.readtext(
        ruta_archivo,
        detail=0
    )

    return "\n".join(resultado)


def obtener_texto(ruta_archivo):
    """
    Decide automáticamente si usar PDF o OCR.
    """
    extension = Path(ruta_archivo).suffix.lower()

    if extension == ".pdf":
        texto = extraer_texto_pdf(ruta_archivo)

        if texto:
            return texto

    return extraer_texto_imagen(ruta_archivo)


def extraer_operacion(texto):

    patrones = [
        r"operaci[oó]n.*?(\d{10,20})",
        r"transacci[oó]n.*?(\d{10,20})",
        r"referencia.*?(\d{10,20})",
    ]

    for patron in patrones:
        match = re.search(
            patron,
            texto,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            return match.group(1)

    numeros = re.findall(
        r"\b\d{10,20}\b",
        texto
    )

    return numeros[-1] if numeros else None



def extraer_cuit_cuil(texto):
    """
    Busca todos los CUIT/CUIL presentes.
    """
    encontrados = re.findall(r"\b\d{11}\b", texto)

    return encontrados


def extraer_importe(texto):
    match = re.search(
        r"\$\s*([\d\.\,]+)",
        texto
    )

    if not match:
        match = re.search(
            r"monto\s+([\d\.\,]+)",
            texto,
            re.IGNORECASE
        )

    if not match:
        return None

    importe = match.group(1).strip()

    # Formato argentino:
    # 120.000,00
    if "," in importe:
        importe = importe.replace(".", "")
        importe = importe.replace(",", ".")
        return float(importe)

    # Si no tiene coma, asumir que el OCR la perdió
    # y que los últimos 2 dígitos son decimales
    if "." in importe:
        partes = importe.split(".")

        # Caso: 12.10000 -> 12100.00
        if len(partes[-1]) > 2:
            importe = "".join(partes[:-1]) + partes[-1]
            importe = importe[:-2] + "." + importe[-2:]

        return float(importe)

    return float(importe)

def detectar_entidad(texto):
    texto_lower = texto.lower()

    if "mercado pago" in texto_lower:
        return "Mercado Pago"

    if "bbva" in texto_lower:
        return "BBVA"

    if "santander" in texto_lower:
        return "Santander"
    
    if "galicia" in texto_lower:
        return "Galicia"
    
    return None


import re

def extraer_fecha(texto):

    # Formato 31/07/2026
    match = re.search(
        r'(\d{2})/(\d{2})/(\d{4})',
        texto
    )

    if match:
        dia = match.group(1)
        mes = match.group(2)
        anio = match.group(3)

        return f"{anio}-{mes}-{dia}"

    # Formato 10 de septiembre de 2026
    match = re.search(
        r'(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de)?\s+(\d{4})',
        texto.lower()
    )

    if match:
            meses = {
                    "enero": 1,
                    "febrero":2,
                    "marzo": 3,
                    "abril": 4,
                    "mayo": 5,
                    "junio": 6,
                    "julio": 7,
                    "agosto": 8,
                    "septiembre": 9,
                    "octubre": 10,
                    "noviembre": 11,
                    "diciembre": 12,
                }

            dia = int(match.group(1))
            mes = meses.get(match.group(2))
            anio = int(match.group(3))

            if mes:
                return f"{anio}-{mes:02d}-{dia:02d}"

            print("NO SE PUDO EXTRAER FECHA")
            return None  

#def limpiar_texto_ocr(texto):

#   while re.search(r'(.)\1', texto):
#        texto = re.sub(r'(.)\1', r'\1', texto)

#   return texto

def extraer_datos_comprobante(ruta_archivo):
    try:
        texto = obtener_texto(ruta_archivo)

        return {
            "entidad": detectar_entidad(texto),
            "fecha": extraer_fecha(texto),
            "importe": extraer_importe(texto),
            "operacion": extraer_operacion(texto),
            "cuit_cuil": extraer_cuit_cuil(texto),
            "texto": texto,
        }

    except Exception:
        return {
            "entidad": None,
            "fecha": None,
            "importe": None,
            "operacion": None,
            "cuit_cuil": [],
            "texto": "",
        }

