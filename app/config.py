import json
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _resolve_aws_region(secret_arn: str) -> str:
    """Región desde env, ARN, o us-east-1 por defecto."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if region:
        return region

    parts = secret_arn.split(":")
    if len(parts) >= 4 and parts[2] == "secretsmanager" and parts[3]:
        return parts[3]

    return "us-east-1"


def _load_secret(secret_arn: str) -> dict | str:
    """Lee un secreto de AWS Secrets Manager (JSON o texto plano)."""
    import boto3
    from botocore.exceptions import ClientError

    region = _resolve_aws_region(secret_arn)
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except ClientError as error:
        raise RuntimeError(
            f"No se pudo leer el secreto {secret_arn}: {error}"
        ) from error

    secret_string = response.get("SecretString")
    if not secret_string:
        raise RuntimeError(f"El secreto {secret_arn} no contiene SecretString")

    try:
        return json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string


def _database_url_from_secret(secret: dict) -> str:
    """Construye la URI SQLAlchemy a partir del JSON de Secrets Manager."""
    if secret.get("DATABASE_URL"):
        return secret["DATABASE_URL"]

    username = secret["username"]
    password = quote_plus(secret["password"])
    host = secret["host"]
    port = secret.get("port", 5432)
    dbname = secret.get("dbname") or secret.get("database")

    if not dbname:
        raise KeyError(
            "El secreto debe incluir 'dbname'/'database' o 'DATABASE_URL'"
        )

    return (
        f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
    )


def get_database_url() -> str:
    """
    Local: usa DATABASE_URL del archivo .env.
    Elastic Beanstalk: si existe DB_SECRET_ARN, lee Secrets Manager.
    """
    secret_arn = os.environ.get("DB_SECRET_ARN")
    if secret_arn:
        secret = _load_secret(secret_arn)
        if not isinstance(secret, dict):
            raise RuntimeError(
                "El secreto de BD debe ser JSON con credenciales o DATABASE_URL"
            )
        return _database_url_from_secret(secret)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Define DATABASE_URL en .env (local) o DB_SECRET_ARN (AWS)"
        )
    return database_url


def _jwt_secret_from_dict(secret: dict) -> str:
    """Extrae la clave JWT de un JSON de Secrets Manager (varios nombres posibles)."""
    for key in (
        "JWT_SECRET_KEY",
        "jwt_secret_key",
        "jwt_secret",
        "secret",
        "secret_key",
        "key",
    ):
        value = secret.get(key)
        if isinstance(value, str) and value:
            return value

    # Si el secreto es key/value con una sola entrada string, úsala.
    string_values = [v for v in secret.values() if isinstance(v, str) and v]
    if len(string_values) == 1:
        return string_values[0]

    raise RuntimeError(
        "El secreto JWT debe ser texto plano o JSON con una clave "
        f"reconocida. Claves encontradas: {list(secret.keys())}"
    )


def get_jwt_secret_key() -> str:
    """
    Local: usa JWT_SECRET_KEY del archivo .env.
    Elastic Beanstalk: si existe JWT_SECRET_ARN, lee Secrets Manager.
    """
    secret_arn = os.environ.get("JWT_SECRET_ARN")
    if secret_arn:
        secret = _load_secret(secret_arn)
        if isinstance(secret, str):
            return secret
        return _jwt_secret_from_dict(secret)

    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError(
            "Define JWT_SECRET_KEY en .env (local) o JWT_SECRET_ARN (AWS)"
        )
    return jwt_secret
