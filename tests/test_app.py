from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app.app import APP_VERSION
from app.models.models import Blacklist, db


AUTHORIZATION_HEADER = "Authorization"
APP_UUID = "123e4567-e89b-12d3-a456-426614174000"

# Función auxiliar para generar encabezados de autorización con un token JWT
def auth_headers(access_token):
    return {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

# Prueba para verificar que la ruta de índice devuelve el estado del servicio
def test_index_returns_service_status(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["service"] == "blacklist-microservice"
    assert body["version"] == APP_VERSION
    assert body["instance"]

# Prueba para verificar que la ruta de salud devuelve el estado de la base de datos 
def test_health_returns_database_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "database": "ok",
        "version": APP_VERSION,
    }

# Prueba para verificar que se puede crear un registro en la lista negra
def test_post_blacklist_creates_record(client, access_token):
    response = client.post(
        "/blacklists",
        json={
            "email": "test@Example.com",
            "app_uuid": "123e4567-e89b-12d3-a456-426614174000",
            "blocked_reason": "Prueba unitaria",
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "message": "Correo agregado a la lista negra",
        "blacklisted": True,
    }

    with client.application.app_context():
        record = db.session.query(Blacklist).filter_by(
            email="test@example.com"
        ).first()
        assert record is not None
        assert record.blocked_reason == "Prueba unitaria"

# Prueba para verificar que se puede obtener un registro bloqueado por correo electrónico
def test_get_blacklist_by_email_returns_blocked_record(
    client, access_token
):
    with client.application.app_context():
        db.session.add(
            Blacklist(
                email="blocked@example.com",
                app_uuid="123e4567-e89b-12d3-a456-426614174000",
                blocked_reason="Fraude",
                ip_address="127.0.0.1",
            )
        )
        db.session.commit()

    response = client.get(
        "/blacklists/blocked@example.com",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "blacklisted": True,
        "blocked_reason": "Fraude",
    }

# Prueba para verificar que una ruta desconocida devuelve un mensaje de recurso no encontrado
def test_unknown_route_returns_not_found_message(client):
    response = client.get("/route-that-does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {"message": "Recurso no encontrado"}

# Prueba para verificar que el health check responde 503 si la base de datos no está disponible (mock)
def test_health_returns_503_when_database_is_unreachable(client):
    with patch.object(
        db.session, "execute", side_effect=OperationalError("SELECT 1", {}, None)
    ):
        response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unreachable"}

# Prueba para verificar que el POST guarda la IP de origen y la fecha de la solicitud
def test_post_blacklist_stores_ip_and_timestamp(client, access_token):
    response = client.post(
        "/blacklists",
        json={"email": "ip@example.com", "app_uuid": APP_UUID},
        headers=auth_headers(access_token),
        environ_base={"REMOTE_ADDR": "10.0.0.7"},
    )

    assert response.status_code == 201

    with client.application.app_context():
        record = db.session.query(Blacklist).filter_by(
            email="ip@example.com"
        ).first()
        assert record.ip_address == "10.0.0.7"
        assert record.created_at is not None
        assert record.blocked_reason is None

# Prueba para verificar que el POST sin token es rechazado
def test_post_blacklist_without_token_returns_401(client):
    response = client.post(
        "/blacklists",
        json={"email": "test@example.com", "app_uuid": APP_UUID},
    )

    assert response.status_code == 401

# Prueba para verificar que el POST rechaza un email inválido
def test_post_blacklist_with_invalid_email_returns_400(client, access_token):
    response = client.post(
        "/blacklists",
        json={"email": "no-es-un-email", "app_uuid": APP_UUID},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]

# Prueba para verificar que el POST exige un app_uuid válido
def test_post_blacklist_with_invalid_app_uuid_returns_400(client, access_token):
    response = client.post(
        "/blacklists",
        json={"email": "test@example.com", "app_uuid": "123"},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]

# Prueba para verificar que el motivo del bloqueo no supera 255 caracteres
def test_post_blacklist_with_long_reason_returns_400(client, access_token):
    response = client.post(
        "/blacklists",
        json={
            "email": "test@example.com",
            "app_uuid": APP_UUID,
            "blocked_reason": "x" * 256,
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 400
    assert "blocked_reason" in response.get_json()["errors"]

# Prueba para verificar que no se puede agregar dos veces el mismo email
def test_post_blacklist_duplicate_email_returns_409(client, access_token):
    payload = {"email": "dup@example.com", "app_uuid": APP_UUID}

    first = client.post("/blacklists", json=payload, headers=auth_headers(access_token))
    second = client.post(
        "/blacklists",
        json={"email": "DUP@example.com", "app_uuid": APP_UUID},
        headers=auth_headers(access_token),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json() == {"message": "El correo ya está en la lista negra"}

# Prueba para verificar que un email que no está en la lista negra devuelve blacklisted=False
def test_get_blacklist_by_email_returns_false_when_not_blocked(
    client, access_token
):
    response = client.get(
        "/blacklists/libre@example.com",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "blacklisted": False,
        "blocked_reason": None,
    }

# Prueba para verificar que el GET sin token es rechazado
def test_get_blacklist_by_email_without_token_returns_401(client):
    response = client.get("/blacklists/blocked@example.com")

    assert response.status_code == 401
