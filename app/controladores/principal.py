from flask import Blueprint, redirect, url_for

principal_bp = Blueprint('principal', __name__)


@principal_bp.route('/')
def index():
    """La raíz lleva al portal del aportante, que es por donde entra casi todo el mundo"""
    return redirect(url_for('aportantes.inicio'))


@principal_bp.route('/salud')
def salud():
    """Para que el hosting pueda chequear que la aplicación responde"""
    return {'estado': 'ok'}, 200
