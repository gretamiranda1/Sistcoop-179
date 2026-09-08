"""Módulo Cooperadora — panel de administración.

Lo que hay acá es lo mínimo para poder operar y mostrar el Módulo Aportante
de punta a punta: verificar o rechazar lo que se carga, ver los comprobantes
y gestionar las libretas.

La bandeja completa con filtros, la emisión de recibos por serie y el
registro de egresos son del Incremento 3.
"""

import os
import mimetypes

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_file, abort)
from flask_login import login_required, current_user
from datetime import date

from app.extensions import db
from app.modelos.aportantes import Aportante
from app.modelos.auditoria import Auditoria
from app.modelos.ejercicios import Ejercicio
from app.modelos.fondos import Fondo
from app.modelos.pagos import Pago
from app.modelos.pagos_grupales import PagoGrupal
from app.modelos.saldos import SaldoAportante
from app.modelos.solicitudes import SolicitudFondo
from app.formularios.administracion import FormularioEditarCuota, FormularioNuevoEjercicio
from app.seguridad.permisos import requiere_rol
from app.servicios import auditoria as servicio_auditoria
from app.servicios import ejercicios as servicio_ejercicios
from app.servicios import pagos as servicio_pagos
from app.servicios import pagos_grupales as servicio_grupales
from app.servicios import saldos as servicio_saldos
from app.servicios.pagos import ErrorDeCarga
from app.utilidades import validaciones
from app.utilidades.archivos import ruta_comprobante
from app.utilidades.peticion import ip_y_user_agent

administracion_bp = Blueprint('administracion', __name__)


# ============================================
# PANEL
# ============================================

@administracion_bp.route('/')
@requiere_rol('admin', 'asistente', mensaje='No tenés permisos para acceder a esa sección.')
@login_required
def panel():
    ejercicio = Ejercicio.get_ejercicio_vigente()
    if ejercicio:
        puede_editar_cuota, motivo_cuota = ejercicio.admite_cambio_de_cuota()
    else:
        puede_editar_cuota = False
        motivo_cuota = 'No hay ejercicio vigente.'

    pagina_pendientes = request.args.get('pagina_pendientes', 1, type=int)
    pagina_grupales = request.args.get('pagina_grupales', 1, type=int)
    pendientes = Pago.get_pendientes(pagina_pendientes)
    grupales_pendientes = PagoGrupal.get_pendientes(pagina_grupales)
    solicitudes = SolicitudFondo.query.filter_by(estado='pendiente').order_by(
        SolicitudFondo.created_at.asc()).all()

    return render_template(
        'admin/panel.html',
        ejercicio=ejercicio,
        puede_editar_cuota=puede_editar_cuota,
        motivo_cuota=motivo_cuota,
        pendientes=pendientes,
        grupales_pendientes=grupales_pendientes,
        solicitudes=solicitudes,
        verificados=Pago.query.filter_by(estado='verificado').count(),
        fondos=Fondo.get_activos()
    )


# ============================================
# VERIFICACIÓN DE PAGOS (RF-03)
# ============================================

@administracion_bp.route('/pagos/<int:pago_id>/verificar', methods=['POST'])
@requiere_rol('admin', 'asistente')
@login_required
def verificar_pago(pago_id):
    ip, user_agent = ip_y_user_agent()
    try:
        pago = servicio_pagos.verificar_pago(
            pago_id,
            current_user.id,
            numero_recibo=(request.form.get('numero_recibo') or '').strip() or None,
            serie_recibo=(request.form.get('serie_recibo') or '').strip() or None,
            ip=ip,
            user_agent=user_agent
        )
        flash('Pago {} verificado. El importe se acreditó en {}.'.format(
            pago.codigo_seguimiento, pago.fondo.nombre), 'success')
    except (ErrorDeCarga, ValueError) as error:
        db.session.rollback()
        flash(str(error), 'danger')

    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/pagos/<int:pago_id>/rechazar', methods=['POST'])
@requiere_rol('admin', 'asistente')
@login_required
def rechazar_pago(pago_id):
    ip, user_agent = ip_y_user_agent()
    try:
        pago = servicio_pagos.rechazar_pago(
            pago_id, current_user.id, request.form.get('motivo', ''),
            ip=ip, user_agent=user_agent)
        flash('Pago {} rechazado.'.format(pago.codigo_seguimiento), 'info')
    except (ErrorDeCarga, ValueError) as error:
        db.session.rollback()
        flash(str(error), 'danger')

    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/pagos-grupales/<int:pago_id>/verificar', methods=['POST'])
@requiere_rol('admin', 'asistente')
@login_required
def verificar_pago_grupal(pago_id):
    ip, user_agent = ip_y_user_agent()
    try:
        pago = servicio_grupales.verificar_pago_grupal(
            pago_id, current_user.id, ip=ip, user_agent=user_agent)
        flash('Transferencia grupal {} verificada: se acreditó a {} persona(s).'.format(
            pago.codigo_seguimiento, pago.pagos.count()), 'success')
    except (ErrorDeCarga, ValueError) as error:
        db.session.rollback()
        flash(str(error), 'danger')

    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/pagos-grupales/<int:pago_id>/rechazar', methods=['POST'])
@requiere_rol('admin', 'asistente')
@login_required
def rechazar_pago_grupal(pago_id):
    ip, user_agent = ip_y_user_agent()
    try:
        pago = servicio_grupales.rechazar_pago_grupal(
            pago_id, current_user.id, request.form.get('motivo', ''),
            ip=ip, user_agent=user_agent)
        flash('Transferencia grupal {} rechazada.'.format(pago.codigo_seguimiento), 'info')
    except (ErrorDeCarga, ValueError) as error:
        db.session.rollback()
        flash(str(error), 'danger')

    return redirect(url_for('administracion.panel'))


# ============================================
# COMPROBANTES
# ============================================
#
# Los archivos están guardados fuera de app/static/ justamente para que no se
# puedan abrir con la URL directa. Estas dos rutas son la única puerta, piden
# sesión y dejan anotado en auditoría quién los miró (RNF-01, RNF-02).

def enviar_comprobante(ruta, codigo):
    """Manda el archivo al navegador con su tipo real.

    Si no le pasamos el tipo, el navegador ofrece descargarlo como binario en
    vez de mostrarlo, y quien verifica tiene que abrirlo aparte.
    """
    extension = os.path.splitext(ruta)[1].lower()
    tipo = mimetypes.types_map.get(extension, 'application/octet-stream')

    return send_file(
        ruta,
        mimetype=tipo,
        as_attachment=False,
        download_name='comprobante-{}{}'.format(codigo, extension)
    )


@administracion_bp.route('/comprobante/<int:pago_id>')
@requiere_rol('admin', 'asistente', 'tesorera', mensaje='No tenés permisos para ver los comprobantes.')
@login_required
def ver_comprobante(pago_id):
    pago = Pago.query.get(pago_id)
    if not pago or not pago.comprobante_nombre:
        abort(404)

    ruta = ruta_comprobante(pago.comprobante_nombre)
    if not ruta:
        abort(404)

    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(
        usuario=str(current_user.id),
        accion='ver_comprobante',
        tabla='pagos',
        registro_id=pago.id,
        detalle={'codigo_seguimiento': pago.codigo_seguimiento},
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()

    return enviar_comprobante(ruta, pago.codigo_seguimiento)


@administracion_bp.route('/comprobante-grupal/<int:pago_id>')
@requiere_rol('admin', 'asistente', 'tesorera', mensaje='No tenés permisos para ver los comprobantes.')
@login_required
def ver_comprobante_grupal(pago_id):
    pago = PagoGrupal.query.get(pago_id)
    if not pago or not pago.comprobante_nombre:
        abort(404)

    ruta = ruta_comprobante(pago.comprobante_nombre)
    if not ruta:
        abort(404)

    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(
        usuario=str(current_user.id),
        accion='ver_comprobante_grupal',
        tabla='pagos_grupales',
        registro_id=pago.id,
        detalle={'codigo_seguimiento': pago.codigo_seguimiento},
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()

    return enviar_comprobante(ruta, pago.codigo_seguimiento)


# ============================================
# EJERCICIO Y CUOTA
# ============================================

@administracion_bp.route('/editar-cuota', methods=['POST'])
@requiere_rol('admin')
@login_required
def editar_cuota():
    """Corrige el importe de la cuota del ejercicio vigente.

    Sólo se puede mientras el ejercicio no tenga ningún pago cargado. La
    cuota se fija en asamblea y no se modifica durante el año (Propuesta,
    sección 6): esto es para arreglar un error de tipeo al abrir el
    ejercicio, no para cambiar la cuota a mitad de camino.
    """
    ejercicio = Ejercicio.get_ejercicio_vigente()
    if not ejercicio:
        flash('No hay un ejercicio vigente.', 'danger')
        return redirect(url_for('administracion.panel'))

    permitido, motivo = ejercicio.admite_cambio_de_cuota()
    if not permitido:
        flash(motivo, 'danger')
        return redirect(url_for('administracion.panel'))

    formulario = FormularioEditarCuota()
    if not formulario.validate_on_submit():
        flash(formulario.cuota.errors[0], 'danger')
        return redirect(url_for('administracion.panel'))

    nuevo_monto = round(float(formulario.cuota.data), 2)

    anterior = ejercicio.cuota
    ejercicio.cuota = nuevo_monto

    # Los saldos ya no guardan la cuota (sale de ejercicio.cuota): sólo hay
    # que recalcular lo que sí queda en cada uno, saldo_pendiente y estado
    for saldo in SaldoAportante.query.filter_by(ejercicio_id=ejercicio.id).all():
        servicio_saldos.recalcular_saldo(saldo)

    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(
        usuario=str(current_user.id),
        accion='corregir_cuota',
        tabla='ejercicios',
        registro_id=ejercicio.id,
        detalle={'valor_anterior': str(anterior), 'valor_nuevo': str(nuevo_monto)},
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()

    flash('Cuota del ejercicio {} corregida a ${:,.2f}.'.format(
        ejercicio.anio, nuevo_monto), 'success')
    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/nuevo-ejercicio', methods=['POST'])
@requiere_rol('admin')
@login_required
def nuevo_ejercicio():
    """Cierra el ejercicio vigente y abre el siguiente"""
    formulario = FormularioNuevoEjercicio()
    if not formulario.validate_on_submit():
        flash('Año o cuota inválidos.', 'danger')
        return redirect(url_for('administracion.panel'))

    anio = int(formulario.anio.data)
    cuota = round(float(formulario.cuota.data), 2)

    if Ejercicio.query.filter_by(anio=anio).first():
        flash('Ya existe un ejercicio {}.'.format(anio), 'danger')
        return redirect(url_for('administracion.panel'))

    fecha_asamblea = formulario.fecha_asamblea.data
    fecha_asamblea = date.fromisoformat(fecha_asamblea) if fecha_asamblea else None

    nuevo, anterior = servicio_ejercicios.abrir_ejercicio(anio, cuota, fecha_asamblea)

    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(
        usuario=str(current_user.id),
        accion='abrir_ejercicio',
        tabla='ejercicios',
        registro_id=None,
        detalle={
            'anio': anio,
            'cuota': str(cuota),
            'ejercicio_cerrado': anterior.anio if anterior else None
        },
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()

    flash('Ejercicio {} abierto con una cuota de ${:,.2f}.'.format(anio, cuota), 'success')
    return redirect(url_for('administracion.panel'))


# ============================================
# LIBRETAS
# ============================================
#
# La cuota de Cooperadora es voluntaria: el sistema NO puede condicionar la
# entrega de la libreta ni de ninguna otra documentación por falta de pago
# (Propuesta sección 6, RF-13). Por eso el botón de entregar está siempre
# habilitado. El saldo pendiente que aparece al lado es sólo información para
# quien atiende el mostrador.

@administracion_bp.route('/libretas')
@requiere_rol('admin', 'asistente', 'preceptoria', mensaje='No tenés permisos para acceder a esa sección.')
@login_required
def gestion_libretas():
    dni = validaciones.limpiar_dni(request.args.get('dni', ''))
    aportante = None
    saldo = None
    pagos_libreta = []

    if dni:
        if not validaciones.validar_dni(dni):
            flash('Ingresá un DNI válido, sin puntos.', 'warning')
        else:
            aportante = Aportante.get_by_dni(dni)
            if aportante:
                ejercicio = Ejercicio.get_ejercicio_vigente()
                if ejercicio:
                    saldo = servicio_saldos.buscar_o_crear_saldo(
                        aportante.id, ejercicio.id, ejercicio.cuota)
                    db.session.commit()

                pagos_libreta = Pago.query.filter_by(
                    aportante_id=aportante.id,
                    solicita_libreta=True
                ).order_by(Pago.created_at.desc()).all()
            else:
                flash('No hay ningún aportante registrado con ese DNI.', 'info')

    return render_template('admin/libretas.html', dni=dni, aportante=aportante,
                           saldo=saldo, pagos_libreta=pagos_libreta)


@administracion_bp.route('/libretas/<int:saldo_id>/entregar', methods=['POST'])
@requiere_rol('admin', 'asistente', 'preceptoria')
@login_required
def entregar_libreta(saldo_id):
    saldo = SaldoAportante.query.get(saldo_id)
    if not saldo:
        flash('No encontramos el registro.', 'danger')
        return redirect(url_for('administracion.gestion_libretas'))

    if saldo.libreta_entregada:
        flash('Esa libreta ya figura entregada.', 'warning')
        return redirect(url_for('administracion.gestion_libretas', dni=saldo.aportante.dni))

    pendiente = float(saldo.saldo_pendiente or 0)
    servicio_saldos.entregar_libreta(saldo)

    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(
        usuario=str(current_user.id),
        accion='entregar_libreta',
        tabla='saldos_aportantes',
        registro_id=saldo.id,
        detalle={'dni': saldo.aportante.dni,
                 'saldo_pendiente_al_momento': str(pendiente)},
        ip=ip,
        user_agent=user_agent
    )
    db.session.commit()

    if pendiente > 0:
        flash('Libreta entregada. Quedan ${:,.2f} de cuota pendiente (dato '
              'informativo: la cuota es voluntaria).'.format(pendiente), 'success')
    else:
        flash('Libreta entregada.', 'success')

    return redirect(url_for('administracion.gestion_libretas', dni=saldo.aportante.dni))


# ============================================
# AUDITORÍA
# ============================================

@administracion_bp.route('/auditoria')
@requiere_rol('admin', 'tesorera', mensaje='No tenés permisos para acceder a esa sección.')
@login_required
def auditoria():
    """Registro de todas las operaciones, de la más nueva a la más vieja (RNF-04)"""
    pagina = request.args.get('pagina', 1, type=int)
    registros = Auditoria.get_ultimas(pagina)

    return render_template('admin/auditoria.html', registros=registros)
