"""
Descarga el dataset Telco Customer Churn desde Kaggle usando kagglehub
y lo sube a S3 como paso inicial del pipeline.

Requiere:
  pip install kagglehub
  Credenciales de Kaggle configuradas (~/.kaggle/kaggle.json o variables
  de entorno KAGGLE_USERNAME / KAGGLE_KEY)
"""

import os
import glob
import kagglehub

from s3_utils import upload_file, BUCKET_NAME

RAW_S3_KEY = "raw/telco_churn.csv"


def download_dataset() -> str:
    """Descarga la última versión del dataset y devuelve la ruta local del CSV."""
    path = kagglehub.dataset_download("blastchar/telco-customer-churn")
    print("Path to dataset files:", path)

    # El dataset de Kaggle trae un único CSV; lo localizamos dentro de la carpeta descargada
    csv_files = glob.glob(os.path.join(path, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontró ningún CSV en {path}")

    csv_path = csv_files[0]
    print("CSV encontrado:", csv_path)
    return csv_path


def download_and_upload_to_s3(bucket: str = BUCKET_NAME, s3_key: str = RAW_S3_KEY) -> None:
    """Descarga el dataset desde Kaggle y lo sube directamente a S3."""
    csv_path = download_dataset()
    upload_file(csv_path, s3_key, bucket)


if __name__ == "__main__":
    download_and_upload_to_s3()
