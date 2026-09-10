"""Reglas de negocio del pago grupal.

Un pago grupal es UNA transferencia que cubre a VARIAS personas: una familia
con dos hermanos, o un grupo de compañeros que junta la plata y manda todo
junto.

Se guarda en tres lugares:

  PagoGrupal          la transferencia (una sola fila)
  PagoGrupalDetalle   cuánto le tocó a cada persona
  Pago                el asiento contable de cada persona (uno por persona)

Igual que en el pago individual, acá no se acredita nada: todo queda
pendiente hasta que la Cooperadora verifique la transferencia.
"""

from app.extensions import db
from app.modelos.ejercicios import Ejercicio
from app.modelos.pagos import Pago, generar_codigo
from app.modelos.pagos_grupales import PagoGrupal, PagoGrupalDetalle
from app.servicios import auditoria, fondos, pagos as servicio_pagos, saldos
from app.servicios.pagos import ErrorDeCarga
from app.utilidades import validaciones

MINIMO_PERSONAS = 2


# ============================================
# PERSONAS DEL FORMULARIO
# ============================================

def normalizar_personas(filas):
    """Limpia y controla la lista de personas. Devuelve (personas, errores).

    Las filas vacías se saltean: el formulario deja agregar y sacar filas, y
    es normal que quede alguna sin completar.
    """
    personas = []
    errores = []
    dnis_ya_vistos = []
    numero = 0

    for fila in filas:
        numero = numero + 1

        dni = (fila.get('dni') or '').strip()

        if not dni:
            continue

        if not validaciones.validar_dni(dni):
            errores.append(
                'Persona {}: DNI inválido. Ingrese únicamente números.'.format(numero)
            )
            continue

        if dni in dnis_ya_vistos:
            errores.append('Persona {}: el DNI {} está repetido en este mismo '
                           'pago.'.format(numero, dni))
            continue

        nombre = (fila.get('nombre') or '').strip()
        apellido = (fila.get('apellido') or '').strip()

        if not nombre or not apellido:
            errores.append(
                'Persona {}: faltan el nombre y/o el apellido.'.format(numero)
                )
            continue

        carrera_id = fila.get('carrera_id')
        if not carrera_id:
            errores.append(
                'Persona {}: falta la carrera.'.format(numero)
            )
            continue

        anio = fila.get('anio')
        if not anio:
            errores.append(
                'Persona {}: falta el año.'.format(numero)
            )
            continue

        if not validaciones.validar_nombre(nombre):
            errores.append(
                'Persona {}: el nombre solo admite caracteres alfabéticos.'.format(numero)
            )
            continue

        if not validaciones.validar_nombre(apellido):
            errores.append(
                'Persona {}: el apellido solo admite caracteres alfabéticos.'.format(numero)
            )
            continue
        
        dnis_ya_vistos.append(dni)

        personas.append({
            'dni': dni,
            'nombre': nombre,
            'apellido': apellido,
            'carrera_id': carrera_id,
            'anio': anio,
            'solicita_libreta': bool(fila.get('solicita_libreta')),
        })

    if len(personas) < MINIMO_PERSONAS and not errores:
        errores.append('Un pago grupal tiene que incluir al menos 2 personas con '
                       'DNI distintos.')

    return personas, errores


# ============================================
# CÓMO SE REPARTE EL IMPORTE
# ============================================
#
# A nadie se le asigna más de lo que le falta pagar. Lo que sobra después de
# aplicar ese tope queda como "excedente" y se registra como aporte adicional
# a nombre de la primera persona del grupo: la plata entró al banco igual, y
# si no la asentáramos, el fondo mostraría menos dinero que el extracto.

def repartir_en_partes_iguales(personas, importe_total):
    """Reparte por igual entre quienes todavía tengan cuota pendiente.

    A quien ya la completó no se le asigna nada. Devuelve (personas, excedente):
    a cada persona se le agrega la clave 'monto_asignado'.
    """
    con_deuda = []
    for persona in personas:
        if persona['falta'] > 0:
            con_deuda.append(persona)

    if not con_deuda:
        raise ErrorDeCarga('Todas las personas de este pago ya tienen la cuota '
                           'completa. Si el aporte es para otro concepto, usá '
                           '"Aporte adicional".')

    total_faltante = 0
    for persona in con_deuda:
        total_faltante = total_faltante + persona['falta']

    # No se reparte más de lo que falta entre todos
    a_repartir = min(importe_total, total_faltante)
    centavos_a_repartir = round(a_repartir * 100)
    cantidad = len(con_deuda)
    centavos_base = centavos_a_repartir // cantidad
    centavos_sobrantes = centavos_a_repartir % cantidad

    asignado = 0.0
    for indice, persona in enumerate(con_deuda):
        centavos_persona = centavos_base + (1 if indice < centavos_sobrantes else 0)
        parte = round(centavos_persona / 100, 2)
        monto = min(parte, persona['falta'])
        persona['monto_asignado'] = monto
        asignado = round(asignado + monto, 2)

    for persona in personas:
        if persona['falta'] <= 0:
            persona['monto_asignado'] = 0.0

    excedente = round(importe_total - asignado, 2)
    return personas, max(excedente, 0.0)


def repartir_a_mano(personas, importe_total, montos):
    """Reparte según lo que indicó quien carga el pago.

    Dos topes: la suma no puede superar lo que realmente se transfirió, y a
    nadie se le puede asignar más de lo que le falta pagar.
    """
    declarados = []
    for monto in montos:
        try:
            declarados.append(round(float(monto), 2))
        except (ValueError, TypeError):
            declarados.append(0.0)

    for monto in declarados:
        if monto < 0:
            raise ErrorDeCarga('Los montos asignados no pueden ser negativos.')

    suma = round(sum(declarados), 2)
    if suma > round(importe_total, 2) + 0.01:
        raise ErrorDeCarga('Estás repartiendo ${:,.2f} pero transferiste ${:,.2f}. '
                           'La suma no puede superar el importe transferido.'.format(
                               suma, importe_total))

    asignado = 0.0
    for i in range(len(personas)):
        if i < len(declarados):
            monto = min(declarados[i], personas[i]['falta'])
        else:
            monto = 0.0
        personas[i]['monto_asignado'] = monto
        asignado = round(asignado + monto, 2)

    if asignado == 0:
        raise ErrorDeCarga('Tenés que asignarle un monto a por lo menos una persona.')

    excedente = round(importe_total - asignado, 2)
    return personas, max(excedente, 0.0)


# ============================================
# ALTA DEL PAGO GRUPAL
# ============================================

def procesar_pago_grupal(data, ip=None, user_agent=None):
    """Registra una transferencia grupal y su reparto.

    Devuelve (pago_grupal, resumen).
    """
    errores = []

    importe_ok, mensaje = validaciones.validar_importe(data.get('importe_total'))
    if not importe_ok:
        errores.append(mensaje)
        importe_total = 0
    else:
        importe_total = round(float(data['importe_total']), 2)

    if not data.get('fecha'):
        errores.append('La fecha de la transferencia es obligatoria.')
    else:
        fecha_ok, mensaje = validaciones.validar_fecha_transferencia(data['fecha'])
        if not fecha_ok:
            errores.append(mensaje)

    errores = errores + servicio_pagos.validar_operacion_y_comprobante(data)

    personas, errores_personas = normalizar_personas(data.get('personas') or [])
    errores = errores + errores_personas

    if errores:
        raise ErrorDeCarga(errores)

    ejercicio = Ejercicio.get_ejercicio_vigente()
    if not ejercicio:
        raise ErrorDeCarga('No hay un ejercicio abierto. Avisale a la Cooperadora.')

    fondo, error_fondo = fondos.buscar_fondo('capital')
    if error_fondo:
        raise ErrorDeCarga(error_fondo)

    # A cada persona le agregamos su aportante, su saldo y cuánto le falta.
    # Lo que ya tiene cargado y sin verificar también se descuenta, para no
    # pedirle dos veces lo mismo.
    for persona in personas:
        aportante = servicio_pagos.buscar_o_crear_aportante(persona)
        saldo = saldos.buscar_o_crear_saldo(aportante.id, ejercicio.id, ejercicio.cuota)

        persona['aportante'] = aportante
        persona['saldo'] = saldo
        persona['falta'] = saldo.falta_pagar

    if data.get('tipo_distribucion') == 'manual':
        personas, excedente = repartir_a_mano(personas, importe_total,
                                              data.get('montos') or [])
    else:
        personas, excedente = repartir_en_partes_iguales(personas, importe_total)

    fecha = validaciones.texto_a_fecha(data.get('fecha'))

    pago_grupal = PagoGrupal(
        codigo_seguimiento=generar_codigo('SG'),
        codigo_transaccion=data['codigo_transaccion'],
        importe_total=importe_total,
        fecha=fecha,
        comprobante_nombre=data.get('comprobante_nombre'),
        hash_comprobante=data.get('hash_comprobante'),
        estado='pendiente'
    )
    db.session.add(pago_grupal)
    # flush() manda el INSERT a la base y le asigna el id a la fila, pero
    # todavía no confirma nada: eso lo hace el commit del final.
    db.session.flush()

    resumen = []
    for persona in personas:
        if persona['monto_asignado'] <= 0:
            continue

        aportante = persona['aportante']

        detalle = PagoGrupalDetalle(
            pago_grupal_id=pago_grupal.id,
            aportante_id=aportante.id,
            monto_asignado=persona['monto_asignado'],
            estado='pendiente',
            solicita_libreta=persona['solicita_libreta']
        )
        db.session.add(detalle)

        # El asiento contable de cada persona. NO lleva número de operación
        # propio: el número vive en la transferencia, así el control de
        # duplicados no lo cuenta dos veces (RF-04).
        pago = Pago(
            codigo_seguimiento=generar_codigo('SC'),
            aportante_id=aportante.id,
            tipo='cuota_grupal',
            importe=persona['monto_asignado'],
            fecha=fecha,
            medio_pago='transferencia',
            codigo_transaccion=None,
            hash_comprobante=data.get('hash_comprobante'),
            comprobante_nombre=data.get('comprobante_nombre'),
            fondo_id=fondo.id,
            ejercicio_id=ejercicio.id,
            estado='pendiente',
            observaciones='Parte de la transferencia grupal ' + pago_grupal.codigo_seguimiento,
            solicita_libreta=persona['solicita_libreta'],
            pago_grupal_id=pago_grupal.id
        )
        db.session.add(pago)

        resumen.append({
            'nombre': aportante.nombre_completo(),
            'dni': aportante.dni,
            'monto': persona['monto_asignado'],
            'falta_luego': round(persona['falta'] - persona['monto_asignado'], 2),
        })

    if excedente > 0 and personas:
        registrar_excedente(pago_grupal, personas[0]['aportante'], fondo, fecha,
                            excedente, data.get('hash_comprobante'))

    auditoria.registrar(
        usuario='portal-publico',
        accion='cargar_pago_grupal',
        tabla='pagos_grupales',
        registro_id=pago_grupal.id,
        detalle={
            'codigo_seguimiento': pago_grupal.codigo_seguimiento,
            'importe_total': str(importe_total),
            'personas': len(resumen),
            'tipo_distribucion': data.get('tipo_distribucion', 'auto'),
            'excedente_a_fondo': str(excedente),
        },
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return pago_grupal, {'asignaciones': resumen, 'excedente': excedente}


def registrar_excedente(pago_grupal, aportante, fondo, fecha, monto, huella):
    """Asienta lo que se transfirió de más como ingreso de la Cooperadora.

    Va como aporte adicional y sin ejercicio, así no le baja la cuota a nadie.
    """
    pago = Pago(
        codigo_seguimiento=generar_codigo('SC'),
        aportante_id=aportante.id,
        tipo='adicional',
        importe=monto,
        fecha=fecha,
        medio_pago='transferencia',
        codigo_transaccion=None,
        hash_comprobante=huella,
        comprobante_nombre=pago_grupal.comprobante_nombre,
        fondo_id=fondo.id,
        ejercicio_id=None,
        estado='pendiente',
        observaciones='Excedente de la transferencia grupal ' + pago_grupal.codigo_seguimiento,
        pago_grupal_id=pago_grupal.id
    )
    db.session.add(pago)
    return pago


# ============================================
# VERIFICACIÓN Y RECHAZO
# ============================================

def verificar_pago_grupal(pago_grupal_id, usuario_id, ip=None, user_agent=None):
    """Verifica la transferencia y todos los pagos que salieron de ella.

    Hay que recorrer los pagos uno por uno: si sólo marcáramos la
    transferencia como verificada, no se movería ningún fondo ni ningún saldo.
    """
    grupal = PagoGrupal.query.get(pago_grupal_id)
    if not grupal:
        raise ErrorDeCarga('La transferencia grupal no existe.')
    if grupal.estado != 'pendiente':
        raise ErrorDeCarga('La transferencia ya está {}.'.format(grupal.estado))

    grupal.estado = 'verificado'
    db.session.add(grupal)

    for detalle in grupal.detalles.all():
        detalle.estado = 'verificado'
        db.session.add(detalle)

    # Pasamos la consulta a lista antes del bucle: verificar_pago() hace su
    # propio commit, y no conviene recorrer una consulta mientras se guarda.
    for pago in grupal.pagos.all():
        if pago.estado == 'pendiente':
            servicio_pagos.verificar_pago(pago.id, usuario_id)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='verificar_pago_grupal',
        tabla='pagos_grupales',
        registro_id=grupal.id,
        detalle={'codigo_seguimiento': grupal.codigo_seguimiento,
                 'importe_total': str(grupal.importe_total)},
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return grupal


def rechazar_pago_grupal(pago_grupal_id, usuario_id, motivo, ip=None, user_agent=None):
    """Rechaza la transferencia y todos los pagos que salieron de ella."""
    grupal = PagoGrupal.query.get(pago_grupal_id)
    if not grupal:
        raise ErrorDeCarga('La transferencia grupal no existe.')

    motivo = (motivo or '').strip()
    if not motivo:
        raise ErrorDeCarga('Hay que indicar el motivo del rechazo.')

    grupal.estado = 'rechazado'
    db.session.add(grupal)

    for detalle in grupal.detalles.all():
        detalle.estado = 'rechazado'
        db.session.add(detalle)

    for pago in grupal.pagos.all():
        if pago.estado in ('pendiente', 'verificado'):
            servicio_pagos.rechazar_pago(pago.id, usuario_id, motivo)

    auditoria.registrar(
        usuario=str(usuario_id),
        accion='rechazar_pago_grupal',
        tabla='pagos_grupales',
        registro_id=grupal.id,
        detalle={'codigo_seguimiento': grupal.codigo_seguimiento, 'motivo': motivo},
        ip=ip,
        user_agent=user_agent
    )

    db.session.commit()
    return grupal
