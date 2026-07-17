import os
from unittest.mock import patch
from fastapi import FastAPI
from backend.core.tracing import setup_tracing
from opentelemetry import trace
from opentelemetry.trace import Span

def test_setup_tracing_enabled():
    app = FastAPI()
    with patch.dict(os.environ, {"ENABLE_TRACING": "true", "OTEL_TRACES_EXPORTER": "none"}):
        setup_tracing(app)
        # Check that tracer provider is set
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_span") as span:
            assert isinstance(span, Span)
            assert span.is_recording()

def test_setup_tracing_disabled():
    app = FastAPI()
    with patch.dict(os.environ, {"ENABLE_TRACING": "false"}):
        # Should not raise any exceptions
        setup_tracing(app)
