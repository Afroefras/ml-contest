# Usa una imagen base de Python 3.10.6
FROM python:3.10.6-slim

# Configura variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos necesarios
COPY . /app/

# Instala pipenv
RUN pip install --no-cache-dir pipenv

# Instala las dependencias usando Pipfile
# Si no tienes un Pipfile, comenta estas líneas y usa requirements.txt
RUN pipenv install --deploy --system

# Alternativa: si prefieres usar requirements.txt
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# Asegúrate de que la carpeta de uploads exista
RUN mkdir -p uploads

# Expone el puerto 5000
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]