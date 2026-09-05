from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

from app.extensions import db
from app.modelos.usuarios import Usuario
from app.servicios import auditoria as servicio_auditoria
from app.utilidades.limite_peticiones import excede_limite
from app.utilidades.peticion import ip_y_user_agent

autenticacion_bp = Blueprint('autenticacion', __name__)


@autenticacion_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Ingreso al área administrativa (RNF-01)"""
    if current_user.is_authenticated:
        return redirect(url_for('administracion.panel'))

    if request.method == 'POST':
        # Tope de intentos por IP, para que no se pueda ir probando
        # contraseñas de a miles
        if excede_limite('login', limite=10, ventana=300):
            flash('Demasiados intentos de acceso. Esperá unos minutos.', 'warning')
            return render_template('auth/login.html')

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        ip, user_agent = ip_y_user_agent()

        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and usuario.check_password(password) and usuario.activo:
            login_user(usuario)
            usuario.ultimo_login = datetime.utcnow()

            servicio_auditoria.registrar(usuario=str(usuario.id), accion='login',
                                         tabla='usuarios', registro_id=usuario.id,
                                         ip=ip, user_agent=user_agent)
            db.session.commit()

            flash('Bienvenido, {}.'.format(usuario.nombre or usuario.username), 'success')
            return redirect(url_for('administracion.panel'))

        # El mensaje es siempre el mismo, no aclaramos si falló el usuario o
        # la contraseña: decirlo le confirma a quien prueba qué usuarios existen
        servicio_auditoria.registrar(usuario=username or 'desconocido',
                                     accion='login_fallido', tabla='usuarios',
                                     ip=ip, user_agent=user_agent)
        db.session.commit()
        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@autenticacion_bp.route('/logout')
@login_required
def logout():
    ip, user_agent = ip_y_user_agent()
    servicio_auditoria.registrar(usuario=str(current_user.id), accion='logout',
                                 tabla='usuarios', registro_id=current_user.id,
                                 ip=ip, user_agent=user_agent)
    db.session.commit()

    logout_user()
    flash('Cerraste la sesión.', 'info')
    return redirect(url_for('aportantes.inicio'))
