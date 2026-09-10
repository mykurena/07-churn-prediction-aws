#!/bin/bash
# Crea o actualiza la Lambda Layer y la funcion Lambda usando AWS CLI.
# Requiere: AWS CLI configurado (aws configure) y haber corrido package_lambda.sh antes.
#
# Variables de entorno esperadas (ajustar segun tu cuenta/region):
#   AWS_REGION            - ej. us-east-1
#   MODEL_BUCKET           - bucket S3 donde vive el modelo entrenado
#   MODEL_KEY              - ej. models/churn_best_model.joblib
#   LAMBDA_ROLE_ARN         - ARN del rol IAM que va a ejecutar la funcion
#                             (ver iam_policy.json + iam_trust_policy.json en esta carpeta)
#
# Uso:
#   chmod +x deploy.sh
#   AWS_REGION=us-east-1 MODEL_BUCKET=mi-bucket LAMBDA_ROLE_ARN=arn:aws:iam::123456789012:role/churn-lambda-role ./deploy.sh

set -e

FUNCTION_NAME="churn-prediction"
LAYER_NAME="churn-prediction-deps"
RUNTIME="python3.11"
HANDLER="deploy_lambda.handler"
BUILD_DIR="build"

: "${AWS_REGION:?Falta AWS_REGION}"
: "${MODEL_BUCKET:?Falta MODEL_BUCKET}"
: "${LAMBDA_ROLE_ARN:?Falta LAMBDA_ROLE_ARN}"
MODEL_KEY="${MODEL_KEY:-models/churn_best_model.joblib}"

echo "1. Publicando Lambda Layer..."
LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --zip-file "fileb://$BUILD_DIR/layer.zip" \
    --compatible-runtimes "$RUNTIME" \
    --region "$AWS_REGION" \
    --query "LayerVersionArn" \
    --output text)

echo "   Layer publicada: $LAYER_VERSION_ARN"

echo "2. Verificando si la funcion ya existe..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "   Funcion existente: actualizando codigo..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$BUILD_DIR/function.zip" \
        --region "$AWS_REGION" > /dev/null

    echo "   Esperando a que termine la actualizacion..."
    aws lambda wait function-updated \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION"

    echo "   Actualizando configuracion (layer, env vars, memoria)..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --layers "$LAYER_VERSION_ARN" \
        --environment "Variables={MODEL_BUCKET=$MODEL_BUCKET,MODEL_KEY=$MODEL_KEY}" \
        --memory-size 512 \
        --timeout 30 \
        --region "$AWS_REGION" > /dev/null
else
    echo "   Funcion nueva: creando..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$LAMBDA_ROLE_ARN" \
        --handler "$HANDLER" \
        --zip-file "fileb://$BUILD_DIR/function.zip" \
        --layers "$LAYER_VERSION_ARN" \
        --environment "Variables={MODEL_BUCKET=$MODEL_BUCKET,MODEL_KEY=$MODEL_KEY}" \
        --memory-size 512 \
        --timeout 30 \
        --region "$AWS_REGION" > /dev/null
fi

echo ""
echo "Listo. Funcion '$FUNCTION_NAME' desplegada en $AWS_REGION."
echo ""
echo "Prueba rapida:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --region $AWS_REGION \\"
echo "    --payload '{\"body\": \"{\\\"tenure\\\": 12, \\\"MonthlyCharges\\\": 70.5, \\\"Contract\\\": \\\"Month-to-month\\\"}\"}' \\"
echo "    --cli-binary-format raw-in-base64-out response.json && cat response.json"
