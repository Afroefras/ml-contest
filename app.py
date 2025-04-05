from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sklearn.metrics import f1_score, mean_absolute_percentage_error

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo para almacenar las sumisiones
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Float, nullable=False)

# Función para evaluar las predicciones
def evaluate_predictions(y_true, y_pred, task_type="classification"):
    # Puedes ajustar esta función según la métrica que necesites.
    if task_type == "classification":
        return f1_score(y_true, y_pred, average="macro")
    elif task_type == "regression":
        return mean_absolute_percentage_error(y_true, y_pred)
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

@app.route('/', methods=['GET', 'POST'])
def index():
    # Obtenemos el ranking ordenado por score (por ejemplo, mayor F1-score primero)
    ranking = Submission.query.order_by(Submission.score.desc()).all()
    if request.method == 'POST':
        student_name = request.form.get('student_name')
        file = request.files.get('file')
        if not student_name or not file:
            flash("Debes ingresar tu nombre y seleccionar un archivo", "danger")
            return redirect(url_for('index'))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Generar un nombre único para evitar conflictos
            timestamp_str = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            unique_filename = f"{student_name}_{timestamp_str}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            try:
                # Leer las predicciones del archivo subido (asegúrate de que contenga una columna 'prediction')
                predictions_df = pd.read_csv(file_path)
                y_pred = predictions_df['prediction']
                
                # Cargar las etiquetas verdaderas (asegúrate de tener un CSV con la columna 'label')
                true_df = pd.read_csv('true_labels.csv')
                y_true = true_df['label']
                
                # Calcula el score. Cambia "classification" por "regression" si fuera el caso.
                score = evaluate_predictions(y_true, y_pred, task_type="classification")
                
                # Guardar la sumisión en la base de datos
                submission = Submission(student_name=student_name, filename=unique_filename, score=score)
                db.session.add(submission)
                db.session.commit()
                
                flash(f"Archivo subido correctamente. Tu score es: {score:.4f}", "success")
            except Exception as e:
                flash(f"Error al procesar el archivo: {str(e)}", "danger")
        else:
            flash("Archivo no permitido. Solo se aceptan archivos CSV.", "danger")
        return redirect(url_for('index'))
    return render_template('index.html', ranking=ranking)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
