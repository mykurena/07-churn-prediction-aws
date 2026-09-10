#!/bin/bash
# Empaqueta la funcion Lambda con sus dependencias en un .zip listo para subir a AWS.
#
# Lambda tiene un limite de tamano de paquete (50 MB comprimido via consola,
# 250 MB descomprimido via S3/CLI). pandas + scikit-learn + xgboost + joblib
# superan facilmente ese limite si se empaquetan junto con el codigo, por eso
# se recomienda separarlos en una Lambda Layer.
#
# Uso:
#   chmod +x package_lambda.sh
#   ./package_lambda.sh
#
# Salida:
#   build/function.zip   -> solo el codigo (deploy_lambda.py)
#   build/layer.zip      -> las dependencias, para subir como Lambda Layer

set -e

BUILD_DIR="build"
FUNCTION_ZIP="$BUILD_DIR/function.zip"
LAYER_ZIP="$BUILD_DIR/layer.zip"
LAYER_DIR="$BUILD_DIR/python"  # Lambda Layers para Python requieren esta carpeta exacta

echo "Limpiando build anterior..."
rm -rf "$BUILD_DIR"
mkdir -p "$LAYER_DIR"

echo "Empaquetando codigo de la funcion..."
mkdir -p "$BUILD_DIR/function"
cp deploy_lambda.py "$BUILD_DIR/function/"
cd "$BUILD_DIR/function"
zip -r "../../$FUNCTION_ZIP" .
cd - > /dev/null

echo "Instalando dependencias para la Layer (esto puede tardar unos minutos)..."
pip install \
    --platform manylinux2014_x86_64 \
    --target "$LAYER_DIR" \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    boto3 pandas scikit-learn joblib xgboost

echo "Comprimiendo Layer..."
cd "$BUILD_DIR"
zip -r "../$LAYER_ZIP" python
cd - > /dev/null

echo ""
echo "Listo:"
echo "  $FUNCTION_ZIP  (codigo de la funcion)"
echo "  $LAYER_ZIP     (dependencias, subir como Lambda Layer)"
echo ""
echo "Siguiente paso: correr deploy.sh (o los comandos AWS CLI equivalentes)"
echo "para crear/actualizar la Layer y la funcion Lambda."
