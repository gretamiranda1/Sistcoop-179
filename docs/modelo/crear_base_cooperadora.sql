-- ============================================================
--  Sistema Cooperadora — modelo consolidado
--  PostgreSQL.  Las tablas están en orden de dependencia:
--  se puede correr el archivo de arriba a abajo.
-- ============================================================

-- ---------- 1 · Núcleo institucional ------------------------

CREATE TABLE usuarios (
    id            SERIAL       PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre        VARCHAR(100) NOT NULL,
    apellido      VARCHAR(100) NOT NULL,
    rol           VARCHAR(20)  NOT NULL,
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    ultimo_login  TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT ck_usuarios_rol
        CHECK (rol IN ('admin','asistente','tesorera','preceptoria'))
);

CREATE TABLE carreras (
    id         SERIAL       PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL UNIQUE,
    activo     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP    NOT NULL DEFAULT now()
);

-- Una fila por año dictado. Reemplaza la columna de texto "1°,2°,3°".
CREATE TABLE carrera_anios (
    carrera_id INTEGER  NOT NULL REFERENCES carreras(id),
    anio       SMALLINT NOT NULL,
    PRIMARY KEY (carrera_id, anio),
    CONSTRAINT ck_carrera_anios_rango CHECK (anio BETWEEN 1 AND 7)
);

CREATE TABLE ejercicios (
    id             SERIAL        PRIMARY KEY,
    anio           SMALLINT      NOT NULL UNIQUE,
    cuota          NUMERIC(12,2) NOT NULL,
    fecha_asamblea DATE,
    activo         BOOLEAN       NOT NULL DEFAULT TRUE,
    cerrado        BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT ck_ejercicios_cuota CHECK (cuota > 0)
);

-- Sólo puede haber un ejercicio vigente a la vez.
CREATE UNIQUE INDEX uq_ejercicio_vigente
    ON ejercicios ((TRUE)) WHERE activo AND NOT cerrado;

-- ---------- 2 · Aportantes ----------------------------------
-- Una sola tabla: la persona es la misma sin importar qué formulario
-- llene. Lo que cambia entre "cuota" y "aporte adicional" es el PAGO,
-- no el aportante: eso vive en pagos.tipo.

CREATE TABLE aportantes (
    id         SERIAL       PRIMARY KEY,
    dni        VARCHAR(15)  NOT NULL UNIQUE,
    nombre     VARCHAR(100) NOT NULL,
    apellido   VARCHAR(100) NOT NULL,
    cuit       VARCHAR(13),
    carrera_id INTEGER,
    anio       SMALLINT,
    email      VARCHAR(120),
    telefono   VARCHAR(30),
    activo     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at TIMESTAMP    NOT NULL DEFAULT now(),
    -- carrera y año son opcionales: quien hace un aporte adicional puede no
    -- estar ligado a ninguna carrera. Si se cargan, el año tiene que existir
    -- en esa carrera.
    CONSTRAINT fk_aportantes_carrera_anio
        FOREIGN KEY (carrera_id, anio) REFERENCES carrera_anios(carrera_id, anio)
);

-- ---------- 3 · Entrada de dinero ---------------------------

-- Única dueña del código de transacción y del hash del comprobante.
CREATE TABLE operaciones (
    id                 SERIAL        PRIMARY KEY,
    medio_pago         VARCHAR(20)   NOT NULL,
    codigo_transaccion VARCHAR(100)  UNIQUE,
    hash_comprobante   VARCHAR(64)   UNIQUE,
    comprobante_nombre VARCHAR(255),
    comprobante_ruta   VARCHAR(255),
    importe            NUMERIC(12,2) NOT NULL,
    fecha              DATE          NOT NULL,
    -- CUIT de quien efectivamente hizo la transferencia. Va acá y no en el
    -- pago porque sirve para conciliar contra el extracto del banco: quien
    -- pone la plata puede no ser el aportante (una empresa, un familiar).
    cuit_ordenante     VARCHAR(13),
    alcance            VARCHAR(12)   NOT NULL,
    created_at         TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT ck_operaciones_medio   CHECK (medio_pago IN ('transferencia','deposito','efectivo')),
    CONSTRAINT ck_operaciones_alcance CHECK (alcance IN ('individual','grupal')),
    CONSTRAINT ck_operaciones_importe CHECK (importe > 0),
    -- una transferencia siempre trae código; el efectivo, no
    CONSTRAINT ck_operaciones_codigo CHECK (
        medio_pago = 'efectivo' OR codigo_transaccion IS NOT NULL)
);

CREATE TABLE fondos (
    id         SERIAL        PRIMARY KEY,
    nombre     VARCHAR(100)  NOT NULL,
    tipo       VARCHAR(20)   NOT NULL,
    saldo      NUMERIC(14,2) NOT NULL DEFAULT 0,
    activo     BOOLEAN       NOT NULL DEFAULT TRUE,
    carrera_id INTEGER       REFERENCES carreras(id),
    created_at TIMESTAMP     NOT NULL DEFAULT now(),
    updated_at TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT ck_fondos_tipo CHECK (tipo IN ('capital','carrera','evento')),
    CONSTRAINT uq_fondos_carrera_tipo UNIQUE (carrera_id, tipo)
);

CREATE TABLE pagos_grupales (
    id                 SERIAL      PRIMARY KEY,
    codigo_seguimiento VARCHAR(20) NOT NULL UNIQUE,
    operacion_id       INTEGER     NOT NULL UNIQUE REFERENCES operaciones(id),
    estado             VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    usuario_id         INTEGER     REFERENCES usuarios(id),
    created_at         TIMESTAMP   NOT NULL DEFAULT now(),
    CONSTRAINT ck_pg_estado CHECK (estado IN ('pendiente','verificado','rechazado'))
);

CREATE TABLE solicitudes_fondo (
    id                 SERIAL        PRIMARY KEY,
    codigo_seguimiento VARCHAR(20)   NOT NULL UNIQUE,
    responsable        VARCHAR(120)  NOT NULL,
    contacto           VARCHAR(120)  NOT NULL,
    curso              VARCHAR(50),
    tipo               VARCHAR(20)   NOT NULL,
    concepto           VARCHAR(200)  NOT NULL,
    importe_estimado   NUMERIC(14,2),
    importe_aprobado   NUMERIC(14,2),
    fecha_estimada     DATE,
    justificacion      TEXT          NOT NULL,
    estado             VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    resolucion         TEXT,
    fecha_resolucion   TIMESTAMP,
    carrera_id         INTEGER       REFERENCES carreras(id),
    fondo_id           INTEGER       REFERENCES fondos(id),
    resuelta_por_id    INTEGER       REFERENCES usuarios(id),
    created_at         TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT ck_sol_tipo   CHECK (tipo   IN ('fondos','evento','viaje')),
    CONSTRAINT ck_sol_estado CHECK (estado IN ('pendiente','aprobada','rechazada')),
    -- si está aprobada, tiene que decir cuánto y contra qué fondo
    CONSTRAINT ck_sol_aprobada CHECK (
        estado <> 'aprobada'
     OR (importe_aprobado IS NOT NULL AND fondo_id IS NOT NULL))
);

CREATE TABLE pagos (
    id                 SERIAL        PRIMARY KEY,
    codigo_seguimiento VARCHAR(20)   NOT NULL UNIQUE,
    tipo               VARCHAR(30)   NOT NULL,
    importe            NUMERIC(12,2) NOT NULL,
    fecha              DATE          NOT NULL,
    estado             VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    solicita_libreta   BOOLEAN       NOT NULL DEFAULT FALSE,
    observaciones      TEXT,
    created_at         TIMESTAMP     NOT NULL DEFAULT now(),
    updated_at         TIMESTAMP     NOT NULL DEFAULT now(),
    operacion_id       INTEGER       UNIQUE REFERENCES operaciones(id),
    aportante_id       INTEGER       NOT NULL REFERENCES aportantes(id),
    fondo_id           INTEGER       NOT NULL REFERENCES fondos(id),
    ejercicio_id       INTEGER       NOT NULL REFERENCES ejercicios(id),
    usuario_id         INTEGER       REFERENCES usuarios(id),
    pago_grupal_id     INTEGER       REFERENCES pagos_grupales(id),
    -- 'cuota_grupal' sale de la lista: un pago de cuota que viene de un
    -- reparto se reconoce porque tiene pago_grupal_id cargado.
    CONSTRAINT ck_pagos_tipo    CHECK (tipo IN ('cuota','adicional','aporte_carrera','libreta_duplicado')),
    CONSTRAINT ck_pagos_estado  CHECK (estado IN ('pendiente','verificado','rechazado','anulado')),
    CONSTRAINT ck_pagos_importe CHECK (importe > 0),
    -- o entra por su propia operación bancaria, o viene de un reparto grupal
    CONSTRAINT ck_pagos_origen CHECK (
        (operacion_id IS NOT NULL AND pago_grupal_id IS NULL)
     OR (operacion_id IS NULL     AND pago_grupal_id IS NOT NULL)),
    -- un aportante no puede repetirse dentro del mismo pago grupal
    CONSTRAINT uq_pagos_grupal_aportante UNIQUE (pago_grupal_id, aportante_id)
);

-- ---------- 4 · Verificación y recibos ----------------------

CREATE TABLE verificaciones (
    id             SERIAL      PRIMARY KEY,
    resultado      VARCHAR(20) NOT NULL,
    motivo         TEXT,
    fecha          TIMESTAMP   NOT NULL DEFAULT now(),
    pago_id        INTEGER     REFERENCES pagos(id),
    pago_grupal_id INTEGER     REFERENCES pagos_grupales(id),
    usuario_id     INTEGER     NOT NULL REFERENCES usuarios(id),
    CONSTRAINT ck_ver_resultado CHECK (resultado IN ('verificado','rechazado')),
    -- apunta a un pago individual o a uno grupal, nunca a los dos
    CONSTRAINT ck_ver_objeto CHECK (
        (pago_id IS NOT NULL AND pago_grupal_id IS NULL)
     OR (pago_id IS NULL     AND pago_grupal_id IS NOT NULL)),
    -- un rechazo tiene que explicarse
    CONSTRAINT ck_ver_motivo CHECK (
        resultado <> 'rechazado' OR motivo IS NOT NULL)
);

CREATE TABLE recibos (
    id            SERIAL        PRIMARY KEY,
    letra         CHAR(1)       NOT NULL,
    serie         SMALLINT      NOT NULL,
    numero        INTEGER       NOT NULL,
    fecha_emision TIMESTAMP     NOT NULL DEFAULT now(),
    concepto      VARCHAR(200),
    razon_social  VARCHAR(200)  NOT NULL,
    documento     VARCHAR(15)   NOT NULL,
    importe       NUMERIC(12,2) NOT NULL,
    pago_id       INTEGER       NOT NULL UNIQUE REFERENCES pagos(id),
    CONSTRAINT ck_recibos_letra CHECK (letra IN ('A','B','C','X')),
    CONSTRAINT uq_recibos_numeracion UNIQUE (letra, serie, numero)
);

-- La entrega de la libreta NO vive en saldos_aportantes: esa tabla es una
-- caché que se puede reconstruir desde los pagos, y un hecho real (se
-- entregó, tal día, tal persona) no puede vivir en algo reconstruible.
CREATE TABLE libretas (
    id               SERIAL      PRIMARY KEY,
    tipo             VARCHAR(12) NOT NULL,
    fecha_entrega    TIMESTAMP   NOT NULL DEFAULT now(),
    observaciones    TEXT,
    aportante_id     INTEGER     NOT NULL REFERENCES aportantes(id),
    ejercicio_id     INTEGER     NOT NULL REFERENCES ejercicios(id),
    entregada_por_id INTEGER     NOT NULL REFERENCES usuarios(id),
    -- el duplicado se cobra: apunta al pago de tipo libreta_duplicado
    pago_id          INTEGER     UNIQUE REFERENCES pagos(id),
    CONSTRAINT ck_libretas_tipo CHECK (tipo IN ('original','duplicado')),
    CONSTRAINT ck_libretas_duplicado CHECK (
        tipo <> 'duplicado' OR pago_id IS NOT NULL)
);

-- Una sola libreta original por persona y ejercicio. Los duplicados no se
-- limitan: cada uno tiene su pago.
CREATE UNIQUE INDEX uq_libreta_original
    ON libretas (aportante_id, ejercicio_id) WHERE tipo = 'original';

-- ---------- 5 · Datos derivados -----------------------------

CREATE TABLE saldos_aportantes (
    id                SERIAL        PRIMARY KEY,
    aportante_id      INTEGER       NOT NULL REFERENCES aportantes(id),
    ejercicio_id      INTEGER       NOT NULL REFERENCES ejercicios(id),
    pagado            NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldo_pendiente   NUMERIC(12,2) NOT NULL DEFAULT 0,
    updated_at        TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT uq_saldos_aportante_ejercicio UNIQUE (aportante_id, ejercicio_id)
);

CREATE TABLE movimientos_fondo (
    id                SERIAL        PRIMARY KEY,
    monto             NUMERIC(14,2) NOT NULL,
    saldo_anterior    NUMERIC(14,2),
    saldo_resultante  NUMERIC(14,2) NOT NULL,
    motivo            VARCHAR(150),
    origen            VARCHAR(20)   NOT NULL,
    fondo_id          INTEGER       NOT NULL REFERENCES fondos(id),
    pago_id           INTEGER       REFERENCES pagos(id),
    solicitud_id      INTEGER       REFERENCES solicitudes_fondo(id),
    usuario_id        INTEGER       REFERENCES usuarios(id),
    created_at        TIMESTAMP     NOT NULL DEFAULT now(),
    CONSTRAINT ck_mov_origen CHECK (origen IN ('pago','solicitud','ajuste','apertura')),
    -- la clave foránea cargada tiene que coincidir con el origen declarado
    CONSTRAINT ck_mov_coherencia CHECK (
        (origen = 'pago'      AND pago_id      IS NOT NULL AND solicitud_id IS NULL)
     OR (origen = 'solicitud' AND solicitud_id IS NOT NULL AND pago_id      IS NULL)
     OR (origen IN ('ajuste','apertura') AND pago_id IS NULL AND solicitud_id IS NULL))
);

-- ---------- 6 · Trazabilidad --------------------------------

CREATE TABLE auditoria (
    id          SERIAL       PRIMARY KEY,
    usuario     VARCHAR(50)  NOT NULL,
    accion      VARCHAR(100) NOT NULL,
    tabla       VARCHAR(50),
    registro_id INTEGER,
    detalle     JSONB,
    ip          VARCHAR(45),
    user_agent  VARCHAR(255),
    created_at  TIMESTAMP    NOT NULL DEFAULT now()
);

-- ---------- 7 · Índices de consulta -------------------------

CREATE INDEX ix_pagos_aportante   ON pagos (aportante_id);
CREATE INDEX ix_pagos_ejercicio   ON pagos (ejercicio_id);
CREATE INDEX ix_pagos_estado      ON pagos (estado);
CREATE INDEX ix_pagos_fecha       ON pagos (fecha);
CREATE INDEX ix_ver_pago          ON verificaciones (pago_id);
CREATE INDEX ix_mov_fondo_fecha   ON movimientos_fondo (fondo_id, created_at);
CREATE INDEX ix_aportantes_apenom ON aportantes (apellido, nombre);
CREATE INDEX ix_libretas_aportante ON libretas (aportante_id, ejercicio_id);

-- ---------- 8 · Sólo un fondo de capital activo -------------

CREATE UNIQUE INDEX uq_fondo_capital_activo
    ON fondos ((TRUE)) WHERE tipo = 'capital' AND activo;
