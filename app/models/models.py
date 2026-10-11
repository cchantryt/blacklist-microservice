
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

# Instancia global de SQLAlchemy para registrar los modelos de la app.
db = SQLAlchemy()


class Blacklist(db.Model):
    # Nombre de la tabla en la base de datos.
    __tablename__ = "blacklists"

    # Identificador único del registro en la lista negra.
    id = db.Column(db.Integer, primary_key=True)

    # Correo electrónico bloqueado. Debe ser único y se indexa para búsquedas rápidas.
    email = db.Column(
        db.String(320), unique=True, nullable=False, index=True
    )

    # UUID de la aplicación que emitió el bloqueo.
    app_uuid = db.Column(db.String(36), nullable=False)

    # Motivo del bloqueo, el cual puede quedar vacío si no se especifica.
    blocked_reason = db.Column(db.String(255), nullable=True)

    # Dirección IP asociada al bloqueo detectado.
    ip_address = db.Column(db.String(45), nullable=False)

    # Fecha y hora en que se registró el bloqueo. Se usa UTC por defecto.
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
