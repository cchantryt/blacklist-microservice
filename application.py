# Punto de entrada WSGI para AWS Elastic Beanstalk (gunicorn carga "application:application")
from app.app import app as application

if __name__ == "__main__":
    application.run()
