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
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey_dev_fallback')
DATABASE = 'pedidos.db'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PEDIDOS_POR_PAGINA = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Configuración de Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'robleka':
        return User('robleka')
    return None

# --- Funciones de la aplicación ---
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
        # ... (código de añadir sin cambios)
        pass

@app.route('/update_pedido/<int:id>', methods=['POST'])
@login_required
def update_pedido(id):
    print("--- INICIO DE UPDATE_PEDIDO ---")
    try:
        if request.method == 'POST':
            print("Request method is POST.")
            # ... (resto del código de la función)
            
            # --- 4. Lógica de la imagen con LOGGING ---
            conn = get_db_connection()
            pedido_actual = conn.execute('SELECT imagen_path FROM pedidos WHERE id = ?', (id,)).fetchone()
            imagen_path = pedido_actual['imagen_path'] if pedido_actual else None
            print(f"LOG: Imagen actual en DB: {imagen_path}")
            
            nueva_imagen_subida = 'imagen' in request.files and request.files['imagen'].filename != ''
            print(f"LOG: ¿Se ha subido una nueva imagen? {nueva_imagen_subida}")

            if nueva_imagen_subida:
                file = request.files['imagen']
                print(f"LOG: Nombre del archivo subido: {file.filename}")
                if allowed_file(file.filename):
                    print("LOG: El formato del archivo es permitido.")
                    # ... (lógica de borrado de imagen antigua)
                    
                    # Subir la nueva imagen
                    try:
                        print("LOG: Intentando subir a Cloudinary...")
                        upload_result = cloudinary.uploader.upload(file)
                        imagen_path = upload_result['secure_url']
                        print(f"LOG: Subida a Cloudinary exitosa. URL: {imagen_path}")
                        flash('Imagen subida a Cloudinary con éxito.', 'success')
                    except Exception as e:
                        print(f"!!!!!!!!!! ERROR EN CLOUDINARY: {e} !!!!!!!!!!")
                        flash(f'Error CRÍTICO al subir a Cloudinary: {e}', 'danger')
                else:
                    print("LOG: El formato del archivo NO es permitido.")
                    flash('Formato de archivo no permitido.', 'warning')
            
            # ... (lógica de actualización de la base de datos)
            print(f"LOG: Actualizando DB con imagen_path: {imagen_path}")
            conn.execute('''UPDATE pedidos SET 
                             nombre_cliente = ?, forma_contacto = ?, contacto_detalle = ?, direccion_entrega = ?, 
                             producto = ?, detalles = ?, precio = ?, anticipo = ?, imagen_path = ?, 
                             estado_pago = ?, estado_pedido = ? 
                             WHERE id = ?''', (id,))
            conn.commit()
            conn.close()
            
            print("--- FIN DE UPDATE_PEDIDO ---")
            flash('¡Pedido actualizado correctamente!', 'success')
            return redirect(url_for('index'))

    except Exception as e:
        print(f"!!!!!!!!!! ERROR GENERAL EN UPDATE_PEDIDO: {e} !!!!!!!!!!")
        flash("Error fatal en el servidor al actualizar el pedido.", "danger")
        return redirect(url_for('index'))

@app.route('/delete_pedido/<int:id>', methods=['POST'])
@login_required
def delete_pedido(id):
    # ... (código de eliminar sin cambios)
    pass

if __name__ == '__main__':
    app.run(debug=True)
