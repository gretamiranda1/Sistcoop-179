from app.extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

ROLES_LEGIBLES = {
    'admin': 'Administración',
    'asistente': 'Asistente',
    'tesorera': 'Tesorería',
    'preceptoria': 'Preceptoría',
}


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    rol = db.Column(db.String(20), nullable=False)  # admin, asistente, tesorera, preceptoria
    activo = db.Column(db.Boolean, default=True)
    ultimo_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # El valor admitido sale de ROLES_LEGIBLES: no hay una segunda lista
    # escrita a mano acá, sólo el SQL armado a partir de ese diccionario.
    __table_args__ = (
        db.CheckConstraint(
            'rol IN ({})'.format(', '.join(repr(v) for v in ROLES_LEGIBLES)),
            name='ck_usuarios_rol'
        ),
    )

    def set_password(self, password):
        """Hashear la contraseña antes de guardarla"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar si la contraseña es correcta"""
        return check_password_hash(self.password_hash, password)
    
    def is_active(self):
        """Verificar si el usuario está activo"""
        return self.activo
    
    def __repr__(self):
        return '<Usuario {}>'.format(self.username)