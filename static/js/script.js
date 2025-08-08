document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica para el modal de Añadir Pedido (Asistente) ---
    const addPedidoModal = document.getElementById('addPedidoModal');
    if (addPedidoModal) {
        const prevBtn = addPedidoModal.querySelector('#prevBtn');
        const nextBtn = addPedidoModal.querySelector('#nextBtn');
        const submitBtn = addPedidoModal.querySelector('#submitBtn');
        const steps = addPedidoModal.querySelectorAll('.form-step');
        let currentStep = 1;

        function showStep(stepNumber) {
            steps.forEach(step => step.style.display = 'none');
            const currentStepElement = addPedidoModal.querySelector(`#step-${stepNumber}`);
            if (currentStepElement) {
                currentStepElement.style.display = 'block';
            }
            if (prevBtn) prevBtn.style.display = (stepNumber === 1) ? 'none' : 'inline-block';
            if (nextBtn) nextBtn.style.display = (stepNumber === steps.length) ? 'none' : 'inline-block';
            if (submitBtn) submitBtn.style.display = (stepNumber === steps.length) ? 'inline-block' : 'none';
        }

        function validateStep(stepNumber) {
            const currentStepElement = addPedidoModal.querySelector(`#step-${stepNumber}`);
            if (!currentStepElement) return true;
            const inputs = currentStepElement.querySelectorAll('input[required], select[required], textarea[required]');
            let isValid = true;
            for (let input of inputs) {
                if (!input.value) {
                    input.classList.add('is-invalid');
                    isValid = false;
                } else {
                    input.classList.remove('is-invalid');
                }
            }
            return isValid;
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (validateStep(currentStep) && currentStep < steps.length) {
                    currentStep++;
                    showStep(currentStep);
                }
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (currentStep > 1) {
                    currentStep--;
                    showStep(currentStep);
                }
            });
        }

        addPedidoModal.addEventListener('hidden.bs.modal', function () {
            currentStep = 1;
            showStep(currentStep);
            const form = addPedidoModal.querySelector('#addPedidoForm');
            if (form) form.reset();
            const invalidInputs = addPedidoModal.querySelectorAll('.is-invalid');
            invalidInputs.forEach(input => input.classList.remove('is-invalid'));
        });

        addPedidoModal.addEventListener('show.bs.modal', function () {
            currentStep = 1;
            showStep(currentStep);
        });
    }

    // --- Lógica para el modal de Editar Pedido ---
    const editPedidoModal = document.getElementById('editPedidoModal');
    if (editPedidoModal) {
        editPedidoModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var id = button.getAttribute('data-id');
            var nombre_cliente = button.getAttribute('data-nombre_cliente');
            var forma_contacto = button.getAttribute('data-forma_contacto');
            var contacto_detalle = button.getAttribute('data-contacto_detalle');
            var direccion_entrega = button.getAttribute('data-direccion_entrega');
            var producto = button.getAttribute('data-producto');
            var detalles = button.getAttribute('data-detalles');
            var precio = parseFloat(button.getAttribute('data-precio'));
            var anticipo = parseFloat(button.getAttribute('data-anticipo'));
            var estado_pedido = button.getAttribute('data-estado_pedido');
            var imagen_path = button.getAttribute('data-imagen_path');

            var modalForm = editPedidoModal.querySelector('#editPedidoForm');
            if(modalForm) modalForm.action = '/update_pedido/' + id;

            function setInputValue(id, value) {
                const element = editPedidoModal.querySelector(id);
                if (element) element.value = value;
            }

            setInputValue('#edit_id', id);
            setInputValue('#edit_nombre_cliente', nombre_cliente);
            setInputValue('#edit_forma_contacto', forma_contacto);
            setInputValue('#edit_contacto_detalle', contacto_detalle);
            setInputValue('#edit_direccion_entrega', direccion_entrega);
            setInputValue('#edit_producto', producto);
            setInputValue('#edit_detalles', detalles);
            setInputValue('#edit_precio', precio.toFixed(2));
            setInputValue('#edit_anticipo', anticipo.toFixed(2));
            setInputValue('#edit_estado_pedido', estado_pedido);
            setInputValue('#current_imagen_path', imagen_path);

            var currentImagePreview = editPedidoModal.querySelector('#current_image_preview');
            if (currentImagePreview) {
                currentImagePreview.innerHTML = '';
                if (imagen_path) {
                    var img = document.createElement('img');
                    img.src = imagen_path;
                    img.alt = 'Imagen Actual';
                    img.style.maxWidth = '100px';
                    img.style.maxHeight = '100px';
                    img.style.objectFit = 'cover';
                    currentImagePreview.appendChild(img);
                } else {
                    currentImagePreview.textContent = 'No hay imagen actual.';
                }
            }

            function updateMontoRestante() {
                const precioInput = editPedidoModal.querySelector('#edit_precio');
                const anticipoInput = editPedidoModal.querySelector('#edit_anticipo');
                const montoRestanteDisplay = editPedidoModal.querySelector('#edit_monto_restante_display');
                if (precioInput && anticipoInput && montoRestanteDisplay) {
                    var currentPrecio = parseFloat(precioInput.value) || 0;
                    var currentAnticipo = parseFloat(anticipoInput.value) || 0;
                    montoRestanteDisplay.textContent = (currentPrecio - currentAnticipo).toFixed(2);
                }
            }
            
            updateMontoRestante();
            const precioInput = editPedidoModal.querySelector('#edit_precio');
            const anticipoInput = editPedidoModal.querySelector('#edit_anticipo');
            if(precioInput) precioInput.addEventListener('input', updateMontoRestante);
            if(anticipoInput) anticipoInput.addEventListener('input', updateMontoRestante);
        });
    }

    // --- Lógica para el modal de Ver Pedido (Solo Lectura) ---
    const viewPedidoModal = document.getElementById('viewPedidoModal');
    if (viewPedidoModal) {
        viewPedidoModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const data = {};
            for (let i = 0; i < button.attributes.length; i++) {
                const attr = button.attributes[i];
                if (attr.name.startsWith('data-')) {
                    const key = attr.name.substring(5);
                    data[key] = attr.value;
                }
            }

            document.getElementById('view_nombre_cliente').textContent = data.nombre_cliente;
            document.getElementById('view_forma_contacto').textContent = data.forma_contacto;
            document.getElementById('view_contacto_detalle').textContent = data.contacto_detalle;
            document.getElementById('view_direccion_entrega').textContent = data.direccion_entrega || 'N/A';
            document.getElementById('view_producto').textContent = data.producto;
            document.getElementById('view_detalles').textContent = data.detalles;
            document.getElementById('view_estado_pedido').textContent = data.estado_pedido;
            document.getElementById('view_fecha_creacion').textContent = data.fecha_creacion;
            document.getElementById('view_precio').textContent = parseFloat(data.precio).toFixed(2);
            document.getElementById('view_anticipo').textContent = parseFloat(data.anticipo).toFixed(2);
            document.getElementById('view_estado_pago').textContent = data.estado_pago;

            const montoRestante = parseFloat(data.precio) - parseFloat(data.anticipo);
            document.getElementById('view_monto_restante').textContent = montoRestante.toFixed(2);

            const viewImagePreview = document.getElementById('view_imagen_preview');
            if (viewImagePreview) {
                viewImagePreview.innerHTML = '';
                if (data.imagen_path) {
                    const img = document.createElement('img');
                    img.src = data.imagen_path;
                    img.alt = 'Imagen del Producto';
                    img.style.maxWidth = '100%';
                    img.style.height = 'auto';
                    img.style.borderRadius = '8px';
                    viewImagePreview.appendChild(img);
                } else {
                    viewImagePreview.textContent = 'No hay imagen asociada.';
                }
            }
        });
    }

    // --- Lógica para el modo oscuro ---
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    const lightModeIcon = document.querySelector('.light-mode-icon');
    const darkModeIcon = document.querySelector('.dark-mode-icon');

    let estadoPedidosChartInstance = null;
    let ingresosMensualesChartInstance = null;

    function renderCharts() {
        const isDarkMode = body.classList.contains('dark-mode');
        const chartFontColor = isDarkMode ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.8)';
        const chartGridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

        const estadoPedidosCtx = document.getElementById('estadoPedidosChart');
        const ingresosMensualesCtx = document.getElementById('ingresosMensualesChart');

        if (estadoPedidosCtx) {
            if (estadoPedidosChartInstance) {
                estadoPedidosChartInstance.destroy();
            }
            const chartEstadosDataElement = document.getElementById('chart-estados-data');
            const chartEstadosData = JSON.parse(chartEstadosDataElement.textContent);
            estadoPedidosChartInstance = new Chart(estadoPedidosCtx, {
                type: 'doughnut',
                data: {
                    labels: chartEstadosData.labels,
                    datasets: [{
                        data: chartEstadosData.data,
                        backgroundColor: ['rgba(255, 193, 7, 0.7)', 'rgba(23, 162, 184, 0.7)', 'rgba(40, 167, 69, 0.7)'],
                        borderColor: [isDarkMode ? '#1e1e1e' : '#ffffff'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'top', labels: { color: chartFontColor } }
                    }
                }
            });
        }

        if (ingresosMensualesCtx) {
            if (ingresosMensualesChartInstance) {
                ingresosMensualesChartInstance.destroy();
            }
            const chartIngresosDataElement = document.getElementById('chart-ingresos-data');
            const chartIngresosData = JSON.parse(chartIngresosDataElement.textContent);
            ingresosMensualesChartInstance = new Chart(ingresosMensualesCtx, {
                type: 'bar',
                data: {
                    labels: chartIngresosData.labels,
                    datasets: [{
                        label: 'Ingresos (€)',
                        data: chartIngresosData.data,
                        backgroundColor: 'rgba(40, 167, 69, 0.5)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true, ticks: { color: chartFontColor }, grid: { color: chartGridColor } },
                        x: { ticks: { color: chartFontColor }, grid: { color: chartGridColor } }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
    }

    function setDarkMode(enabled) {
        if (enabled) {
            body.classList.add('dark-mode');
            if(lightModeIcon) lightModeIcon.style.display = 'none';
            if(darkModeIcon) darkModeIcon.style.display = 'inline';
            localStorage.setItem('darkMode', 'enabled');
        } else {
            body.classList.remove('dark-mode');
            if(lightModeIcon) lightModeIcon.style.display = 'inline';
            if(darkModeIcon) darkModeIcon.style.display = 'none';
            localStorage.setItem('darkMode', 'disabled');
        }
        renderCharts();
    }

    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode === 'enabled') {
        setDarkMode(true);
    } else {
        setDarkMode(false);
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            const isDarkModeEnabled = body.classList.contains('dark-mode');
            setDarkMode(!isDarkModeEnabled);
        });
    }

    const table = document.getElementById('pedidosTable');
    const tableBody = table.querySelector('tbody');
    const rows = Array.from(tableBody.querySelectorAll('tr'));
    const headers = table.querySelectorAll('th[data-sort]');
    let currentSort = { column: null, direction: 'asc' };
    const calendarioEl = document.getElementById('calendario');
    const showAllBtn = document.getElementById('showAllBtn');
    let calendar = null;

    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-sort');
            const direction = (currentSort.column === column && currentSort.direction === 'asc') ? 'desc' : 'asc';
            const sortedRows = rows.sort((a, b) => {
                let valA = a.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent.trim();
                let valB = b.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent.trim();
                if (column === 'precio') {
                    valA = parseFloat(valA.replace(' €', ''));
                    valB = parseFloat(valB.replace(' €', ''));
                }
                if (valA < valB) return direction === 'asc' ? -1 : 1;
                if (valA > valB) return direction === 'asc' ? 1 : -1;
                return 0;
            });
            tableBody.innerHTML = '';
            sortedRows.forEach(row => tableBody.appendChild(row));
            headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
            header.classList.add(direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
            currentSort = { column, direction };
        });
    });

    if (calendarioEl) {
        const fechasPedidosJson = calendarioEl.getAttribute('data-dates');
        const fechasPedidos = JSON.parse(fechasPedidosJson);
        const eventos = fechasPedidos.map(fecha => ({ start: fecha, display: 'background', classNames: ['event-day'] }));
        calendar = new FullCalendar.Calendar(calendarioEl, {
            initialView: 'dayGridMonth',
            locale: 'es',
            headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' },
            events: eventos,
            dateClick: function(info) {
                const clickedDate = info.dateStr;
                let hasEvent = false;
                rows.forEach(row => {
                    const rowDate = row.cells[5].textContent.split(' ')[0];
                    if (rowDate === clickedDate) {
                        row.style.display = '';
                        hasEvent = true;
                    } else {
                        row.style.display = 'none';
                    }
                });
                if (hasEvent && showAllBtn) showAllBtn.style.display = 'inline-block';
            }
        });
        calendar.render();
    }

    if (showAllBtn) {
        showAllBtn.addEventListener('click', () => {
            rows.forEach(row => { row.style.display = ''; });
            showAllBtn.style.display = 'none';
            const searchInput = document.getElementById('searchInput');
            if (searchInput) searchInput.value = '';
        });
    }

    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl, { delay: 3000 });
    });
    toastList.forEach(toast => toast.show());

    const animatedElements = document.querySelectorAll('.metric-card, .table-responsive, #calendario-container, #charts-container');
    animatedElements.forEach((el, index) => {
        const animationDelay = index * 100;
        setTimeout(() => {
            el.style.opacity = 0;
            el.classList.add('animated', 'fadeInUp');
            el.style.opacity = 1;
            if (el.id === 'calendario-container' && calendar) {
                setTimeout(() => { calendar.updateSize(); }, 400);
            }
        }, animationDelay);
    });

    const tableRows = document.querySelectorAll('#pedidosTable tbody tr');
    tableRows.forEach((row, index) => {
        setTimeout(() => {
            row.style.animation = `fadeInUp 0.5s ease-out forwards`;
            row.style.animationDelay = `${index * 0.05}s`;
            row.style.opacity = 1;
        }, 300);
    });

    const confirmDeleteModal = document.getElementById('confirmDeleteModal');
    if (confirmDeleteModal) {
        confirmDeleteModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const pedidoId = button.getAttribute('data-id');
            const nombreCliente = button.getAttribute('data-nombre_cliente');

            const deleteForm = confirmDeleteModal.querySelector('#deleteForm');
            const clienteNombreSpan = confirmDeleteModal.querySelector('#delete_cliente_nombre');

            if (deleteForm && clienteNombreSpan) {
                deleteForm.action = `/delete_pedido/${pedidoId}`;
                clienteNombreSpan.textContent = nombreCliente;
            }
        });
    }
});