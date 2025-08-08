document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica para el modal de Añadir Pedido (Asistente) ---
    const addPedidoModal = document.getElementById('addPedidoModal');
    if (addPedidoModal) {
        // ... (código del modal de añadir sin cambios)
    }

    // --- Lógica para el modal de Editar Pedido ---
    const editPedidoModal = document.getElementById('editPedidoModal');
    if (editPedidoModal) {
        const editForm = editPedidoModal.querySelector('#editPedidoForm');
        const saveChangesBtn = editPedidoModal.querySelector('#saveChangesBtn'); // ID AÑADIDO

        // Listener para cuando se muestra el modal
        editPedidoModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var id = button.getAttribute('data-id');
            
            // Actualizar el action del formulario dinámicamente
            if(editForm) editForm.action = '/update_pedido/' + id;

            // Rellenar todos los campos del formulario (código sin cambios)
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
        });

        // Listener para el envío del formulario
        if (editForm) {
            editForm.addEventListener('submit', function(e) {
                alert('¡PRUEBA DEFINITIVA! El formulario se está enviando.');
            });
        }
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

            // Rellenar el modal (código sin cambios)
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

    // ... resto del código (modos oscuro, toasts, etc. sin cambios)
});