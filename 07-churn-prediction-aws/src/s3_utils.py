"""
Utilidades para interactuar con S3: subir/bajar datasets y modelos.
Requiere credenciales AWS configuradas como variables de entorno:
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
(o un perfil configurado con `aws configure`).
"""

import os
import io
import boto3
import pandas as pd

BUCKET_NAME = os.environ.get("CHURN_BUCKET", "my-churn-project-bucket")


def get_s3_client():
    """Crea un cliente de S3 usando las credenciales del entorno."""
    return boto3.client("s3")


def upload_file(local_path: str, s3_key: str, bucket: str = BUCKET_NAME) -> None:
    """Sube un archivo local a S3.

    Args:
        local_path: ruta local del archivo (ej. 'data/telco_churn.csv')
        s3_key: ruta destino dentro del bucket (ej. 'raw/telco_churn.csv')
        bucket: nombre del bucket S3
    """
    s3 = get_s3_client()
    s3.upload_file(local_path, bucket, s3_key)
    print(f"Subido: {local_path} -> s3://{bucket}/{s3_key}")


def download_file(s3_key: str, local_path: str, bucket: str = BUCKET_NAME) -> None:
    """Descarga un archivo de S3 a una ruta local."""
    s3 = get_s3_client()
    s3.download_file(bucket, s3_key, local_path)
    print(f"Descargado: s3://{bucket}/{s3_key} -> {local_path}")


def read_csv_from_s3(s3_key: str, bucket: str = BUCKET_NAME) -> pd.DataFrame:
    """Lee un CSV directamente desde S3 a un DataFrame, sin guardar en disco."""
    s3 = get_s3_client()
    obj = s3.get_object(Bucket=bucket, Key=s3_key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def upload_dataframe_as_csv(df: pd.DataFrame, s3_key: str, bucket: str = BUCKET_NAME) -> None:
    """Sube un DataFrame como CSV directamente a S3, sin guardar en disco."""
    s3 = get_s3_client()
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    s3.put_object(Bucket=bucket, Key=s3_key, Body=buffer.getvalue())
    print(f"DataFrame subido a s3://{bucket}/{s3_key}")


def upload_model(local_model_path: str, s3_key: str, bucket: str = BUCKET_NAME) -> None:
    """Sube un modelo entrenado (.pkl, .joblib) a S3."""
    upload_file(local_model_path, s3_key, bucket)


if __name__ == "__main__":
    # Ejemplo de uso rápido
    # upload_file("data/telco_churn.csv", "raw/telco_churn.csv")
    # df = read_csv_from_s3("raw/telco_churn.csv")
    # print(df.head())
    pass
