# Pendientes

Bugs y ambigüedades detectados durante trabajos de reorganización, anotados
para no perder el hilo pero sin corregir (fuera del alcance de esa tarea).

## MAX_CONTENT_LENGTH del .env.example no se usa

`.env.example` documenta una variable `MAX_CONTENT_LENGTH` (bytes, 16 MB),
pero `app/config.py` nunca la lee con `os.getenv`: el límite queda fijo en
`TAMANIO_MAXIMO_COMPROBANTE` (`app/constantes.py`) sin importar lo que diga
el `.env`. Detectado en el Bloque 1 (constantes compartidas).
