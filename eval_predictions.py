import csv
import pandas as pd
from sklearn.metrics import f1_score, mean_absolute_percentage_error

class PredictionEvaluator:
    """
    Clase para evaluar las predicciones de un estudiante comparándolas con las etiquetas verdaderas.
    
    Atributos:
    - true_labels_path: Ruta del archivo CSV con las etiquetas verdaderas.
    - true_labels: DataFrame con las etiquetas verdaderas, cargado desde true_labels_path.
    """
    def __init__(self, true_labels_path: str):
        self.true_labels_path = true_labels_path
        try:
            self.true_labels = pd.read_csv(self.true_labels_path)
        except Exception as e:
            self.true_labels = None
            print(f"Error al cargar las etiquetas verdaderas: {str(e)}")

    def validate_columns(self, df, required_columns):
        """
        Verifica que el DataFrame 'df' contenga las columnas requeridas.
        
        Parámetros:
        - df: DataFrame a validar.
        - required_columns: Lista de nombres de columnas necesarias.
        
        Retorna:
        - (bool, mensaje): True y None si se cumplen, o False y un mensaje de error.
        """
        for col in required_columns:
            if col not in df.columns:
                return False, f"Falta la columna '{col}'"
        return True, None

    def validate_ids(self, predictions_df):
        """
        Valida que el archivo de predicciones contenga exactamente los mismos IDs que las etiquetas verdaderas.
        
        Parámetros:
        - predictions_df: DataFrame con las predicciones.
        
        Retorna:
        - (bool, mensaje): True y None si los IDs coinciden, o False y un mensaje indicando los IDs faltantes o adicionales.
        """
        true_ids = set(self.true_labels['id'])
        pred_ids = set(predictions_df['id'])
        if true_ids != pred_ids:
            missing_ids = true_ids - pred_ids
            extra_ids = pred_ids - true_ids
            msg = "El archivo de predicciones no contiene los mismos IDs que las etiquetas verdaderas."
            if missing_ids:
                msg += f" Faltan IDs: {missing_ids}."
            if extra_ids:
                msg += f" IDs adicionales: {extra_ids}."
            return False, msg
        return True, None

    def evaluate_predictions(self, predictions, task_type='classification'):
        """
        Evalúa las predicciones comparándolas con las etiquetas verdaderas.
        
        Pasos:
        1. Validar que el archivo contenga las columnas 'id' y 'target'.
        2. Validar que el archivo de etiquetas verdaderas también tenga las columnas 'id' y 'target'.
        3. Validar que los IDs en el archivo de predicciones sean exactamente los mismos que en el de etiquetas.
        4. Fusionar ambos DataFrames por la columna 'id' para alinear las predicciones con las etiquetas verdaderas.
        5. Calcular el score según el tipo de tarea:
           - Para clasificación, se usa F1-score ponderado.
           - Para regresión, se calcula MAPE (conversión para que mayor sea mejor).
        
        Parámetros:
        - predictions: archivo CSV con las predicciones del estudiante.
        - task_type: Tipo de tarea ('classification' o 'regression'). Por defecto es 'classification'.
        
        Retorna:
        - (score, mensaje_error): El score calculado y None si todo fue correcto, o 0 y un mensaje de error en caso de fallo.
        """

        # 1. Verificar que las predicciones tengan las columnas necesarias
        valid, msg = self.validate_columns(predictions, ['id', 'target'])
        if not valid:
            return 0, f"El archivo de predicciones debe tener columnas 'id' y 'target'. {msg}"
        predictions.drop_duplicates(subset="id", inplace=True)
        

        # 2. Verificar que las etiquetas verdaderas tengan las columnas necesarias
        valid, msg = self.validate_columns(self.true_labels, ['id', 'target'])
        if not valid:
            return 0, f"El archivo de etiquetas verdaderas debe tener columnas 'id' y 'target'. {msg}"
        
        # 3. Validar que los IDs en el archivo de predicciones sean exactamente los mismos que en el de etiquetas
        valid, msg = self.validate_ids(predictions)
        if not valid:
            return 0, msg
        
        # 4. Fusionar los DataFrames por la columna 'id'
        merged = predictions.merge(
            right=self.true_labels,
            how='right',
            on='id',
            suffixes=('_pred', '_true')
        ).fillna(-1)
        
        if len(merged) == 0:
            return 0, "No se encontraron coincidencias entre los IDs."
        
        # 5. Calcular el score basado en el tipo de tarea
        try:
            if task_type == 'classification':
                score = f1_score(merged['target_true'], merged['target_pred'], average='weighted')
            else:  # Para regresión
                # Evitar división por cero en MAPE
                non_zero_mask = merged['target_true'] != 0
                if non_zero_mask.sum() == 0:
                    return 0, "No se puede calcular MAPE porque todos los valores verdaderos son cero."
                score = mean_absolute_percentage_error(
                    merged.loc[non_zero_mask, 'target_true'], 
                    merged.loc[non_zero_mask, 'target_pred']
                )
                # Convertir MAPE a un score donde mayor es mejor: score = 1 / (1 + MAPE)
                score = 1 / (1 + score)
            return score, None
        except Exception as e:
            return 0, f"Error al calcular el score: {str(e)}"


def load_students(csv_path: str):
    alumnos = {}
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Supongamos que en el CSV tienes columnas 'registration_number' y 'name'
            alumnos[int(row['registration_number'])] = row['name']
    return alumnos
