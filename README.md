# Churn Prediction with AWS Pipeline

## Problema
Predecir el abandono de clientes (churn) usando el dataset Telco Customer Churn (Kaggle, `blastchar/telco-customer-churn`), con un pipeline de entrenamiento y despliegue en AWS.

## Arquitectura
```
Kaggle (kagglehub) → S3 (raw/)
                         │
                         ▼
              Feature Engineering (limpieza, encoding)
                         │
                         ▼
                  S3 (processed/)
                         │
                         ▼
        Entrenamiento (Logistic Regression, Random Forest, XGBoost)
                         │
                         ▼
              S3 (models/ — Pipeline serializado)
                         │
                         ▼
        Despliegue: Lambda + Layer (o SageMaker Endpoint)
                         │
                         ▼
              Inferencia (predicción + probabilidad de churn)
```

## Estructura del proyecto
```
07-churn-prediction-aws/
├── README.md
├── requirements.txt
├── data/
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_feature_engineering.ipynb
│   └── 03_model_training.ipynb
├── src/
│   ├── download_data.py      # descarga desde Kaggle (kagglehub) y sube a S3
│   ├── s3_utils.py           # utilidades boto3: subir/bajar, leer/escribir CSV y modelos
│   ├── train.py              # entrena y compara modelos, sube el mejor a S3
│   ├── deploy_lambda.py      # handler de la función Lambda de inferencia
│   ├── package_lambda.sh     # empaqueta código + dependencias (function.zip / layer.zip)
│   └── deploy.sh             # crea/actualiza la Layer y la función Lambda vía AWS CLI
└── infra/
    ├── iam_trust_policy.json # permite que Lambda asuma el rol de ejecución
    └── iam_policy.json       # permisos mínimos: s3:GetObject sobre models/ + CloudWatch Logs
```

## Resultados de los modelos

| Modelo | AUC | F1-score | Precision | Recall |
|---|---|---|---|---|
| **Logistic Regression** (Mejor) | **0.8403** | **0.5882** | 0.6347 | **0.5481** |
| **Random Forest** | 0.8231 | 0.5601 | **0.6502** | 0.4920 |
| **XGBoost** | 0.8187 | 0.5603 | 0.6056 | 0.5214 |

*El modelo de **Regresión Logística** obtuvo el mayor AUC (0.8403) y fue guardado automáticamente en S3 en `models/churn_best_model.joblib`.*

## Costos estimados (arquitectura Lambda + Layer)
Estimación aproximada para uso ligero/demo, región us-east-1:

| Componente | Costo aproximado |
|---|---|
| Lambda (512 MB, ~1-2s por invocación) | Gratis hasta 1M invocaciones/mes (free tier); luego ~$0.20 por millón de invocaciones + cómputo |
| S3 (almacenamiento de datos + modelo, <1 GB) | < $0.05/mes |
| S3 (requests GET/PUT durante desarrollo) | Centavos por mes con uso moderado |
| CloudWatch Logs | Gratis hasta 5 GB/mes |

Para uso productivo con tráfico sostenido, un **SageMaker Endpoint** (instancia dedicada, ej. `ml.t2.medium`) cuesta desde ~$0.05/hora (~$36/mes corriendo 24/7) — más caro que Lambda en reposo, pero sin cold starts y con más control de escalado. Lambda es la opción recomendada para este proyecto por ser un caso de baja frecuencia de invocación.

*Nota: estimación orientativa, no una cotización — verificar precios actuales en la [calculadora de AWS](https://calculator.aws).*

## Cómo reproducirlo

### 1. Configurar credenciales
```bash
# AWS (para S3 y despliegue)
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# Kaggle (para kagglehub)
export KAGGLE_USERNAME=...
export KAGGLE_KEY=...

# Bucket de trabajo
export CHURN_BUCKET=tu-bucket-de-churn
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Descargar el dataset y subirlo a S3
```bash
python src/download_data.py
```

### 4. Ejecutar el pipeline (notebooks, en orden)
1. `notebooks/01_eda.ipynb` — exploración inicial
2. `notebooks/02_feature_engineering.ipynb` — limpieza, encoding, sube `processed/telco_churn_clean.csv`
3. `notebooks/03_model_training.ipynb` — entrena, compara y guarda el mejor modelo en S3

Alternativa no interactiva (mismo resultado, sin abrir notebooks):
```bash
python src/train.py
```

### 5. Desplegar el modelo como Lambda
```bash
# Una sola vez: crear el rol IAM con infra/iam_trust_policy.json + infra/iam_policy.json
# (reemplazar el bucket en iam_policy.json antes de crearlo)

cd src/
./package_lambda.sh
AWS_REGION=us-east-1 \
MODEL_BUCKET=tu-bucket-de-churn \
LAMBDA_ROLE_ARN=arn:aws:iam::<cuenta>:role/churn-lambda-role \
./deploy.sh
```

### 6. Probar la inferencia
```bash
aws lambda invoke --function-name churn-prediction --region us-east-1 \
  --payload '{"body": "{\"tenure\": 12, \"MonthlyCharges\": 70.5, \"Contract\": \"Month-to-month\"}"}' \
  --cli-binary-format raw-in-base64-out response.json && cat response.json
```

## Estado
🚧 Código base y pipeline completos (descarga, EDA, feature engineering, entrenamiento, despliegue).
