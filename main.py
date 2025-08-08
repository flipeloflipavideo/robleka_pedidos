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

# --- DEBUGGING CLOUDINARY ENV VARS ---
print("--- VARIABLES DE ENTORNO DE CLOUDINARY ---")
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')
print(f"Cloud Name: {cloud_name}")
print(f"API Key: {api_key}")
print(f"API Secret: {'Presente' if api_secret else 'AUSENTE'}") # No mostramos el secreto completo por seguridad
print("-----------------------------------------")

cloudinary.config(
    cloud_name = cloud_name,
    api_key = api_key,
    api_secret = api_secret,
    secure=True
)

app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_dev_key')
DATABASE = 'pedidos.db'
PEDIDOS_POR_PAGINA = 10

# ... (resto del código sin cambios) ...
