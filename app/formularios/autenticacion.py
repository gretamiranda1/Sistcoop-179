"""Formulario de acceso al panel administrativo.

Hoy el login no controla formato de usuario/contraseña: cualquier valor se
manda tal cual contra la base, y el mensaje de error es siempre el mismo
("Usuario o contraseña incorrectos.") para no confirmarle a quien prueba
qué usuarios existen. Este formulario no le agrega validadores nuevos a eso:
sólo junta los dos campos bajo un FlaskForm, para el mismo manejo de CSRF
que el resto de app/formularios/.
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField


class FormularioLogin(FlaskForm):
    username = StringField()
    password = PasswordField()
