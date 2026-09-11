-- ============================================================
--  Pruebas de las restricciones del modelo consolidado
--  Correr DESPUÉS de crear_base_cooperadora.sql, sobre una base vacía.
--  Los INSERT de la parte 1 tienen que entrar.
--  Los diez de la parte 2 tienen que fallar, todos.
-- ============================================================

-- ---------- Parte 1 · datos válidos -------------------------
INSERT INTO usuarios (id,username,email,password_hash,nombre,apellido,rol)
     VALUES (1,'ana','ana@coop.edu','hash','Ana','Paz','tesorera');

INSERT INTO carreras (id,nombre) VALUES (1,'Analista de Sistemas');
INSERT INTO carrera_anios (carrera_id,anio) VALUES (1,1),(1,2),(1,3);

INSERT INTO ejercicios (id,anio,cuota) VALUES (1,2026,15000.50);

-- Un aportante ligado a una carrera (paga la cuota) y otro que no lo está
-- (hace un aporte adicional). Es la misma tabla: lo que cambia es el pago.
INSERT INTO aportantes (id,dni,nombre,apellido,carrera_id,anio)
     VALUES (1,'30111222','Luz','Diaz',1,2);
INSERT INTO aportantes (id,dni,nombre,apellido,cuit)
     VALUES (2,'27333444','Sur','SRL','30-27333444-9');

INSERT INTO fondos (id,nombre,tipo) VALUES (1,'Fondo de capital','capital');

INSERT INTO operaciones (id,medio_pago,codigo_transaccion,importe,fecha,alcance)
     VALUES (1,'transferencia','TX-001',15000.50,'2026-03-01','individual');

INSERT INTO pagos (id,codigo_seguimiento,tipo,importe,fecha,
                   operacion_id,aportante_id,fondo_id,ejercicio_id,usuario_id)
     VALUES (1,'SC-A3F9K2XY','cuota',15000.50,'2026-03-01',1,1,1,1,1);

-- Al cargar los id a mano, las secuencias no avanzan solas: hay que ponerlas
-- al día o el próximo INSERT sin id choca contra la clave primaria.
SELECT setval(pg_get_serial_sequence('usuarios','id'),    (SELECT max(id) FROM usuarios));
SELECT setval(pg_get_serial_sequence('carreras','id'),    (SELECT max(id) FROM carreras));
SELECT setval(pg_get_serial_sequence('ejercicios','id'),  (SELECT max(id) FROM ejercicios));
SELECT setval(pg_get_serial_sequence('aportantes','id'),  (SELECT max(id) FROM aportantes));
SELECT setval(pg_get_serial_sequence('fondos','id'),      (SELECT max(id) FROM fondos));
SELECT setval(pg_get_serial_sequence('operaciones','id'), (SELECT max(id) FROM operaciones));
SELECT setval(pg_get_serial_sequence('pagos','id'),       (SELECT max(id) FROM pagos));

-- La cuota se guardó con los centavos intactos:
SELECT cuota FROM ejercicios WHERE id = 1;   -- 15000.50

-- ---------- Parte 2 · lo que la base tiene que rechazar -----

-- 1 · el mismo comprobante bancario, cargado dos veces
INSERT INTO operaciones (medio_pago,codigo_transaccion,importe,fecha,alcance)
     VALUES ('transferencia','TX-001',100,'2026-03-02','grupal');

-- 2 · un pago que entra por su operación y por un reparto grupal a la vez
INSERT INTO pagos (codigo_seguimiento,tipo,importe,fecha,
                   operacion_id,pago_grupal_id,aportante_id,fondo_id,ejercicio_id)
     VALUES ('SC-2','cuota',10,'2026-03-01',1,1,1,1,1);

-- 3 · un pago que no entra por ninguna de las dos vías
INSERT INTO pagos (codigo_seguimiento,tipo,importe,fecha,aportante_id,fondo_id,ejercicio_id)
     VALUES ('SC-3','cuota',10,'2026-03-01',1,1,1);

-- 4 · un aportante en 5° año, de una carrera que sólo dicta tres
INSERT INTO aportantes (dni,nombre,apellido,carrera_id,anio)
     VALUES ('40555666','Eze','Roa',1,5);

-- 5 · un segundo aportante con un DNI ya cargado
INSERT INTO aportantes (dni,nombre,apellido,cuit)
     VALUES ('30111222','Otro','Igual','30-30111222-9');

-- 6 · un segundo ejercicio vigente
INSERT INTO ejercicios (anio,cuota) VALUES (2027,20000);

-- 7 · una verificación rechazada que no explica por qué
INSERT INTO verificaciones (resultado,pago_id,usuario_id) VALUES ('rechazado',1,1);

-- 8 · una operación con importe negativo
INSERT INTO operaciones (medio_pago,codigo_transaccion,importe,fecha,alcance)
     VALUES ('transferencia','TX-009',-5,'2026-03-02','individual');

-- 9 · un movimiento que dice venir de un pago, sin decir de cuál
INSERT INTO movimientos_fondo (monto,saldo_resultante,origen,fondo_id)
     VALUES (100,100,'pago',1);

-- 10 · una solicitud aprobada sin importe aprobado ni fondo
INSERT INTO solicitudes_fondo (codigo_seguimiento,responsable,contacto,tipo,
                               concepto,justificacion,estado)
     VALUES ('SF-1','Juan','j@j.com','evento','Acto de fin de año',
             'Se realiza todos los años','aprobada');

-- 11 · un duplicado de libreta sin el pago que lo respalda
INSERT INTO libretas (tipo,aportante_id,ejercicio_id,entregada_por_id)
     VALUES ('duplicado',1,1,1);

-- 12 · una segunda libreta original del mismo año para la misma persona
--      (la primera entra bien; ésta tiene que rebotar)
INSERT INTO libretas (tipo,aportante_id,ejercicio_id,entregada_por_id)
     VALUES ('original',1,1,1);
INSERT INTO libretas (tipo,aportante_id,ejercicio_id,entregada_por_id)
     VALUES ('original',1,1,1);
