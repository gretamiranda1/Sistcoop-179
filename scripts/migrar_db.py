from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrar():
    app = create_app('development')
    with app.app_context():
        # Crear tabla saldos_aportantes
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS saldos_aportantes (
                id INTEGER PRIMARY KEY,
                aportante_id INTEGER NOT NULL,
                ejercicio_id INTEGER NOT NULL,
                cuota_total DECIMAL(10,2) NOT NULL,
                pagado DECIMAL(10,2) DEFAULT 0,
                saldo_pendiente DECIMAL(10,2),
                estado VARCHAR(20) DEFAULT 'pendiente',
                libreta_entregada BOOLEAN DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aportante_id) REFERENCES aportantes(id),
                FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id)
            )
        '''))
        print("✅ Tabla 'saldos_aportantes' creada")

        # Crear tabla pagos_grupales
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS pagos_grupales (
                id INTEGER PRIMARY KEY,
                codigo_transaccion VARCHAR(100) UNIQUE NOT NULL,
                importe_total DECIMAL(10,2) NOT NULL,
                fecha DATE NOT NULL,
                comprobante_url VARCHAR(255),
                estado VARCHAR(20) DEFAULT 'pendiente',
                usuario_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        '''))
        print("✅ Tabla 'pagos_grupales' creada")

        # Crear tabla pagos_grupales_detalle
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS pagos_grupales_detalle (
                id INTEGER PRIMARY KEY,
                pago_grupal_id INTEGER NOT NULL,
                aportante_id INTEGER NOT NULL,
                monto_asignado DECIMAL(10,2) NOT NULL,
                estado VARCHAR(20) DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pago_grupal_id) REFERENCES pagos_grupales(id),
                FOREIGN KEY (aportante_id) REFERENCES aportantes(id)
            )
        '''))
        print("✅ Tabla 'pagos_grupales_detalle' creada")

        db.session.commit()
        print("🎉 Migración completada con éxito")

if __name__ == '__main__':
    migrar()