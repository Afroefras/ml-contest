import os
from config import *
from models import Submission
from extensions import db, csrf, limiter

from sqlalchemy import func
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash

import pytz
import pandas as pd
from datetime import datetime
from eval_predictions import PredictionEvaluator, load_students, allowed_file

# Crear la app
app = Flask(__name__)

# Cargar la configuración ANTES de instanciar SQLAlchemy
app.config.from_object('config')
print(f"DATABASE_URL configurado como: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"Tipo de base de datos: {app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0] if app.config['SQLALCHEMY_DATABASE_URI'] else 'None'}")

# Primero inicializa las extensiones
db.init_app(app)
csrf.init_app(app)
limiter.init_app(app)

# Y después intenta la conexión
with app.app_context():
    try:
        db.engine.connect()
        print("¡Conexión a la base de datos establecida con éxito!")
        # Verifica si la tabla existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        print(f"Tablas existentes: {inspector.get_table_names()}")
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")

# Asegúrate de que la carpeta de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Manejo de muchos requests
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template("too_many_requests.html"), 429

# Lógica de index.html
@app.route('/', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def index():
    if request.method == 'POST':
        # Verificar si se proporcionó un nombre
        student_id = request.form.get('student_id')
        if not student_id:
            flash('Ingresa tu número de registro.')
            return redirect(url_for('index'))

        try:
            student_id = int(student_id)
        except ValueError:
            flash('El número de registro debe ser un entero.')
            return redirect(url_for('index'))
        
        students = load_students(csv_path='students.csv')

        try:
            student_name = students[student_id]
        except KeyError:
            flash(f'El número de registro "{student_id}" no está registrado en esta clase.')
            return redirect(url_for('index'))
        
        # Verificar si se subió un archivo
        if 'file' not in request.files:
            flash('No se ha subido ningún archivo.')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No se ha seleccionado ningún archivo.')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('El archivo debe tener extensión .csv')
            return redirect(url_for('index'))
        
        if file:
            try:
                predictions = pd.read_csv(file)
            except Exception as e:
                return 0, f"Error al leer el archivo de predicciones: {str(e)}"
            
            # Evaluar predicciones
            pe = PredictionEvaluator(true_labels_path='true_labels.csv')
            score, error = pe.evaluate_predictions(predictions, task_type='classification')
            
            if error:
                flash(f'Error: {error}')
                return redirect(url_for('index'))
            
            # Guardar el archivo
            now_datetime = datetime.now(pytz.timezone('America/Mexico_City'))
            filename = secure_filename(f"{student_id}_{now_datetime.strftime('%Y%m%d_%H%M%S')}.csv")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            predictions.to_csv(filepath, index=False)
            
            # Guardar en la base de datos
            submission = Submission(
                student_id=student_id,
                student_name=student_name,
                filename=filename,
                score=score,
                timestamp=now_datetime,
            )
            db.session.add(submission)
            db.session.commit()
            
            flash(f'Muy bien, {student_name}! Tu score es: {score:.1%}')
            return redirect(url_for('index'))
    
    # # Obtener el ranking
    # submissions = db.session.query(
    #     Submission.student_name,
    #     func.max(Submission.score).label('max_score'),
    #     func.min(Submission.score).label('min_score'),
    #     func.avg(Submission.score).label('avg_score'),
    #     func.count(Submission.score).label('score_count'),
    #     func.max(Submission.timestamp).label('last_update_at')
    # ).group_by(Submission.student_name).order_by(
    #         func.max(Submission.score).desc(),
    #         func.count(Submission.score).asc(),
    #         func.min(Submission.score).desc(),
    #         func.max(Submission.timestamp).asc()
    #     ).all()
    submissions = []
    return render_template('index.html', submissions=submissions)


@app.route('/health')
def health():
    """Endpoint para verificar que la aplicación está funcionando"""
    return {'status': 'ok'}


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)