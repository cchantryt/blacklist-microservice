# Blacklist Microservice

Microservicio REST desarrollado en Python con Flask y PostgreSQL para registrar y consultar correos electrónicos en una lista negra.

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

Si PowerShell bloquea la activación, se puede ejecutar directamente:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Instalar las dependencias

Con el entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
```

## 5. Configurar PostgreSQL

Crear una base de datos llamada `blacklist_db` en PostgreSQL.

Copiar `.env.example` y renombrar la copia a `.env`. Configurar las credenciales de PostgreSQL y una clave secreta propia.

Ejemplo:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:TU_PASSWORD@localhost:5432/blacklist_db
JWT_SECRET_KEY=CAMBIA_POR_UN_SECRETO_LARGO 'Ver paso 7'
```

Reemplazar `TU_PASSWORD` por la contraseña local de PostgreSQL.

## 6. Ejecutar el microservicio

Desde la carpeta raíz del proyecto:

```powershell
python -m app.app
```

La aplicación estará disponible en:

http://127.0.0.1:5000/

La primera ejecución crea las tablas si la aplicación tiene configurado `db.create_all()`.

> **Nota sobre el Procfile:**  
> Se ha incluido un archivo `Procfile` en la raíz del microservicio para facilitar el despliegue en servidores que usen Gunicorn (como AWS Elastic Beanstalk).  
> El comando especificado en el `Procfile` es:  
> ```
> web: gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 15 app.app:app
> ```  
> Esto permite levantar la aplicación con Gunicorn en puerto 8000, lo cual es habitual en producción o contenedores.  
> Para desarrollo local, basta con ejecutar el comando `python -m app.app` como se indica arriba.

## 7. Generar un token JWT

El token se firma con `JWT_SECRET_KEY`. No hace falta generarlo dentro de Beanstalk: si lo firmas localmente con la misma clave de producción, la API desplegada lo aceptará.

### Local (usa `.env`)

```powershell
python -c "from app.app import app; from flask_jwt_extended import create_access_token; app.app_context().push(); print(create_access_token(identity='postman-client'))"
```

### Contra la API en Elastic Beanstalk

Con credenciales AWS que puedan leer el secreto JWT:

```powershell
$env:JWT_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:prod/blacklist/jwt-XXXXXX"
python -c "from app.config import get_jwt_secret_key; from flask import Flask; from flask_jwt_extended import JWTManager, create_access_token; a=Flask(__name__); a.config['JWT_SECRET_KEY']=get_jwt_secret_key(); a.config['JWT_ACCESS_TOKEN_EXPIRES']=False; JWTManager(a); a.app_context().push(); print(create_access_token(identity='postman-client'))"
```

Copiar el token generado para utilizarlo en Postman.

Puede ser necesario desactivar Smart App Control en Windows al generar el token; luego se puede volver a activar.

## 8. Probar los endpoints en Postman

Todas las solicitudes requieren autenticación JWT mediante `Authorization: Bearer TOKEN`.

### Registrar un correo

- Método: `POST`
- URL: `http://127.0.0.1:5000/blacklists`
- Body → raw → JSON:

```json
{
  "email": "prueba@example.com",
  "app_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "blocked_reason": "Prueba del microservicio"
}
```

Se espera una respuesta `201 Created` si el correo se registra correctamente.

### Consultar un correo

- Método: `GET`
- URL: `http://127.0.0.1:5000/blacklists/prueba@example.com`

Se espera una respuesta JSON que indique si el correo está en la lista negra y su motivo de bloqueo.

Consultar la colección de Postman incluida en la carpeta `postman/`, si está disponible, para ver los ejemplos de solicitudes.

## Notas

- No subir el archivo `.env` ni la carpeta `venv/` a GitHub.
- Cada integrante debe configurar su propia base de datos y sus variables de entorno.
- Si aparece un error de PostgreSQL o de sus controladores, revisar la instalación local antes de probar los endpoints.
