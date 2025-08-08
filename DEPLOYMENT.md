# Guía de Despliegue para ROBLEKA Gestor de Pedidos

Esta guía proporciona los pasos esenciales para desplegar la aplicación Flask "ROBLEKA Gestor de Pedidos" en un entorno de producción.

## 1. Requisitos Previos

Asegúrate de tener instalados los siguientes componentes en tu servidor de producción:

*   **Python 3.x**: Se recomienda Python 3.8 o superior.
*   **pip**: El gestor de paquetes de Python (normalmente viene con Python).
*   **Git** (opcional, pero recomendado para clonar el repositorio).

## 2. Configuración del Entorno

### 2.1. Clonar el Repositorio (si aplica)

Si tu código está en un repositorio Git, clónalo:

```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_DIRECTORIO_DEL_PROYECTO>
```

### 2.2. Crear y Activar un Entorno Virtual

Es una buena práctica aislar las dependencias de tu proyecto:

```bash
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

### 2.3. Instalar Dependencias

Una vez activado el entorno virtual, instala las dependencias listadas en `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 3. Configuración de Variables de Entorno

**¡IMPORTANTE!** Nunca hardcodees claves secretas en tu código. La aplicación espera una variable de entorno `SECRET_KEY`.

Configura esta variable antes de iniciar la aplicación. La forma de hacerlo depende de tu sistema operativo y cómo gestiones los procesos:

*   **En Linux/macOS (temporal para la sesión actual):**
    ```bash
    export SECRET_KEY="TU_CLAVE_SECRETA_MUY_SEGURA_Y_LARGA"
    ```
*   **En Windows (temporal para la sesión actual):**
    ```cmd
    set SECRET_KEY="TU_CLAVE_SECRETA_MUY_SEGURA_Y_LARGA"
    ```
*   **Para persistencia:** Utiliza herramientas como `systemd` (Linux), `Supervisor`, o el sistema de gestión de variables de entorno de tu proveedor de hosting (Heroku, AWS Elastic Beanstalk, etc.).

## 4. Base de Datos

La aplicación utiliza SQLite (`pedidos.db`).

*   **Desarrollo:** SQLite es conveniente para el desarrollo y aplicaciones pequeñas. El archivo `pedidos.db` se creará automáticamente si no existe al iniciar la aplicación.
*   **Producción:** Para aplicaciones con mayor concurrencia o que requieran escalabilidad, se recomienda migrar a una base de datos más robusta como **PostgreSQL** o **MySQL**. Esto implicaría:
    *   Instalar el motor de base de datos.
    *   Cambiar la cadena de conexión en `main.py` (o una configuración externa).
    *   Posiblemente usar una ORM como SQLAlchemy para gestionar las migraciones de esquema.

## 5. Servidor de Aplicaciones WSGI

Flask es un microframework y no debe ser ejecutado directamente con `app.run(debug=True)` en producción. Necesitas un servidor WSGI (Web Server Gateway Interface) para servir la aplicación.

Opciones populares:

*   **Gunicorn** (para Linux/macOS):
    ```bash
    pip install gunicorn
    gunicorn -w 4 main:app -b 0.0.0.0:8000
    ```
    (Donde `-w 4` son 4 workers, `main:app` es el módulo y la instancia de la aplicación Flask, y `-b` es la dirección de enlace).

*   **Waitress** (para Windows):
    ```bash
    pip install waitress
    waitress-serve --listen=0.0.0.0:8000 main:app
    ```

## 6. Servidor Web (Proxy Inverso)

Para una configuración de producción robusta, se recomienda colocar un servidor web como **Nginx** o **Apache** delante de tu servidor WSGI. Esto proporciona:

*   **Servicio de archivos estáticos:** Nginx/Apache son mucho más eficientes sirviendo CSS, JavaScript e imágenes.
*   **Balanceo de carga:** Si tienes múltiples instancias de tu aplicación.
*   **SSL/TLS:** Para HTTPS.
*   **Seguridad adicional.**

**Ejemplo de configuración Nginx (simplificado):**

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location /static {
        alias /path/to/your/app/static; # Ruta absoluta a tu carpeta static
    }

    location / {
        proxy_pass http://127.0.0.1:8000; # Dirección de tu servidor WSGI
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. Gestión de Procesos

Para asegurar que tu aplicación se ejecute continuamente y se reinicie en caso de fallos, utiliza un gestor de procesos como `systemd` (Linux) o `Supervisor`.

## 8. Consideraciones Adicionales

*   **Errores:** Configura el registro de errores para que los mensajes se guarden en archivos o se envíen a un servicio de monitoreo.
*   **Backups:** Implementa una estrategia de copia de seguridad para tu base de datos.
*   **HTTPS:** Siempre usa HTTPS en producción.
*   **Firewall:** Configura un firewall para permitir solo el tráfico necesario (puertos 80/443).
*   **Actualizaciones:** Mantén tus dependencias y el sistema operativo actualizados.
