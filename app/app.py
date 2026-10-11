
import os
from uuid import UUID

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
)
from marshmallow import Schema, fields, validate, ValidationError
from sqlalchemy.exc import IntegrityError

from .models.models import db, Blacklist

# Carga las variables de entorno desde un archivo .env.
load_dotenv()

# Inicializa la aplicación Flask y su API REST.
app = Flask(__name__)
api = Api(app)

# ELIMINAR ESTA LINEA EN PRODUCCION
# Configuración de la expiración de tokens JWT. Se desactiva la expiración para pruebas.
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

# Configuración de la base de datos y autenticación JWT.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]

# Conecta SQLAlchemy a la aplicación y habilita JWT.
db.init_app(app)
jwt = JWTManager(app)


# Define la validación esperada para crear un registro de bloqueo.
class BlacklistInput(Schema):
    # Email válido requerido para identificar al usuario afectado.
    email = fields.Email(required=True)

    # UUID de la aplicación que reporta el bloqueo.
    app_uuid = fields.UUID(required=True)

    # Motivo opcional del bloqueo, con longitud máxima de 255 caracteres.
    blocked_reason = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255),
    )


# Endpoint para registrar un correo en la lista negra.
class Blacklists(Resource):
    # Cada solicitud requiere autenticación JWT.
    @jwt_required()
    def post(self):
        try:
            # Valida y convierte los datos JSON recibidos.
            data = BlacklistInput().load(request.get_json() or {})
        except ValidationError as error:
            return {"message": "Datos inválidos", "errors": error.messages}, 400

        # Normaliza el email para evitar duplicados por mayúsculas o espacios.
        email = data["email"].strip().lower()
        app_uuid = str(data["app_uuid"])
        reason = data.get("blocked_reason")

        # Detrás del proxy de AWS debe configurarse
        # correctamente la confianza en los encabezados reenviados.
        ip_address = request.remote_addr or "unknown"

        # Crea el registro nuevo en la base de datos.
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


# Endpoint para consultar si un correo está bloqueado.
class BlacklistByEmail(Resource):
    # La consulta también requiere autenticación.
    @jwt_required()
    def get(self, email):
        # Normaliza el email como en la creación para comparar correctamente.
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


# Endpoint de salud para verificar que el servicio está funcionando.
@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "blacklist-microservice"})


# Respuesta estándar para rutas inexistentes.
@app.errorhandler(404)
def not_found(_error):
    return jsonify({"message": "Recurso no encontrado"}), 404


# Inicia el servidor solo cuando se ejecuta directamente este archivo.
if __name__ == "__main__":
    with app.app_context():
        # Crea las tablas necesarias si aún no existen.
        db.create_all()

    app.run(host="127.0.0.1", port=5000, debug=True)
