from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os
from werkzeug.utils import secure_filename
from collections import Counter
from datetime import datetime
import json
import io
import csv
import math

import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)

# Configuración de Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey_dev_fallback') # ¡IMPORTANTE: Cambia esto por una clave segura en producción y cárgala desde una variable de entorno!
DATABASE = 'pedidos.db'

# NOTA DE SEGURIDAD: Las credenciales de usuario están hardcodeadas en esta versión.
# Para una aplicación en producción, se recomienda implementar un sistema de gestión de usuarios
# más robusto, que incluya almacenamiento de contraseñas hasheadas y una base de datos de usuarios real.

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PEDIDOS_POR_PAGINA = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Configuración de Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirige aquí si el usuario no está logueado

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self): # CORREGIDO: Añadido 'self'
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    # En este caso, solo tenemos un usuario 'robleka'
    if user_id == 'robleka':
        return User('robleka')
    return None

# --- Funciones de la aplicación (sin cambios)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_cliente TEXT NOT NULL,
                forma_contacto TEXT NOT NULL,
                contacto_detalle TEXT,
                direccion_entrega TEXT,
                producto TEXT NOT NULL,
                detalles TEXT,
                precio REAL NOT NULL,
                anticipo REAL DEFAULT 0.0,
                imagen_path TEXT,
                estado_pago TEXT NOT NULL,
                estado_pedido TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

init_db()

# --- Rutas de la aplicación ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'robleka' and password == 'robleka_pass':
            user = User(username)
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

@app.route('/export/csv')
@login_required
def export_csv():
    conn = get_db_connection()
    pedidos = conn.execute('SELECT * FROM pedidos ORDER BY fecha_creacion DESC').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    header = pedidos[0].keys() if pedidos else []
    writer.writerow(header)

    for pedido in pedidos:
        writer.writerow([pedido[key] for key in header])

    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=pedidos.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    conn = get_db_connection()
    
    query_params = []
    base_query = 'FROM pedidos'
    search_query = ''
    if search_term:
        search_query = ' WHERE nombre_cliente LIKE ? OR producto LIKE ? OR estado_pedido LIKE ?'
        query_params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])

    count_query = f'SELECT COUNT(*) {base_query} {search_query}'
    total_pedidos_result = conn.execute(count_query, query_params).fetchone()
    total_pedidos = total_pedidos_result[0] if total_pedidos_result else 0
    total_paginas = math.ceil(total_pedidos / PEDIDOS_POR_PAGINA)
    
    offset = (page - 1) * PEDIDOS_POR_PAGINA
    pedidos_query = f'SELECT * {base_query} {search_query} ORDER BY fecha_creacion DESC LIMIT ? OFFSET ?'
    query_params.extend([PEDIDOS_POR_PAGINA, offset])
    pedidos = conn.execute(pedidos_query, query_params).fetchall()
    
    total_facturado_result = conn.execute("""
        SELECT
            SUM(CASE WHEN estado_pago = 'Pagado Completo' THEN precio ELSE 0 END) AS total_completo,
            SUM(CASE WHEN estado_pago = 'Anticipo Pagado' THEN anticipo ELSE 0 END) AS total_anticipo
        FROM pedidos
    """).fetchone()
    total_facturado = (total_facturado_result['total_completo'] or 0) + (total_facturado_result['total_anticipo'] or 0)

    monto_pendiente_result = conn.execute("""
        SELECT SUM(precio - anticipo) AS pendiente
        FROM pedidos
        WHERE estado_pago != 'Pagado Completo'
    """).fetchone()
    monto_pendiente = monto_pendiente_result['pendiente'] or 0.0

    estados_result = conn.execute("SELECT estado_pedido, COUNT(*) FROM pedidos GROUP BY estado_pedido").fetchall()
    chart_estados_data = {
        'labels': [row['estado_pedido'] for row in estados_result],
        'data': [row['COUNT(*)'] for row in estados_result]
    }

    ingresos_mensuales_result = conn.execute("""
        SELECT
            strftime('%Y-%m', fecha_creacion) AS mes_ano,
            SUM(precio) AS total_ingreso
        FROM pedidos
        WHERE estado_pago = 'Pagado Completo'
        GROUP BY mes_ano
        ORDER BY mes_ano
    """).fetchall()
    chart_ingresos_data = {
        'labels': [row['mes_ano'] for row in ingresos_mensuales_result],
        'data': [row['total_ingreso'] for row in ingresos_mensuales_result]
    }

    fechas_unicas_result = conn.execute("SELECT DISTINCT strftime('%Y-%m-%d', fecha_creacion) AS fecha FROM pedidos ORDER BY fecha").fetchall()
    fechas_unicas = [row['fecha'] for row in fechas_unicas_result]

    conn.close()
    return render_template('index.html', 
                           pedidos=pedidos, 
                           fechas_pedidos_json=json.dumps(fechas_unicas),
                           total_facturado=total_facturado,
                           monto_pendiente=monto_pendiente,
                           chart_estados_data=json.dumps(chart_estados_data),
                           chart_ingresos_data=json.dumps(chart_ingresos_data),
                           page=page,
                           total_paginas=total_paginas,
                           search_term=search_term)

@app.route('/add_pedido', methods=['POST'])
@login_required
def add_pedido():
    if request.method == 'POST':
        nombre_cliente = request.form['nombre_cliente']
        forma_contacto = request.form['forma_contacto']
        contacto_detalle = request.form['contacto_detalle']
        direccion_entrega = request.form['direccion_entrega']
        producto = request.form['producto']
        detalles = request.form['detalles']
        precio_str = request.form['precio']
        anticipo_str = request.form.get('anticipo', '0.0')
        
        errors = []
        if not nombre_cliente: errors.append('El nombre del cliente es obligatorio.')
        if not forma_contacto: errors.append('La forma de contacto es obligatoria.')
        if not producto: errors.append('El producto es obligatorio.')

        try:
            precio = float(precio_str)
            if precio <= 0: errors.append('El precio debe ser un número positivo.')
        except ValueError: errors.append('El precio debe ser un número válido.')

        try:
            anticipo = float(anticipo_str)
            if anticipo < 0: errors.append('El anticipo no puede ser negativo.')
            if 'precio' in locals() and anticipo > precio: errors.append('El anticipo no puede ser mayor que el precio total.')
        except ValueError: errors.append('El anticipo debe ser un número válido.')

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('index.html', 
                                   pedidos=[], 
                                   fechas_pedidos_json=json.dumps([]),
                                   total_facturado=0,
                                   monto_pendiente=0,
                                   chart_estados_data=json.dumps({}),
                                   chart_ingresos_data=json.dumps({}),
                                   page=1, total_paginas=1,
                                   search_term='',
                                   form_data=request.form)

        if anticipo == precio:
            estado_pago = 'Pagado Completo'
        elif anticipo > 0:
            estado_pago = 'Anticipo Pagado'
        else:
            estado_pago = 'Pendiente'
        
        estado_pedido = 'Pendiente'
        
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file.filename != '' and allowed_file(file.filename):
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    imagen_path = upload_result['secure_url']
                except Exception as e:
                    flash(f'Error al subir la imagen a Cloudinary: {e}', 'danger')
                    imagen_path = None

        conn = get_db_connection()
        conn.execute('''INSERT INTO pedidos (nombre_cliente, forma_contacto, contacto_detalle, direccion_entrega, producto, detalles, precio, anticipo, imagen_path, estado_pago, estado_pedido) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (nombre_cliente, forma_contacto, contacto_detalle, direccion_entrega, producto, detalles, precio, anticipo, imagen_path, estado_pago, estado_pedido))
        conn.commit()
        conn.close()
        flash('¡Pedido añadido con éxito!', 'success')
        return redirect(url_for('index'))

@app.route('/update_pedido/<int:id>', methods=['POST'])
@login_required
def update_pedido(id):
    if request.method == 'POST':
        # --- 1. Obtener todos los datos del formulario ---
        nombre_cliente = request.form['nombre_cliente']
        forma_contacto = request.form['forma_contacto']
        contacto_detalle = request.form['contacto_detalle']
        direccion_entrega = request.form['direccion_entrega']
        producto = request.form['producto']
        detalles = request.form['detalles']
        precio_str = request.form['precio']
        anticipo_str = request.form.get('anticipo', '0.0')
        estado_pedido = request.form['estado_pedido']
        
        # --- 2. Validar los datos --- 
        errors = []
        if not nombre_cliente: errors.append('El nombre del cliente es obligatorio.')
        if not forma_contacto: errors.append('La forma de contacto es obligatoria.')
        if not producto: errors.append('El producto es obligatorio.')

        try:
            precio = float(precio_str)
            if precio <= 0: errors.append('El precio debe ser un número positivo.')
        except (ValueError, TypeError): errors.append('El precio debe ser un número válido.')

        try:
            anticipo = float(anticipo_str)
            if anticipo < 0: errors.append('El anticipo no puede ser negativo.')
            if 'precio' in locals() and anticipo > precio: errors.append('El anticipo no puede ser mayor que el precio total.')
        except (ValueError, TypeError): errors.append('El anticipo debe ser un número válido.')

        if errors:
            for error in errors: flash(error, 'danger')
            return redirect(url_for('index'))

        # --- 3. Lógica de negocio (estados de pago, etc.) ---
        if estado_pedido == 'Completado':
            anticipo = precio
            estado_pago = 'Pagado Completo'
        else:
            if anticipo == precio:
                estado_pago = 'Pagado Completo'
            elif anticipo > 0:
                estado_pago = 'Anticipo Pagado'
            else:
                estado_pago = 'Pendiente'

        # --- 4. Lógica de la imagen con DEBUGGING ---
        conn = get_db_connection()
        pedido_actual = conn.execute('SELECT imagen_path FROM pedidos WHERE id = ?', (id,)).fetchone()
        imagen_path = pedido_actual['imagen_path'] if pedido_actual else None
        flash(f"DEBUG 1: Path de imagen inicial desde DB: {imagen_path}", 'info')
        
        nueva_imagen_subida = 'imagen' in request.files and request.files['imagen'].filename != ''

        if nueva_imagen_subida:
            flash("DEBUG 2: Detectada nueva imagen para subir.", 'info')
            file = request.files['imagen']
            if allowed_file(file.filename):
                if imagen_path and imagen_path.startswith('http'):
                    try:
                        parts = imagen_path.split('/upload/')
                        if len(parts) > 1:
                            public_id_with_version_and_ext = parts[1]
                            if public_id_with_version_and_ext.startswith('v'):
                                public_id_with_ext = public_id_with_version_and_ext.split('/', 1)[1]
                            else:
                                public_id_with_ext = public_id_with_version_and_ext
                            public_id = public_id_with_ext.rsplit('.', 1)[0]
                            cloudinary.uploader.destroy(public_id)
                            flash(f"DEBUG 3: Imagen antigua ({public_id}) borrada de Cloudinary.", 'warning')
                    except Exception as e:
                        flash(f"DEBUG 3: Error borrando imagen antigua: {e}", 'danger')
                
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    imagen_path = upload_result['secure_url']
                    flash(f"DEBUG 4: Nueva imagen subida. URL: {imagen_path}", 'success')
                except Exception as e:
                    flash(f"DEBUG 4: ERROR al subir a Cloudinary: {e}", 'danger')
            else:
                flash('DEBUG: Formato de archivo no permitido.', 'warning')
        else:
            flash("DEBUG 2: No se subió una nueva imagen.", 'info')

        # --- 5. Actualizar la base de datos ---
        flash(f"DEBUG 5: Guardando en DB con imagen_path: {imagen_path}", 'info')
        conn.execute('''UPDATE pedidos SET 
                         nombre_cliente = ?, forma_contacto = ?, contacto_detalle = ?, direccion_entrega = ?, 
                         producto = ?, detalles = ?, precio = ?, anticipo = ?, imagen_path = ?, 
                         estado_pago = ?, estado_pedido = ? 
                         WHERE id = ?''',
                     (nombre_cliente, forma_contacto, contacto_detalle, direccion_entrega, producto, detalles, precio, anticipo, imagen_path, estado_pago, estado_pedido, id))
        conn.commit()
        conn.close()
        
        flash('¡Pedido actualizado correctamente!', 'success')
        return redirect(url_for('index'))

@app.route('/delete_pedido/<int:id>', methods=['POST'])
@login_required
def delete_pedido(id):
    conn = get_db_connection()
    pedido = conn.execute('SELECT imagen_path FROM pedidos WHERE id = ?', (id,)).fetchone()
    
    if pedido and pedido['imagen_path'] and pedido['imagen_path'].startswith('http'):
        imagen_url = pedido['imagen_path']
        try:
            parts = imagen_url.split('/upload/')
            if len(parts) > 1:
                public_id_with_version_and_ext = parts[1]
                if public_id_with_version_and_ext.startswith('v'):
                    first_slash_after_v = public_id_with_version_and_ext.find('/')
                    if first_slash_after_v != -1:
                        public_id_with_ext = public_id_with_version_and_ext[first_slash_after_v + 1:]
                    else:
                        public_id_with_ext = public_id_with_version_and_ext
                else:
                    public_id_with_ext = public_id_with_version_and_ext

                last_dot_index = public_id_with_ext.rfind('.')
                if last_dot_index != -1:
                    public_id = public_id_with_ext[:last_dot_index]
                else:
                    public_id = public_id_with_ext
                
                cloudinary.uploader.destroy(public_id)
                print(f"Imagen {public_id} eliminada de Cloudinary.")
            else:
                print(f"No se pudo analizar la URL de Cloudinary para public_id: {imagen_url}")

        except Exception as e:
            print(f"Error al eliminar la imagen de Cloudinary: {e}")

    conn.execute('DELETE FROM pedidos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Pedido eliminado.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
