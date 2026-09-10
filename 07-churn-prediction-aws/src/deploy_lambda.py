"""
Funcion Lambda para servir predicciones de churn.
Carga el modelo desde S3 (una sola vez, fuera del handler, para reuso entre invocaciones)
y responde a eventos con los datos de un cliente.

Despliegue sugerido:
  - Runtime: Python 3.11
  - Memoria: 512 MB (ajustar segun tamaño del modelo)
  - Variables de entorno: MODEL_BUCKET, MODEL_KEY
  - Permisos IAM: s3:GetObject sobre el bucket del modelo
  - Empaquetar con las dependencias (pandas, scikit-learn, xgboost, joblib)
    en una Lambda Layer para no exceder el limite de tamaño del paquete.
"""

import os
import io
import json
import boto3
import joblib
import pandas as pd

MODEL_BUCKET = os.environ.get("MODEL_BUCKET", "my-churn-project-bucket")
MODEL_KEY = os.environ.get("MODEL_KEY", "models/churn_best_model.joblib")

_model = None  # cache entre invocaciones (contenedor "caliente")


def _load_model():
    global _model
    if _model is None:
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=MODEL_BUCKET, Key=MODEL_KEY)
        _model = joblib.load(io.BytesIO(obj["Body"].read()))
        print(f"Modelo cargado desde s3://{MODEL_BUCKET}/{MODEL_KEY}")
    return _model


def handler(event, context):
    """
    Espera un event con el body en formato JSON, ej:
    {
      "body": "{\"tenure\": 12, \"MonthlyCharges\": 70.5, \"Contract\": \"Month-to-month\", ...}"
    }
    """
    try:
        model = _load_model()

        body = event.get("body", event)
        if isinstance(body, str):
            body = json.loads(body)

        df = pd.DataFrame([body])
        prediction = model.predict(df)[0]
        probability = model.predict_proba(df)[0][1]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "churn_prediction": int(prediction),
                "churn_probability": round(float(probability), 4),
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


if __name__ == "__main__":
    # Prueba local simulando un evento
    test_event = {
        "body": json.dumps({
            "tenure": 12,
            "MonthlyCharges": 70.5,
            "Contract": "Month-to-month",
        })
    }
    print(handler(test_event, None))
