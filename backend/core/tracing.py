import os
import logging
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)

# Global flag to track if we've already instrumented
_INSTRUMENTED = False

def redact_sensitive_data(span, **kwargs):
    """Remove sensitive data like passwords, JWTs, API keys from spans."""
    if not hasattr(span, 'attributes'):
        return
        
    sensitive_keys = ['password', 'token', 'authorization', 'api_key', 'secret', 'cookie']
    # Attributes is an immutable dictionary-like proxy in OTel, we can only add new ones, but
    # the request_hook allows us to mutate span attributes natively
    if span.attributes:
        for key in list(span.attributes.keys()):
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                span.set_attribute(key, "***REDACTED***")


def setup_tracing(app: FastAPI, service_name: str = None):
    global _INSTRUMENTED
    try:
        # Check if tracing is enabled
        if os.getenv("ENABLE_TRACING", "false").lower() != "true":
            logger.info("OpenTelemetry tracing is disabled (ENABLE_TRACING != true).")
            return

        if _INSTRUMENTED:
            logger.info("OpenTelemetry already instrumented, skipping duplicate setup.")
            return

        service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "cybersec-assistant-backend")
        
        resource = Resource.create(attributes={
            ResourceAttributes.SERVICE_NAME: service_name
        })
        
        # Don't register global provider if one already exists
        if isinstance(trace.get_tracer_provider(), TracerProvider):
            provider = trace.get_tracer_provider()
        else:
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
        
        # Determine exporters based on environment
        exporter_types = os.getenv("OTEL_TRACES_EXPORTER", "console").split(",")
        
        for exp_type in exporter_types:
            exp_type = exp_type.strip().lower()
            if exp_type == "otlp":
                endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
                logger.info(f"Configuring OTLP span exporter to {endpoint}")
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            elif exp_type == "console":
                logger.info("Configuring console span exporter")
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Instrument FastAPI
        # Exclude endpoints that we don't want to trace (e.g., healthchecks)
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls="health,healthcheck,/api/v1/health",
                tracer_provider=provider,
                server_request_hook=lambda span, scope: redact_sensitive_data(span)
            )
        except Exception as e:
            logger.debug(f"FastAPI instrumentation notice: {e}")

        # Instrument HTTPX for outgoing requests (e.g., to LLM, Supabase, Rasa)
        try:
            HTTPXClientInstrumentor().instrument(
                tracer_provider=provider,
                request_hook=lambda span, request: redact_sensitive_data(span)
            )
        except Exception as e:
            # Avoid crashing if HTTPX is already instrumented
            logger.debug(f"HTTPX instrumentation notice: {e}")
            
        _INSTRUMENTED = True
        logger.info("✅ OpenTelemetry tracing configured successfully.")
    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry tracing: {e}")
