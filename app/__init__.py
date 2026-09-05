import os
from flask import Flask, render_template

from app.config import config, ProductionConfig
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name='development'):
    app = Flask(__name__, template_folder='vistas')
    app.config.from_object(config[config_name])

    if config_name == 'production':
        ProductionConfig.validar()

    # Carpetas que tienen que existir sí o sí
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Los controladores se importan ACÁ ADENTRO y no arriba del archivo a
    # propósito: cada uno usa db, que se crea en este mismo archivo. Si los
    # importáramos arriba, Python entraría en un círculo. Es la forma normal
    # de armar una aplicación Flask con una función de fábrica.
    from app.controladores.autenticacion import autenticacion_bp
    from app.controladores.aportantes import aportantes_bp
    from app.controladores.administracion import administracion_bp
    from app.controladores.api import api_bp
    from app.controladores.principal import principal_bp

    app.register_blueprint(autenticacion_bp, url_prefix='/auth')
    app.register_blueprint(aportantes_bp, url_prefix='/aportante')
    app.register_blueprint(administracion_bp, url_prefix='/admin')
    # Mismo prefijo que aportantes_bp: las URL de estos cuatro endpoints no
    # cambian (/aportante/api/...), sólo el archivo donde vive el código.
    app.register_blueprint(api_bp, url_prefix='/aportante')
    app.register_blueprint(principal_bp)

    from app.modelos.usuarios import Usuario

    @login_manager.user_loader
    def cargar_usuario(user_id):
        return Usuario.query.get(int(user_id))

    @app.context_processor
    def contexto_global():
        """Variables que quedan disponibles en todas las plantillas"""
        # Mismo motivo que arriba: el modelo usa db, que se crea en este archivo
        from app.modelos.ejercicios import Ejercicio
        return {
            'app_name': 'SistCoop 179',
            'instituto': 'ISFT N° 179 "Dr. Carlos Pellegrini"',
            'ejercicio_vigente': Ejercicio.get_ejercicio_vigente(),
        }

    @app.template_filter('pesos')
    def formato_pesos(valor):
        """Muestra un importe como $ 1.234.567,89 (formato argentino)"""
        try:
            numero = float(valor or 0)
        except (ValueError, TypeError):
            return '$ 0,00'

        # Python formatea con coma para los miles y punto para los decimales,
        # así que hay que darlos vuelta.
        entero, decimal = '{:,.2f}'.format(numero).split('.')
        entero = entero.replace(',', '.')
        return '$ {},{}'.format(entero, decimal)

    registrar_errores(app)
    return app


def registrar_errores(app):
    """Páginas de error propias.

    Además de verse mejor, evitan que un error interno le muestre al
    aportante el detalle técnico de lo que falló.
    """

    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template('errores/404.html'), 404

    @app.errorhandler(403)
    def prohibido(error):
        return render_template('errores/403.html'), 403

    @app.errorhandler(413)
    def archivo_muy_grande(error):
        return render_template(
            'errores/generico.html',
            titulo='El archivo es demasiado grande',
            detalle='El comprobante no puede pesar más de 16 MB. Probá sacarle '
                    'una foto con menos resolución.'
        ), 413

    @app.errorhandler(500)
    def error_interno(error):
        db.session.rollback()
        app.logger.exception('Error interno')
        return render_template('errores/500.html'), 500
