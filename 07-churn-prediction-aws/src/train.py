"""
Entrenamiento y comparación de modelos de churn.
Lee los datos desde S3, entrena Logistic Regression, Random Forest y XGBoost,
compara métricas y guarda el mejor modelo de vuelta en S3.
"""

import io
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from xgboost import XGBClassifier

from s3_utils import read_csv_from_s3, get_s3_client, BUCKET_NAME

RAW_DATA_KEY = "raw/telco_churn.csv"
MODEL_KEY = "models/churn_best_model.joblib"
TARGET_COL = "Churn"  # ajustar según el nombre real de la columna en el dataset


def load_data() -> pd.DataFrame:
    """Carga el dataset crudo desde S3."""
    return read_csv_from_s3(RAW_DATA_KEY)


def build_preprocessor(df: pd.DataFrame, target_col: str) -> ColumnTransformer:
    """Construye el preprocesador según tipos de columna (numéricas/categóricas)."""
    features = df.drop(columns=[target_col])
    numeric_cols = features.select_dtypes(include=["int64", "float64"]).columns.tolist()
    categorical_cols = features.select_dtypes(include=["object"]).columns.tolist()

    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ]
    )


def evaluate(model, X_test, y_test) -> dict:
    """Calcula métricas de evaluación estándar."""
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    return {
        "auc": roc_auc_score(y_test, probs),
        "f1": f1_score(y_test, preds),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
    }


def train_and_compare(df: pd.DataFrame, target_col: str = TARGET_COL):
    """Entrena varios modelos, compara métricas y devuelve el mejor pipeline."""
    # Convertir Churn de 'Yes'/'No' a 1/0 si viene como string
    if df[target_col].dtype == object or isinstance(df[target_col].iloc[0], str):
        y = df[target_col].map({"Yes": 1, "No": 0})
    else:
        y = df[target_col]

    X = df.drop(columns=[target_col])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = build_preprocessor(df, target_col)

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1000),
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=42),
        "xgboost": XGBClassifier(eval_metric="logloss", random_state=42),
    }

    results = {}
    best_name, best_pipeline, best_auc = None, None, -1

    for name, clf in candidates.items():
        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])
        pipeline.fit(X_train, y_train)
        metrics = evaluate(pipeline, X_test, y_test)
        results[name] = metrics
        print(f"{name}: {metrics}")

        if metrics["auc"] > best_auc:
            best_name, best_pipeline, best_auc = name, pipeline, metrics["auc"]

    print(f"\nMejor modelo: {best_name} (AUC={best_auc:.4f})")
    return best_name, best_pipeline, results


def save_model_to_s3(pipeline, s3_key: str = MODEL_KEY, bucket: str = BUCKET_NAME) -> None:
    """Serializa el pipeline entrenado y lo sube a S3 sin pasar por disco."""
    buffer = io.BytesIO()
    joblib.dump(pipeline, buffer)
    buffer.seek(0)
    s3 = get_s3_client()
    s3.put_object(Bucket=bucket, Key=s3_key, Body=buffer.getvalue())
    print(f"Modelo guardado en s3://{bucket}/{s3_key}")


if __name__ == "__main__":
    df = load_data()
    best_name, best_pipeline, results = train_and_compare(df)
    save_model_to_s3(best_pipeline)
