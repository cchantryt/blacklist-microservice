# Blacklist Microservice

Microservicio REST desarrollado en Python con Flask y PostgreSQL para registrar y consultar correos electrónicos en una lista negra. La aplicación usa JWT para proteger los endpoints de la lista y puede desplegarse en AWS Elastic Beanstalk.

## 1. Requisitos previos

Instalar y tener disponible:

- Python 3.11 o una versión compatible.
- PostgreSQL.
- Git.
- Postman.

## 2. Descargar el proyecto

```bash
git clone https://github.com/cchantryt/blacklist-microservice.git
cd blacklist-microservice
```

## 3. Crear y activar el entorno virtual

En Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, se puede usar directamente el ejecutable del entorno:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Instalar las dependencias

Con el entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
```

## 5. Configurar el entorno local

Crear una base de datos llamada `blacklist_db` en PostgreSQL.

Copiar `.env.example` y renombrar la copia a `.env`. En ese archivo, configurar `DATABASE_URL` con la URI completa de PostgreSQL y `JWT_SECRET_KEY` con una clave secreta larga y propia. No subir `.env` a GitHub.

## 6. Ejecutar el microservicio

Desde la carpeta raíz del proyecto:

```powershell
python -m app.app
```

La aplicación estará disponible en `http://127.0.0.1:5000/`.

La aplicación crea las tablas al iniciar si la conexión a PostgreSQL está disponible. También expone:

- `GET /`: devuelve el estado, la versión y el nombre de la instancia.
- `GET /health`: comprueba el estado de la aplicación y la conexión a PostgreSQL.

## 7. Despliegue en AWS Elastic Beanstalk

El archivo `Procfile` usa Gunicorn mediante el punto de entrada WSGI `application:application`:

```text
web: gunicorn --bind 127.0.0.1:8000 --workers 3 --access-logfile - application:application
```

En Elastic Beanstalk, la aplicación obtiene las credenciales desde AWS Secrets Manager:

- `DB_SECRET_ARN`: ARN del secreto con las credenciales de PostgreSQL o con `DATABASE_URL`.
- `JWT_SECRET_ARN`: ARN del secreto que contiene la clave JWT como texto plano o como JSON con la propiedad `JWT_SECRET_KEY`.
- `AWS_REGION` o `AWS_DEFAULT_REGION`: región de AWS del secreto. Si no se define, se usa la región incluida en el ARN.

El archivo `.ebextensions/options.config` configura estas variables para el entorno. Sustituir sus ARN por los de la cuenta correspondiente y conceder al rol de la instancia de Elastic Beanstalk permiso `secretsmanager:GetSecretValue`. No publicar credenciales ni valores secretos en el repositorio.

## 8. Generar un token JWT

El token se firma con la misma clave configurada en `JWT_SECRET_KEY` o almacenada en `JWT_SECRET_ARN`. El token generado localmente solo funcionará contra AWS si se usa exactamente la misma clave de producción.

### Local usando `.env`

```powershell
python -c "from app.app import app; from flask_jwt_extended import create_access_token; app.app_context().push(); print(create_access_token(identity='postman-client'))"
```

### Usando el secreto JWT de AWS

Con credenciales AWS que tengan permiso para leer el secreto:

```powershell
$env:JWT_SECRET_ARN = "ARN_DEL_SECRETO_JWT"
python -c "from app.config import get_jwt_secret_key; from flask import Flask; from flask_jwt_extended import JWTManager, create_access_token; a=Flask(__name__); a.config['JWT_SECRET_KEY']=get_jwt_secret_key(); a.config['JWT_ACCESS_TOKEN_EXPIRES']=False; JWTManager(a); a.app_context().push(); print(create_access_token(identity='postman-client'))"
```

Copiar el token generado y enviarlo en el encabezado `Authorization` usando el esquema `Bearer`.

## 9. Probar los endpoints

Las solicitudes a `/blacklists` requieren autenticación JWT mediante un encabezado `Authorization` con esquema `Bearer`. Los endpoints `/` y `/health` no requieren token.

### Registrar un correo

- Método: `POST`
- URL local: `http://127.0.0.1:5000/blacklists`
- Body → raw → JSON:

```json
{
  "email": "prueba@example.com",
  "app_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "blocked_reason": "Prueba del microservicio"
}
```

Se espera una respuesta `201 Created` si el correo se registra correctamente. Si el correo ya existe, la API responde `409 Conflict`.

### Consultar un correo

- Método: `GET`
- URL: `http://127.0.0.1:5000/blacklists/prueba@example.com`

Se espera una respuesta JSON que indique si el correo está en la lista negra y su motivo de bloqueo.

También se puede importar la colección de Postman incluida en la carpeta `postman/` y configurar la variable `baseURL`.

## 10. Ejecutar las pruebas unitarias

Las pruebas automatizadas cubren al menos un escenario para cada endpoint:

- `GET /`
- `GET /health`
- `POST /blacklists`
- `GET /blacklists/<email>`
- Respuesta `404` para rutas inexistentes

Se usa una base de datos SQLite en memoria, por lo que las pruebas no necesitan PostgreSQL ni modifican datos locales. Para ejecutarlas:

```powershell
.\venv\Scripts\python.exe -m pytest tests -q
```

El resultado esperado es que todos los escenarios finalicen correctamente.

## Notas

- No subir los archivos `.env`, secretos ni la carpeta `venv/` a GitHub.
- Cada integrante debe configurar su propia base de datos y sus variables de entorno.
- Si aparece un error de PostgreSQL o de sus controladores, revisar la instalación local antes de probar los endpoints.
