"""Restricciones CHECK en dominios de estado y tipo

Revision ID: 909b3621ff6e
Revises: 8a078e83d673
Create Date: 2026-09-05 16:47:05.047228

Alembic no detecta constraints CHECK con autogenerate, así que esta
migración se escribió a mano (ver docs/PENDIENTES.md).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '909b3621ff6e'
down_revision = '8a078e83d673'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_pagos_estado',
            "estado IN ('pendiente', 'verificado', 'rechazado', 'anulado')"
        )
        batch_op.create_check_constraint(
            'ck_pagos_tipo',
            "tipo IN ('cuota', 'cuota_grupal', 'adicional', 'aporte_carrera', "
            "'libreta_duplicado')"
        )

    with op.batch_alter_table('fondos', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_fondos_tipo',
            "tipo IN ('capital', 'carrera', 'evento')"
        )

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_usuarios_rol',
            "rol IN ('admin', 'asistente', 'tesorera', 'preceptoria')"
        )

    with op.batch_alter_table('solicitudes_fondo', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'ck_solicitudes_fondo_tipo',
            "tipo IN ('fondos', 'evento', 'viaje')"
        )
        batch_op.create_check_constraint(
            'ck_solicitudes_fondo_estado',
            "estado IN ('pendiente', 'aprobada', 'rechazada')"
        )


def downgrade():
    with op.batch_alter_table('solicitudes_fondo', schema=None) as batch_op:
        batch_op.drop_constraint('ck_solicitudes_fondo_estado', type_='check')
        batch_op.drop_constraint('ck_solicitudes_fondo_tipo', type_='check')

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint('ck_usuarios_rol', type_='check')

    with op.batch_alter_table('fondos', schema=None) as batch_op:
        batch_op.drop_constraint('ck_fondos_tipo', type_='check')

    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_constraint('ck_pagos_tipo', type_='check')
        batch_op.drop_constraint('ck_pagos_estado', type_='check')
