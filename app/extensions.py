from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Sacamos Flask-CORS: todas las pantallas se sirven desde esta misma
# aplicación, no hay ningún cliente en otro dominio que consuma las rutas.

login_manager.login_view = 'autenticacion.login'
login_manager.login_message = 'Iniciá sesión para acceder a esta sección.'
login_manager.login_message_category = 'warning'
