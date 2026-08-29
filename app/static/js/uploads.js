// ============================================================
// Funciones compartidas de UI para los formularios de Aportante
// (cuota.html, adicional.html, solicitud.html)
// ------------------------------------------------------------
// - setupUpload:        área de arrastrar/soltar + selección de comprobante
// - validarDni:         feedback en vivo del DNI contra la API
// - validarTransaccion: feedback en vivo del código de transacción
// ============================================================

const TIPOS_ARCHIVO_PERMITIDOS = ['image/jpeg', 'image/png', 'application/pdf'];
const TAMANIO_MAXIMO_ARCHIVO = 16 * 1024 * 1024; // 16MB

function setupUpload(uploadAreaId, fileInputId, fileInfoId, previewContainerId) {
    const uploadArea = document.getElementById(uploadAreaId);
    const fileInput = document.getElementById(fileInputId);
    const fileInfo = fileInfoId ? document.getElementById(fileInfoId) : null;
    const previewContainer = previewContainerId ? document.getElementById(previewContainerId) : null;

    if (!uploadArea || !fileInput) return;

    function mostrarError(mensaje) {
        fileInput.value = '';
        if (fileInfo) {
            fileInfo.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-circle"></i> ${mensaje}</span>`;
        }
        if (previewContainer) {
            previewContainer.style.display = 'none';
            previewContainer.innerHTML = '';
        }
        uploadArea.style.borderColor = '#dc3545';
    }

    function mostrarArchivo(file) {
        if (!TIPOS_ARCHIVO_PERMITIDOS.includes(file.type)) {
            mostrarError('Formato no permitido. Usá JPG, PNG o PDF.');
            return;
        }
        if (file.size > TAMANIO_MAXIMO_ARCHIVO) {
            mostrarError('El archivo supera el tamaño máximo permitido (16MB).');
            return;
        }

        if (fileInfo) {
            fileInfo.innerHTML = `<i class="bi bi-file-earmark-check text-success"></i> ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        }
        uploadArea.style.borderColor = '#2e7d4f';

        if (previewContainer) {
            previewContainer.innerHTML = '';
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewContainer.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded border" style="max-height: 220px;" alt="Vista previa del comprobante">`;
                    previewContainer.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else {
                previewContainer.innerHTML = `<div class="text-muted small"><i class="bi bi-file-earmark-pdf me-1"></i>Comprobante en PDF cargado (sin vista previa).</div>`;
                previewContainer.style.display = 'block';
            }
        }
    }

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            mostrarArchivo(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', function () {
        if (this.files.length) {
            mostrarArchivo(this.files[0]);
        }
    });
}

function validarDni(inputId, feedbackId) {
    const input = document.getElementById(inputId);
    const feedback = feedbackId ? document.getElementById(feedbackId) : null;
    if (!input) return;

    input.addEventListener('blur', function () {
        const dni = this.value.trim();
        input.classList.remove('is-valid', 'is-invalid');
        if (!dni) {
            if (feedback) feedback.textContent = '';
            return;
        }

        fetch('/aportante/api/validar-dni', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dni })
        })
            .then(response => response.json())
            .then(data => {
                if (!data.valido) {
                    input.classList.add('is-invalid');
                    if (feedback) feedback.textContent = data.mensaje || 'DNI inválido';
                } else {
                    input.classList.add('is-valid');
                    if (feedback) feedback.textContent = '';
                }
            })
            .catch(() => {
                // Si falla la verificación por red, no bloqueamos al usuario:
                // puede seguir completando el formulario igual.
                if (feedback) feedback.textContent = '';
            });
    });
}

function validarTransaccion(inputId, feedbackId) {
    const input = document.getElementById(inputId);
    const feedback = feedbackId ? document.getElementById(feedbackId) : null;
    if (!input) return;

    input.addEventListener('blur', function () {
        const codigo = this.value.trim();
        input.classList.remove('is-valid', 'is-invalid');
        if (feedback) feedback.textContent = '';
        if (codigo.length < 5) return;

        fetch('/aportante/api/validar-transaccion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo })
        })
            .then(response => response.json())
            .then(data => {
                if (data.existe) {
                    input.classList.add('is-invalid');
                    if (feedback) feedback.textContent = data.mensaje;
                } else {
                    input.classList.add('is-valid');
                    if (feedback) feedback.textContent = data.mensaje;
                }
            })
            .catch(() => {
                if (feedback) feedback.textContent = '';
            });
    });
}
