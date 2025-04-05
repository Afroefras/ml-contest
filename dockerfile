# Usa una imagen base de Python
FROM python:3.10

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia los archivos de Pipenv para instalar las dependencias
COPY Pipfile Pipfile.lock ./

# Instala pipenv y las dependencias definidas en el Pipfile
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --ignore-pipfile

# Copia el resto de la aplicación al contenedor
COPY . .

# Expone el puerto en el que la app va a correr
EXPOSE 5000

# Comando para iniciar la aplicación usando pipenv
CMD ["pipenv", "run", "python", "app.py"]
