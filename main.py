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

# --- Configuración ROBUSTA de Cloudinary ---
# Asegurarse de que las variables de entorno se cargan
if not all(os.environ.get(key) for key in ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']):
    print("ALERTA: Faltan variables de entorno de Cloudinary. La subida de imágenes fallará.")

cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True # Forzar HTTPS
)

app.secret_key = os.environ.get('SECRET_KEY', 'a_fallback_dev_key')
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
    # ... (sin cambios)
    pass

init_db()

# --- Rutas de la aplicación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (sin cambios)
    pass

@app.route('/logout')
@login_required
def logout():
    # ... (sin cambios)
    pass

@app.route('/export/csv')
@login_required
def export_csv():
    # ... (sin cambios)
    pass

@app.route('/')
@login_required
def index():
    # ... (sin cambios)
    pass

@app.route('/add_pedido', methods=['POST'])
@login_required
def add_pedido():
    # ... (sin cambios)
    pass

@app.route('/update_pedido/<int:id>', methods=['POST'])
@login_required
def update_pedido(id):
    # ... (código de validación y lógica de negocio sin cambios)
    
    conn = get_db_connection()
    pedido_actual = conn.execute('SELECT imagen_path FROM pedidos WHERE id = ?', (id,)).fetchone()
    imagen_path = pedido_actual['imagen_path'] if pedido_actual else None
    
    if 'imagen' in request.files and request.files['imagen'].filename != '':
        file = request.files['imagen']
        if allowed_file(file.filename):
            try:
                # Borrar imagen antigua si existe
                if imagen_path and imagen_path.startswith('http'):
                    public_id = imagen_path.split('/')[-1].rsplit('.', 1)[0]
                    cloudinary.uploader.destroy(public_id)
                
                # Subir nueva imagen
                upload_result = cloudinary.uploader.upload(file)
                imagen_path = upload_result['secure_url']
                flash('Imagen actualizada en Cloudinary.', 'success')
            except Exception as e:
                print(f"ERROR CLOUDINARY: {e}")
                flash(f'Error al subir a Cloudinary: {e}', 'danger')
    
    # --- CORRECCIÓN CRÍTICA: Pasar todos los parámetros a execute() ---
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
    # ... (sin cambios)
    pass

if __name__ == '__main__':
    app.run(debug=True)