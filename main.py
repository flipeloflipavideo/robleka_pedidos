from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
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

# --- Configuración de Cloudinary ---
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_dev_key')

# --- Configuración de SQLAlchemy para PostgreSQL ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

PEDIDOS_POR_PAGINA = 10

# --- Definición del Modelo de Pedido con SQLAlchemy ---
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    forma_contacto = db.Column(db.String(50), nullable=False)
    contacto_detalle = db.Column(db.String(100))
    direccion_entrega = db.Column(db.String(200))
    producto = db.Column(db.String(100), nullable=False)
    detalles = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    anticipo = db.Column(db.Float, default=0.0)
    imagen_path = db.Column(db.String(255))
    estado_pago = db.Column(db.String(50), nullable=False)
    estado_pedido = db.Column(db.String(50), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Pedido {self.id} - {self.nombre_cliente}>'

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
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# No necesitamos get_db_connection() ni init_db() con SQLAlchemy

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
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Obtener los nombres de las columnas del modelo Pedido
    header = [column.name for column in Pedido.__table__.columns]
    writer.writerow(header)
    
    for pedido in pedidos:
        writer.writerow([getattr(pedido, col) for col in header])
    
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
    
    query = Pedido.query

    if search_term:
        query = query.filter(
            (Pedido.nombre_cliente.ilike(f'%{search_term}%')) |\
            (Pedido.producto.ilike(f'%{search_term}%')) |\
            (Pedido.estado_pedido.ilike(f'%{search_term}%'))
        )

    total_pedidos = query.count()
    total_paginas = math.ceil(total_pedidos / PEDIDOS_POR_PAGINA)
    
    pedidos = query.order_by(Pedido.fecha_creacion.desc())
    pedidos = pedidos.paginate(page=page, per_page=PEDIDOS_POR_PAGINA, error_out=False).items
    
    total_facturado_result = db.session.query(
        db.func.sum(db.case(
            (Pedido.estado_pago == 'Pagado Completo', Pedido.precio),
            else_=0
        )) + 
        db.func.sum(db.case(
            (Pedido.estado_pago == 'Anticipo Pagado', Pedido.anticipo),
            else_=0
        ))
    ).scalar()
    total_facturado = total_facturado_result or 0

    monto_pendiente_result = db.session.query(
        db.func.sum(Pedido.precio - Pedido.anticipo)
    ).filter(Pedido.estado_pago != 'Pagado Completo').scalar()
    monto_pendiente = monto_pendiente_result or 0.0

    estados_result = db.session.query(Pedido.estado_pedido, db.func.count(Pedido.id)).group_by(Pedido.estado_pedido).all()
    chart_estados_data = {
        'labels': [row[0] for row in estados_result],
        'data': [row[1] for row in estados_result]
    }

    ingresos_mensuales_result = db.session.query(
        db.func.strftime('%Y-%m', Pedido.fecha_creacion),
        db.func.sum(Pedido.precio)
    ).filter(Pedido.estado_pago == 'Pagado Completo').group_by(1).order_by(1).all()
    chart_ingresos_data = {
        'labels': [row[0] for row in ingresos_mensuales_result],
        'data': [row[1] for row in ingresos_mensuales_result]
    }

    fechas_unicas_result = db.session.query(
        db.func.strftime('%Y-%m-%d', Pedido.fecha_creacion)
    ).distinct().order_by(1).all()
    fechas_unicas = [row[0] for row in fechas_unicas_result]

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
        precio = float(request.form['precio'])
        anticipo = float(request.form.get('anticipo', '0.0'))
        
        errors = []
        if not nombre_cliente: errors.append('El nombre del cliente es obligatorio.')
        if not forma_contacto: errors.append('La forma de contacto es obligatoria.')
        if not producto: errors.append('El producto es obligatorio.')

        if precio <= 0: errors.append('El precio debe ser un número positivo.')
        if anticipo < 0: errors.append('El anticipo no puede ser negativo.')
        if anticipo > precio: errors.append('El anticipo no puede ser mayor que el precio total.')

        if errors:
            for error in errors: flash(error, 'danger')
            return redirect(url_for('index'))

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

        nuevo_pedido = Pedido(
            nombre_cliente=nombre_cliente,
            forma_contacto=forma_contacto,
            contacto_detalle=contacto_detalle,
            direccion_entrega=direccion_entrega,
            producto=producto,
            detalles=detalles,
            precio=precio,
            anticipo=anticipo,
            imagen_path=imagen_path,
            estado_pago=estado_pago,
            estado_pedido=estado_pedido
        )
        db.session.add(nuevo_pedido)
        db.session.commit()
        flash('¡Pedido añadido con éxito!', 'success')
        return redirect(url_for('index'))

@app.route('/update_pedido/<int:id>', methods=['POST'])
@login_required
def update_pedido(id):
    pedido = Pedido.query.get_or_404(id)

    nombre_cliente = request.form['nombre_cliente']
    forma_contacto = request.form['forma_contacto']
    contacto_detalle = request.form['contacto_detalle']
    direccion_entrega = request.form['direccion_entrega']
    producto = request.form['producto']
    detalles = request.form['detalles']
    precio = float(request.form['precio'])
    anticipo = float(request.form.get('anticipo', '0.0'))
    estado_pedido = request.form['estado_pedido']

    errors = []
    if not nombre_cliente: errors.append('El nombre del cliente es obligatorio.')
    if not forma_contacto: errors.append('La forma de contacto es obligatoria.')
    if not producto: errors.append('El producto es obligatorio.')
    if precio <= 0: errors.append('El precio debe ser un número positivo.')
    if anticipo < 0: errors.append('El anticipo no puede ser negativo.')
    if anticipo > precio: errors.append('El anticipo no puede ser mayor que el precio total.')

    if errors:
        for error in errors: flash(error, 'danger')
        return redirect(url_for('index'))

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

    # Lógica de la imagen
    imagen_path = pedido.imagen_path # Mantener la imagen existente por defecto
    if 'imagen' in request.files and request.files['imagen'].filename != '':
        file = request.files['imagen']
        if allowed_file(file.filename):
            try:
                # Borrar imagen antigua de Cloudinary si existe
                if imagen_path and imagen_path.startswith('http'):
                    public_id = imagen_path.split('/')[-1].rsplit('.', 1)[0]
                    cloudinary.uploader.destroy(public_id)
                
                # Subir nueva imagen a Cloudinary
                upload_result = cloudinary.uploader.upload(file)
                imagen_path = upload_result['secure_url']
                flash('Imagen actualizada en Cloudinary.', 'success')
            except Exception as e:
                print(f"ERROR CLOUDINARY: {e}")
                flash(f'Error al subir a Cloudinary: {e}', 'danger')
        else:
            flash('Formato de archivo no permitido.', 'warning')

    # Actualizar el objeto pedido con los nuevos datos
    pedido.nombre_cliente = nombre_cliente
    pedido.forma_contacto = forma_contacto
    pedido.contacto_detalle = contacto_detalle
    pedido.direccion_entrega = direccion_entrega
    pedido.producto = producto
    pedido.detalles = detalles
    pedido.precio = precio
    pedido.anticipo = anticipo
    pedido.imagen_path = imagen_path
    pedido.estado_pago = estado_pago
    pedido.estado_pedido = estado_pedido

    db.session.commit()
    flash('¡Pedido actualizado correctamente!', 'success')
    return redirect(url_for('index'))

@app.route('/delete_pedido/<int:id>', methods=['POST'])
@login_required
def delete_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    
    # Borrar imagen de Cloudinary si existe
    if pedido.imagen_path and pedido.imagen_path.startswith('http'):
        try:
            public_id = pedido.imagen_path.split('/')[-1].rsplit('.', 1)[0]
            cloudinary.uploader.destroy(public_id)
        except Exception as e:
            print(f"Error deleting image from Cloudinary: {e}")

    db.session.delete(pedido)
    db.session.commit()
    flash('Pedido eliminado.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea las tablas si no existen
    app.run(debug=True)
