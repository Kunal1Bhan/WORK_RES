"""Structured JSON logging + OpenTelemetry tracing (both degrade gracefully)."""
import json
import logging
import os
import sys
import time


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    return logging.getLogger("lab")


def setup_tracing(service_name="reliability-lab-api"):
    """OTLP exporter if OTEL_EXPORTER_OTLP_ENDPOINT set, else console.
    Opt-in: enabled only when OTEL_ENABLED=1 (avoids noisy no-op exporters
    in tests). Returns (mode, tracer) or None. Never raises."""
    if os.getenv("OTEL_ENABLED") != "1":
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return None
    try:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=endpoint + "/v1/traces")
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        provider = TracerProvider(resource=Resource({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            if FastAPIInstrumentor is None:  # pragma: no cover
                return ("manual", trace.get_tracer(service_name))
            return ("fastapi", trace.get_tracer(service_name))
        except ImportError:
            return ("manual", trace.get_tracer(service_name))
    except Exception:
        return None
