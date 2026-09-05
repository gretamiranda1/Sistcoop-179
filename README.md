# SistCoop 179

Sistema web de gestión contable para la Asociación Cooperadora del
ISFT N° 179 "Dr. Carlos Pellegrini".

Desarrollado por el equipo **CodeAr 179** en el marco de las Prácticas
Profesionalizantes de la Tecnicatura Superior en Análisis de Sistemas.

---

## 1. Qué hace

Digitaliza el circuito de pagos, recibos y egresos de la Cooperadora, que hoy
se sostiene con correo electrónico, planillas de Excel y registros en papel.

Contempla cuatro roles: **Aportante** (portal público de carga y consulta),
**Cooperadora** (validación, recibos, egresos, fondos), **Preceptoría**
(consulta de estado de pago) y **Tesorería** (conciliación y reportes).

## 2. Estado por incremento

| Incremento | Alcance | Estado |
| ---------- | ------- | ------ |
| 1 | Diseño técnico, modelo de datos y arquitectura 
| 2 | Módulo Aportante: carga de pagos y comprobantes |
| 3 | Módulo Cooperadora y Preceptoría 
| 4 | Módulo Tesorería, conciliación y reportes 
| 5 | Aceptación, capacitación y despliegue 


## 3. Stack tecnológico

| Capa | Tecnología |
| ---- | ---------- |
| Backend | Python 3.12 + Flask 2.3 |
| Base de datos | PostgreSQL (producción) · SQLite (desarrollo) |
| Acceso a datos | SQLAlchemy 2 + Flask-SQLAlchemy |
| Migraciones | Flask-Migrate (Alembic) |
| Sesiones y permisos | Flask-Login |
| Protección CSRF | Flask-WTF |
| Frontend | Jinja2 + Bootstrap 5 **servido localmente** + JavaScript propio |
| Gráficos | Chart.js local (a incorporar en Incremento 4) |
| Reportes | openpyxl (.xlsx) y ReportLab (.pdf) (Incremento 4) |
| Servidor | Gunicorn + Nginx |


## 4. Estructura del repositorio

```
sistcoop179/
├── app/
│   ├── modelos/           Las TABLAS. Describen la base y responden
│   │                      consultas. No modifican nada
│   ├── servicios/         Las REGLAS. Acá se modifica todo: alta,
│   │                      verificación y rechazo de pagos, reparto grupal,
│   │                      saldos, fondos y auditoría
│   ├── controladores/     Las RUTAS por blueprint: autenticación,
│   │                      aportantes, administración, principal
│   ├── utilidades/        Funciones sueltas sin base de datos: validaciones
│   │                      (DNI/CUIT/fechas), archivos, límite de peticiones
│   ├── vistas/            Plantillas Jinja2 por rol (admin/, aportante/,
│   │                      auth/, errores/) + base.html + _componentes.html
│   ├── static/
│   │   ├── css/           Hoja de estilos propia
│   │   ├── js/            JavaScript propio
│   │   └── vendor/        Bootstrap 5 y Bootstrap Icons (locales)
│   ├── data/              Datos de referencia (carreras del instituto)
│   ├── config.py          Configuración por entorno
│   └── extensions.py      Instancias de las extensiones de Flask
├── scripts/               init_db, migrar_incremento2, agregar_carreras,
│                          limpiar_datos, prueba_flujo
├── instance/              Base SQLite y comprobantes subidos (NO versionado)
├── docs/                  Guía del código, bitácoras, pruebas manuales e
│                          informes de avance
├── run.py                 Servidor de desarrollo
├── requirements.txt
├── .env.example
├── requirements-prod.txt
└── .gitignore
```

En desarrollo se instala `requirements.txt`; en el servidor, `requirements-prod.txt`.

## 5. Equipo

CodeAr 179 — Prácticas Profesionalizantes 2026.

| Integrante | Área |
| ---------- | ---- |
| Silvera, Santiago | Gestión, documentación y frontend |
| Vercelli, Brenda | Backend, base de datos y frontend |
| Sanoguera, Agustín | Backend y base de datos |
| Wainberg, Evelyn | Análisis y pruebas |
| Miranda, Greta | Análisis y pruebas |

Los roles indican el área principal de cada uno: todo el equipo participa
del desarrollo.
