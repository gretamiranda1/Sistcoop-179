"""Apertura de un ejercicio nuevo.

Sólo puede haber un ejercicio VIGENTE (activo y no cerrado) a la vez. La
base lo garantiza con un índice único parcial sobre (activo) filtrado a
activo=1 AND cerrado=0 (ver la migración que agrega uq_ejercicio_vigente),
pero esta función es la que cierra el anterior antes de abrir el que sigue:
sin ella, cada llamador tendría que acordarse de hacerlo a mano, y si se
olvida, el índice de la base rechaza el alta con un IntegrityError en vez
del mensaje de negocio que corresponde.
"""

from app.extensions import db
from app.modelos.ejercicios import Ejercicio


def abrir_ejercicio(anio, cuota, fecha_asamblea=None):
    """Cierra el ejercicio vigente (si hay uno) y abre el nuevo.

    Devuelve (nuevo, anterior); `anterior` es None si no había ningún
    ejercicio vigente. No hace commit: lo hace quien llamó a esta función.
    """
    anterior = Ejercicio.get_ejercicio_vigente()
    if anterior:
        anterior.activo = False
        anterior.cerrado = True
        db.session.add(anterior)
        # Se cierra el anterior ANTES de crear el nuevo: si los dos quedaran
        # pendientes en el mismo flush, el orden en que la sesión los manda
        # a la base no está garantizado, y el índice único parcial rechazaría
        # el insert si por un instante hay dos filas vigentes.
        db.session.flush()

    nuevo = Ejercicio(
        anio=anio,
        cuota=cuota,
        fecha_asamblea=fecha_asamblea,
        activo=True,
        cerrado=False
    )
    db.session.add(nuevo)
    db.session.flush()

    return nuevo, anterior
