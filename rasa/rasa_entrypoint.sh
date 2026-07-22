#!/bin/sh
set -e

echo "=== Rasa Startup Model Validator ==="

MANIFEST_PATH="/app/models/current-model.json"

if [ ! -f "$MANIFEST_PATH" ]; then
  echo "[ERROR] Model manifest not found at $MANIFEST_PATH. Please run training first."
  exit 1
fi

# Run a python inline script to check manifest, calculate hash, and verify matching.
# If verification passes, it prints the filename to stdout.
MODEL_FILE=$(python -c '
import json
import os
import hashlib

manifest_path = "'"$MANIFEST_PATH"'"
if not os.path.exists(manifest_path):
    print("ERROR: Manifest file not found")
    exit(1)

with open(manifest_path, "r") as f:
    try:
        data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse manifest JSON: {e}")
        exit(1)

filename = data.get("filename")
expected_hash = data.get("sha256")

if not filename or not expected_hash:
    print("ERROR: Manifest must contain filename and sha256")
    exit(1)

model_path = os.path.join("/app/models", filename)
if not os.path.exists(model_path):
    print(f"ERROR: Model file {filename} does not exist at {model_path}")
    exit(1)

# Calculate SHA-256
sha256_hash = hashlib.sha256()
with open(model_path, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
calculated_hash = sha256_hash.hexdigest()

if calculated_hash != expected_hash:
    print(f"ERROR: Model hash mismatch. Expected: {expected_hash}, Calculated: {calculated_hash}")
    exit(1)

print(f"OK:{filename}")
')

# Check if the output of python script starts with OK:
case "$MODEL_FILE" in
  OK:*)
    FILENAME="${MODEL_FILE#OK:}"
    echo "[OK] Model $FILENAME verified successfully."
    echo "[INFO] Starting Rasa NLU server with model: $FILENAME"
    exec rasa run --enable-api --cors "*" --endpoints /app/endpoints.yml --credentials /app/credentials.yml --model "/app/models/$FILENAME"
    ;;
  *)
    echo "[ERROR] Model validation failed:"
    echo "$MODEL_FILE"
    exit 1
    ;;
esac
