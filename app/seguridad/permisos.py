"""Decorador para exigir sesión iniciada y un rol determinado.

Reemplaza al chequeo sin_permiso() que había que repetir a mano al
principio de cada vista de administracion.py: si una vista nueva se
olvidaba de esa línea, quedaba accesible a cualquier usuario logueado
(RF-14, RNF-01).
"""

from functools import wraps

from flask import current_app, flash, redirect, url_for
from flask_login import current_user, logout_user


def requiere_rol(*roles, mensaje='No tenés permisos para hacer eso.'):
    """Sólo deja pasar a un usuario logueado con alguno de estos roles.

    Sin sesión iniciada se comporta igual que login_required: delega en el
    login_manager, que manda al login y vuelve acá después. Con sesión
    iniciada pero sin ninguno de los roles permitidos, avisa por flash y
    redirige al portal del aportante.
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if not current_user.is_active:
                logout_user()
                flash('Tu cuenta fue desactivada. Iniciá sesión de nuevo o '
                      'contactate con un administrador.', 'danger')
                return current_app.login_manager.unauthorized()
            if current_user.rol not in roles:
                flash(mensaje, 'danger')
                return redirect(url_for('aportantes.inicio'))
            return vista(*args, **kwargs)
        return envoltura
    return decorador