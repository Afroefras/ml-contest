import os
import pytz
import pandas as pd
from sqlalchemy import func
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from eval_predictions import PredictionEvaluator, load_students
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///submissions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'tu_clave_secreta'  # Necesario para flash messages

# Asegúrate de que la carpeta de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Definir el modelo para la base de datos
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Submission {self.student_id}>'

@app.route('/', methods=['GET', 'POST'])
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
    
    # Obtener el ranking
    submissions = db.session.query(
        Submission.student_name,
        func.max(Submission.score).label('max_score'),
        func.min(Submission.score).label('min_score'),
        func.avg(Submission.score).label('avg_score'),
        func.count(Submission.score).label('score_count'),
        func.max(Submission.timestamp).label('last_update_at')
    ).group_by(Submission.student_name).order_by(
            func.max(Submission.score).desc(),
            func.count(Submission.score).asc(),
            func.min(Submission.score).desc(),
            func.max(Submission.timestamp).asc()
        ).all()
    
    return render_template('index.html', submissions=submissions)

@app.route('/health')
def health():
    """Endpoint para verificar que la aplicación está funcionando"""
    return {'status': 'ok'}

def create_tables():
    with app.app_context():
        db.create_all()

# Llamamos a la función explícitamente antes de ejecutar la app
if __name__ == '__main__':
    create_tables()  # Crear tablas antes de iniciar la app
    app.run(host='0.0.0.0', port=5000, debug=True)