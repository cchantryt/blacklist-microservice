import os
import socket

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
)
from marshmallow import Schema, fields, validate, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from .models.models import db, Blacklist

# Versión desplegada. Se incrementa en cada despliegue para validar las estrategias en Beanstalk
APP_VERSION = "1.0.0"

# Carga las variables de entorno .env (en Beanstalk llegan como propiedades del ambiente)
load_dotenv()

# Inicializa la aplicación Flask y su API REST.
app = Flask(__name__)
api = Api(app)

# En Beanstalk la petición pasa por el balanceador (ALB) y por nginx, cada uno agrega
# una entrada en X-Forwarded-For. Se confía en esos dos saltos para obtener la IP real del cliente
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2)

# El enunciado permite un token estático para toda la aplicación, por eso no expira
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

# Sin esto Flask-RESTful captura los errores de JWT y responde 500 en lugar de 401/422
app.config["PROPAGATE_EXCEPTIONS"] = True

# Configuración de la base de datos y autenticación JWT
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]

# Conecta SQLAlchemy a la aplicación y habilita JWT
db.init_app(app)
jwt = JWTManager(app)

# Crea las tablas al iniciar (también bajo gunicorn en Beanstalk). Varias instancias pueden
# arrancar a la vez, así que si otra ya creó la tabla se ignora el error
with app.app_context():
    try:
        db.create_all()
    except SQLAlchemyError:
        db.session.rollback()


# Esquema de validación para la entrada de datos al registrar un correo en la lista negra
class BlacklistInput(Schema):
    # El correo electrónico debe ser válido y no puede estar vacío
    email = fields.Email(required=True)

    # El UUID de la aplicación que emite el bloqueo debe ser un UUID válido
    app_uuid = fields.UUID(required=True)

    # El motivo del bloqueo es opcional y puede ser nulo
    blocked_reason = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255),
    )


# Endpoint para registrar un correo en la lista negra
class Blacklists(Resource):
    # La creación de un registro en la lista negra requiere autenticación JWT
    @jwt_required()
    def post(self):
        try:
            # Valida y deserializa la entrada JSON usando el esquema definido
            data = BlacklistInput().load(request.get_json() or {})
        except ValidationError as error:
            return {"message": "Datos inválidos", "errors": error.messages}, 400

        # Normaliza el email para evitar duplicados por mayúsculas o espacios
        email = data["email"].strip().lower()
        app_uuid = str(data["app_uuid"])
        reason = data.get("blocked_reason")

        # Obtiene la dirección IP del cliente que realiza la solicitud; si no está disponible, se asigna "unknown"
        ip_address = request.remote_addr or "unknown"

        # Crea el registro nuevo en la base de datos
        record = Blacklist(
            email=email,
            app_uuid=app_uuid,
            blocked_reason=reason,
            ip_address=ip_address,
        )

        db.session.add(record)

        try:
            # Guarda el registro; si el email ya existe, se devuelve conflicto.
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"message": "El correo ya está en la lista negra"}, 409

        return {
            "message": "Correo agregado a la lista negra",
            "blacklisted": True,
        }, 201


# Endpoint para consultar si un correo está bloqueado
class BlacklistByEmail(Resource):

    # La consulta también requiere autenticación
    @jwt_required()
    def get(self, email):

        # Normaliza el email como en la creación para comparar correctamente
        email = email.strip().lower()
        record = db.session.query(Blacklist).filter_by(
            email=email
        ).first()

        return {
            "blacklisted": record is not None,
            "blocked_reason": record.blocked_reason if record else None,
        }, 200


# Registra las rutas REST del microservicio.
api.add_resource(Blacklists, "/blacklists")
api.add_resource(BlacklistByEmail, "/blacklists/<string:email>")


# Endpoint raíz: muestra la versión y la instancia que atendió la solicitud
@app.get("/")
def index():
    return jsonify({
        "status": "ok",
        "service": "blacklist-microservice",
        "version": APP_VERSION,
        "instance": socket.gethostname(),
    })


# Endpoint usado por el health check de Beanstalk: también verifica la conexión a RDS
@app.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"status": "error", "database": "unreachable"}), 503
    return jsonify({"status": "ok", "database": "ok", "version": APP_VERSION})


# Respuesta estándar para rutas inexistentes
@app.errorhandler(404)
def not_found(_error):
    return jsonify({"message": "Recurso no encontrado"}), 404


# Inicia el servidor solo cuando se ejecuta directamente este archivo
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
