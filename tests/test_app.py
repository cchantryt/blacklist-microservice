from app.app import APP_VERSION
from app.models.models import Blacklist, db


AUTHORIZATION_HEADER = "Authorization"

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
