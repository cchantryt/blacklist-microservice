import os

import pytest

# Configuración de variables de entorno para pruebas
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
# Evita que las pruebas lean Secrets Manager si el entorno (p. ej. CodeBuild) define los ARN
os.environ.pop("DB_SECRET_ARN", None)
os.environ.pop("JWT_SECRET_ARN", None)

from app.app import app
from app.models.models import db

# Fixture para crear un cliente de prueba de Flask
@pytest.fixture
def client():
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()

# Fixture para crear un token de acceso JWT para pruebas
@pytest.fixture
def access_token():
    with app.app_context():
        from flask_jwt_extended import create_access_token

        return create_access_token(identity="test-client")
