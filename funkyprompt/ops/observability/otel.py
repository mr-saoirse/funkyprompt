# https://opentelemetry.io/docs/instrumentation/python/manual/
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

SERVICE_NAME_OTEL = "funkyprompt"
TRACER_NAME_OTEL = "core.funkyprompt"


def get_tracer(name=TRACER_NAME_OTEL):
    """
    get the system wide otel tracer

    """
    resource = Resource(attributes={SERVICE_NAME: SERVICE_NAME_OTEL})
    # TODO load providers from environment
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(name)

    return tracer
