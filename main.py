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
import importlib
import math

import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)

# --- Configuración de Cloudinary ---
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_dev_key')

# --- Ajuste de URL para PostgreSQL ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# --- Configuración de SQLAlchemy ---
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- CREACIÓN DE TABLAS ---
with app.app_context():
    db.create_all()

PEDIDOS_POR_PAGINA = 10

# --- Modelo ---
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

# --- Flask-Login ---
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

# --- Funciones auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- Rutas ---
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
            (Pedido.nombre_cliente.ilike(f'%{search_term}%')) |
            (Pedido.producto.ilike(f'%{search_term}%')) |
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

    ingresos_mensuales_expr = db.func.to_char(Pedido.fecha_creacion, 'YYYY-MM')
    ingresos_mensuales_result = db.session.query(
        ingresos_mensuales_expr,
        db.func.sum(Pedido.precio)
    ).filter(Pedido.estado_pago == 'Pagado Completo').group_by(ingresos_mensuales_expr).order_by(ingresos_mensuales_expr).all()
    chart_ingresos_data = {
        'labels': [row[0] for row in ingresos_mensuales_result],
        'data': [row[1] for row in ingresos_mensuales_result]
    }

    # FIX: evitar order_by(1), usar la expresión directamente
    fechas_unicas_expr = db.func.to_char(Pedido.fecha_creacion, 'YYYY-MM-DD')
    fechas_unicas_result = db.session.query(
        fechas_unicas_expr
    ).distinct().order_by(fechas_unicas_expr).all()
    fechas_unicas = [row[0] for row in fechas_unicas_result]

    return render_template(
        'index.html',
        pedidos=pedidos,
        fechas_pedidos_json=json.dumps(fechas_unicas),
        total_facturado=total_facturado,
        monto_pendiente=monto_pendiente,
        chart_estados_data=json.dumps(chart_estados_data),
        chart_ingresos_data=json.dumps(chart_ingresos_data),
        page=page,
        total_paginas=total_paginas,
        search_term=search_term
    )

# --- Rutas de añadir, actualizar y borrar pedidos ---
# (el resto del código que ya tienes para add_pedido, update_pedido y delete_pedido se mantiene igual)

if __name__ == '__main__':
    app.run(debug=True)
