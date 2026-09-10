import os
from dotenv import load_dotenv

from app.constantes import TAMANIO_MAXIMO_COMPROBANTE

load_dotenv()

# Carpeta raíz del proyecto (una arriba de app/)
RAIZ = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class ConfigInvalida(Exception):
    """Falta algo en el .env como para arrancar en producción."""


class Config:
    """Configuración común a todos los entornos"""

    SECRET_KEY = os.getenv('SECRET_KEY')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Los comprobantes NO van en app/static/. Todo lo que está ahí lo sirve
    # Flask a cualquiera que sepa la URL, y un comprobante tiene el nombre y
    # la cuenta bancaria de la persona. Se sirven desde /admin/comprobante/,
    # que pide sesión iniciada.
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(RAIZ, 'instance', 'comprobantes'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', TAMANIO_MAXIMO_COMPROBANTE))

    # Cookies de sesión
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    """Desarrollo local"""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(RAIZ, 'instance', 'sistcoop179.db')
    )

    # Clave fija sólo para desarrollo, para no tener que configurar nada
    # antes de levantar el proyecto. En producción no se usa: ProductionConfig
    # no arranca si no hay una clave propia en el .env.
    SECRET_KEY = os.getenv('SECRET_KEY') or 'clave-de-desarrollo-no-usar-en-produccion'


class ProductionConfig(Config):
    """Producción"""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SESSION_COOKIE_SECURE = True

    @classmethod
    def validar(cls):
        """Corta el arranque si falta configuración importante.

        Preferimos que el sistema no levante antes que levantarlo con una
        clave que está escrita en el repositorio.
        """
        faltan = []
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            faltan.append('SECRET_KEY (mínimo 32 caracteres)')
        if not cls.SQLALCHEMY_DATABASE_URI:
            faltan.append('DATABASE_URL')

        if faltan:
            raise ConfigInvalida(
                'Faltan variables de entorno para arrancar en producción: '
                + ', '.join(faltan) + '. Ver .env.example.'
            )


class TestingConfig(Config):
    """Pruebas automáticas"""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'clave-de-pruebas'
    UPLOAD_FOLDER = os.path.join(RAIZ, 'instance', 'comprobantes_test')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
