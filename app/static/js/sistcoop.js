// ============================================================
// SistCoop 179 — JavaScript de los formularios del portal
// ------------------------------------------------------------
// Todo lo de acá es ayuda para el aportante mientras completa el formulario.
// Nada de esto reemplaza las validaciones del servidor: el HTML se puede
// editar y el formulario se puede mandar sin pasar por esta pantalla.
// ============================================================

var TIPOS_PERMITIDOS = ['image/jpeg', 'image/png', 'application/pdf'];
var TAMANIO_MAXIMO = 16 * 1024 * 1024;   // 16 MB
var TAMANIO_MINIMO = 1024;               // 1 KB


// ============================================
// FUNCIONES AUXILIARES
// ============================================

function tokenCsrf() {
    // El token está en un <meta> de base.html. Las rutas de la API son POST
    // y Flask las protege con CSRF: si no mandamos esta cabecera el servidor
    // contesta 400 y ninguna validación en vivo funciona.
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        return meta.content;
    }
    return '';
}

function consultarApi(url, datos) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': tokenCsrf()
        },
        body: JSON.stringify(datos)
    }).then(function (respuesta) {
        if (!respuesta.ok) {
            throw new Error(respuesta.status);
        }
        return respuesta.json();
    });
}

function enPesos(valor) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    }).format(valor || 0);
}

function mostrarMensaje(elemento, texto, clase) {
    if (!elemento) {
        return;
    }
    elemento.textContent = texto || '';
    elemento.className = 'sc-campo-estado';
    if (clase) {
        elemento.className = elemento.className + ' ' + clase;
    }
}


// ============================================
// CARGA DEL COMPROBANTE
// ============================================

function configurarCarga(idZona, idInput, idEstado, idVista) {
    var zona = document.getElementById(idZona);
    var input = document.getElementById(idInput);
    var estado = document.getElementById(idEstado);
    var vista = document.getElementById(idVista);

    if (!zona || !input) {
        return;
    }

    function rechazar(mensaje) {
        input.value = '';
        zona.classList.remove('cargado');
        zona.classList.add('invalido');
        mostrarMensaje(estado, mensaje, 'error');
        if (vista) {
            vista.innerHTML = '';
            vista.hidden = true;
        }
    }

    function aceptar(archivo) {
        zona.classList.remove('invalido');
        zona.classList.add('cargado');

        var kb = (archivo.size / 1024).toFixed(0);
        mostrarMensaje(estado, archivo.name + ' — ' + kb + ' KB. Listo para enviar.', 'ok');

        if (!vista) {
            return;
        }
        vista.innerHTML = '';

        if (archivo.type.startsWith('image/')) {
            // Vista previa de la imagen, así la persona confirma que subió
            // el archivo correcto antes de mandarlo
            var lector = new FileReader();
            lector.onload = function (e) {
                var img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Vista previa del comprobante adjuntado';
                img.className = 'img-fluid';
                vista.appendChild(img);
                vista.hidden = false;
            };
            lector.readAsDataURL(archivo);
        } else {
            vista.innerHTML = '<p class="sc-ayuda mb-0">' +
                '<i class="bi bi-file-earmark-pdf" aria-hidden="true"></i> ' +
                'Comprobante en PDF adjuntado. Los PDF no muestran vista previa.</p>';
            vista.hidden = false;
        }
    }

    function revisarArchivo(archivo) {
        if (!archivo) {
            return;
        }
        if (TIPOS_PERMITIDOS.indexOf(archivo.type) === -1) {
            rechazar('Ese formato no sirve. Adjuntá una imagen JPG o PNG, o un PDF.');
            return;
        }
        if (archivo.size > TAMANIO_MAXIMO) {
            rechazar('El archivo pesa más de 16 MB. Sacale una foto con menos resolución.');
            return;
        }
        if (archivo.size < TAMANIO_MINIMO) {
            rechazar('El archivo parece estar vacío o dañado.');
            return;
        }
        aceptar(archivo);
    }

    zona.addEventListener('click', function () {
        input.click();
    });

    // La zona es un <button>, así que también tiene que responder al teclado
    zona.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            input.click();
        }
    });

    zona.addEventListener('dragover', function (e) {
        e.preventDefault();
        zona.classList.add('arrastrando');
    });

    zona.addEventListener('dragleave', function () {
        zona.classList.remove('arrastrando');
    });

    zona.addEventListener('drop', function (e) {
        e.preventDefault();
        zona.classList.remove('arrastrando');
        if (e.dataTransfer.files.length > 0) {
            input.files = e.dataTransfer.files;
            revisarArchivo(e.dataTransfer.files[0]);
        }
    });

    input.addEventListener('change', function () {
        if (this.files.length > 0) {
            revisarArchivo(this.files[0]);
        }
    });
}


// ============================================
// VALIDACIONES MIENTRAS ESCRIBE
// ============================================

function validarDni(idInput, idEstado) {
    var input = document.getElementById(idInput);
    var estado = document.getElementById(idEstado);

    if (!input) {
        return;
    }

    input.addEventListener('blur', function () {
        var dni = input.value.trim();
        input.classList.remove('is-valid', 'is-invalid');

        if (!dni) {
            mostrarMensaje(estado, '');
            return;
        }

        consultarApi('/aportante/api/validar-dni', { dni: dni })
            .then(function (datos) {
                if (datos.valido) {
                    input.classList.add('is-valid');
                    mostrarMensaje(estado, '');
                } else {
                    input.classList.add('is-invalid');
                    mostrarMensaje(estado, datos.mensaje, 'error');
                }
            })
            .catch(function () {
                // Si falla la red no bloqueamos a la persona: el servidor
                // vuelve a validar cuando manda el formulario
                mostrarMensaje(estado, '');
            });
    });
}

function validarCuit(idInput, idEstado) {
    var input = document.getElementById(idInput);
    var estado = document.getElementById(idEstado);

    if (!input) {
        return;
    }

input.addEventListener('input', function () {
    let valor = input.value.replace(/\D/g, '');

    valor = valor.slice(0, 11);

    if (valor.length >= 11) {
        valor =
            valor.slice(0, 2) + '-' +
            valor.slice(2, 10) + '-' +
            valor.slice(10);
    } else if (valor.length > 2) {
        valor = valor.slice(0, 2) + '-' + valor.slice(2);
    }

    input.value = valor;
    });

    input.addEventListener('blur', function () {
        var cuit = input.value.trim();

        input.classList.remove('is-valid', 'is-invalid');

        if (!cuit) {
            mostrarMensaje(estado, '');
            return;
        }
        consultarApi('/aportante/api/validar-cuit', { cuit: cuit })
            .then(function (datos) {
                if (datos.valido) {
                    input.classList.add('is-valid');
                    if (datos.formateado) {
                        input.value = datos.formateado;
                    }
                    mostrarMensaje(estado, 'CUIT válido.', 'ok');
                } else {
                    input.classList.add('is-invalid');
                    mostrarMensaje(estado, datos.mensaje, 'error');
                }
            })
            .catch(function () {
                mostrarMensaje(estado, '');
            });
    });
}

function validarTransaccion(idInput, idEstado) {
    var input = document.getElementById(idInput);
    var estado = document.getElementById(idEstado);

    if (!input) {
        return;
    }

    input.addEventListener('blur', function () {
        var codigo = input.value.trim();
        input.classList.remove('is-valid', 'is-invalid');

        if (codigo.length < 4) {
            mostrarMensaje(estado, '');
            return;
        }

        consultarApi('/aportante/api/validar-transaccion', { codigo: codigo })
            .then(function (datos) {
                if (datos.disponible) {
                    input.classList.add('is-valid');
                    mostrarMensaje(estado, '');
                } else {
                    input.classList.add('is-invalid');
                    mostrarMensaje(estado, datos.mensaje, 'error');
                }
            })
            .catch(function () {
                mostrarMensaje(estado, '');
            });
    });
}


// ============================================
// ESTADO DE CUOTA EN VIVO
// ============================================
// Al escribir el DNI, la persona ve cuánto es la cuota, cuánto tiene
// verificado, cuánto está en revisión y cuánto le falta. Es la consulta que
// hoy le llega por WhatsApp a la Cooperadora.

function configurarEstadoCuota(idDni, idPanel, idImporte) {
    var input = document.getElementById(idDni);
    var panel = document.getElementById(idPanel);

    if (!input || !panel) {
        return;
    }

    var barraVerificado = panel.querySelector('[data-medidor="verificado"]');
    var barraRevision = panel.querySelector('[data-medidor="revision"]');
    var inputImporte = idImporte ? document.getElementById(idImporte) : null;

    function escribir(selector, texto) {
        var elemento = panel.querySelector(selector);
        if (elemento) {
            elemento.textContent = texto;
        }
    }

    function armarResumen(datos) {
        if (datos.al_dia) {
            return 'Tu cuota de este año ya está completa y verificada.';
        }
        if (datos.en_revision > 0) {
            var faltaDespues = Math.max(datos.saldo_pendiente - datos.en_revision, 0);
            return 'Tenés ' + enPesos(datos.en_revision) + ' esperando que la ' +
                   'Cooperadora los verifique. Después de eso te faltarían ' +
                   enPesos(faltaDespues) + '.';
        }
        if (!datos.registrado) {
            return 'Es tu primer aporte registrado. La cuota completa de este año es ' +
                   enPesos(datos.cuota_total) + '.';
        }
        return 'Te faltan ' + enPesos(datos.saldo_pendiente) +
               ' para completar la cuota de este año.';
    }

    input.addEventListener('blur', function () {
        var dni = input.value.trim();

        if (dni.replace(/\D/g, '').length < 7) {
            panel.hidden = true;
            return;
        }

        consultarApi('/aportante/api/estado-cuota', { dni: dni })
            .then(function (datos) {
                if (!datos.disponible) {
                    panel.hidden = true;
                    return;
                }

                escribir('[data-campo="cuota"]', enPesos(datos.cuota_total));
                escribir('[data-campo="pagado"]', enPesos(datos.pagado));
                escribir('[data-campo="revision"]', enPesos(datos.en_revision));
                escribir('[data-campo="pendiente"]', enPesos(datos.saldo_pendiente));
                escribir('[data-campo="resumen"]', armarResumen(datos));

                // Barra de avance: primero lo verificado, después lo que
                // está en revisión, sin pasarse del 100%
                var total = datos.cuota_total || 1;
                var porcentajePagado = Math.min(100, (datos.pagado / total) * 100);
                var porcentajeRevision = Math.min(100 - porcentajePagado,
                                                  (datos.en_revision / total) * 100);

                if (barraVerificado) {
                    barraVerificado.style.width = porcentajePagado + '%';
                }
                if (barraRevision) {
                    barraRevision.style.width = porcentajeRevision + '%';
                }

                // Sugerimos el importe que falta, sin pisarlo si ya escribió otro
                if (inputImporte && !inputImporte.value && datos.saldo_pendiente > 0) {
                    inputImporte.placeholder = datos.saldo_pendiente.toFixed(2);
                }

                panel.hidden = false;
            })
            .catch(function () {
                panel.hidden = true;
            });
    });
}


// ============================================
// ENVÍO DEL FORMULARIO
// ============================================

function evitarDobleEnvio(idForm, idBoton, textoEnviando) {
    var form = document.getElementById(idForm);
    var boton = document.getElementById(idBoton);

    if (!form || !boton) {
        return;
    }

    form.addEventListener('submit', function (e) {
        // Si ya se está enviando, cortamos: si no quedarían dos pagos
        // cargados con un solo comprobante
        if (form.dataset.enviando === 'true') {
            e.preventDefault();
            return;
        }
        if (e.defaultPrevented) {
            return;
        }

        form.dataset.enviando = 'true';
        boton.disabled = true;
        boton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" ' +
                          'aria-hidden="true"></span>' + (textoEnviando || 'Enviando…');
    });
}


// ============================================
// AL CARGAR LA PÁGINA
// ============================================

document.addEventListener('DOMContentLoaded', function () {

    // Ninguna transferencia puede tener fecha de mañana
    var hoy = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"][data-no-futura]').forEach(function (input) {
        input.max = hoy;
    });

    // Los mensajes se cierran solos, menos los de error: esos quedan hasta
    // que la persona los lea
    document.querySelectorAll('.sc-mensajes .alert:not(.alert-danger)').forEach(function (alerta) {
        setTimeout(function () {
            if (window.bootstrap && bootstrap.Alert) {
                bootstrap.Alert.getOrCreateInstance(alerta).close();
            }
        }, 7000);
    });

    // Botones de "copiar" (el código de seguimiento)
    document.querySelectorAll('[data-copiar]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            var original = boton.innerHTML;
            if (!navigator.clipboard) {
                return;
            }
            navigator.clipboard.writeText(boton.dataset.copiar).then(function () {
                boton.innerHTML = '<i class="bi bi-check2" aria-hidden="true"></i> Copiado';
                setTimeout(function () {
                    boton.innerHTML = original;
                }, 2000);
            });
        });
    });
});


// Si la persona vuelve con el botón "atrás" del navegador, el formulario
// quedaba con el botón desactivado
window.addEventListener('pageshow', function (evento) {
    if (!evento.persisted) {
        return;
    }
    document.querySelectorAll('form[data-enviando="true"]').forEach(function (form) {
        form.dataset.enviando = 'false';
        form.querySelectorAll('button[type="submit"]').forEach(function (boton) {
            boton.disabled = false;
        });
    });
});
