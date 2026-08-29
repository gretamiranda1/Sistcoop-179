from app.extensions import db
from datetime import datetime

class Carrera(db.Model):
    __tablename__ = 'carreras'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    anios = db.Column(db.String(20), default='1°,2°,3°')
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    aportantes = db.relationship('Aportante', backref='carrera', lazy='dynamic')
    fondos = db.relationship('Fondo', backref='carrera', lazy='dynamic')
    
    @classmethod
    def get_carreras_activas(cls):
        """Obtener todas las carreras activas"""
        return cls.query.filter_by(activo=True).order_by(cls.nombre).all()
    
    def __repr__(self):
        return '<Carrera {}>'.format(self.nombre)