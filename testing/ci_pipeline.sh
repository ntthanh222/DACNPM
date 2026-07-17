#!/bin/bash
set -e

echo "Starting CI Pipeline..."

echo "1. Running Settings & Environment Security Tests..."
backend/venv/Scripts/python.exe -m pytest backend/tests/test_settings_security.py -v

echo "2. Running API Contract Validation..."
backend/venv/Scripts/python.exe -m pytest backend/tests/test_api_contracts.py -v

echo "3. Running OpenTelemetry & Tracing Tests..."
backend/venv/Scripts/python.exe -m pytest backend/tests/test_tracing.py -v

echo "4. Running AI/RAG Prompt Injection Evaluation..."
backend/venv/Scripts/python.exe -m pytest backend/tests/test_prompt_injection.py -v

echo "CI Pipeline Completed Successfully!"
