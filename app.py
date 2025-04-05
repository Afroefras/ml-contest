import os
import pandas as pd
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sklearn.metrics import f1_score, mean_absolute_percentage_error
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
    student_name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Submission {self.student_name}>'

# Función para evaluar las predicciones
def evaluate_predictions(predictions_file, task_type='classification'):
    # Cargar las predicciones del estudiante
    try:
        predictions = pd.read_csv(predictions_file)
    except Exception as e:
        return 0, f"Error al leer el archivo: {str(e)}"
    
    # Cargar las etiquetas verdaderas
    try:
        true_labels = pd.read_csv('true_labels.csv')
    except Exception as e:
        return 0, f"Error al leer las etiquetas verdaderas: {str(e)}"
    
    # Verificar que los archivos tengan la misma estructura
    if 'id' not in predictions.columns or 'target' not in predictions.columns:
        return 0, "El archivo debe tener columnas 'id' y 'target'"
    
    if 'id' not in true_labels.columns or 'target' not in true_labels.columns:
        return 0, "Error en el archivo de etiquetas verdaderas"
    
    # Fusionar por ID para asegurarse de que están en el mismo orden
    merged = predictions.merge(
        right=true_labels,
        how='right',
        on='id',
        suffixes=('_pred', '_true')
    ).fillna(-1)
    
    if len(merged) == 0:
        return 0, "No se encontraron coincidencias entre IDs"
    
    # Calcular el score según el tipo de tarea
    try:
        if task_type == 'classification':
            score = f1_score(merged['target_true'], merged['target_pred'], average='weighted')
        else:  # regresión
            # Evitar división por cero en MAPE
            non_zero_mask = merged['target_true'] != 0
            if non_zero_mask.sum() == 0:
                return 0, "No se puede calcular MAPE porque todos los valores verdaderos son cero"
            score = mean_absolute_percentage_error(
                merged.loc[non_zero_mask, 'target_true'], 
                merged.loc[non_zero_mask, 'target_pred']
            )
            # Para MAPE, menor es mejor, así que convertimos para que mayor sea mejor
            score = 1 / (1 + score)
        
        return score, None
    except Exception as e:
        return 0, f"Error al calcular el score: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Verificar si se proporcionó un nombre
        student_name = request.form.get('student_name')
        if not student_name:
            flash('Por favor, ingresa tu nombre.')
            return redirect(url_for('index'))
        
        # Verificar si se subió un archivo
        if 'file' not in request.files:
            flash('No se ha subido ningún archivo.')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No se ha seleccionado ningún archivo.')
            return redirect(url_for('index'))
        
        # Guardar el archivo
        if file:
            filename = secure_filename(f"{student_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Evaluar predicciones
            # Puedes cambiar 'classification' por 'regression' según tu tarea
            score, error = evaluate_predictions(filepath, task_type='classification')
            
            if error:
                flash(f'Error: {error}')
                return redirect(url_for('index'))
            
            # Guardar en la base de datos
            submission = Submission(
                student_name=student_name,
                filename=filename,
                score=score
            )
            db.session.add(submission)
            db.session.commit()
            
            flash(f'¡Predicciones evaluadas con éxito! Tu score es: {score:.4f}')
            return redirect(url_for('index'))
    
    # Obtener el ranking
    submissions = Submission.query.order_by(Submission.score.desc()).all()
    
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