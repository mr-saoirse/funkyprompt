# https://opentelemetry.io/docs/instrumentation/python/manual/
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
import funkyprompt
import os

SERVICE_NAME_OTEL = "funkyprompt"
TRACER_NAME_OTEL = "core.funkyprompt"


class my_writer:
    spans = []

    def write(x):
        my_writer.spans.append(x)

    def flush(*args, **kwargs):
        """
        wait to flush - this is just a debugging tool and down want to span spam
        """
        for s in my_writer.spans:
            try:
                funkyprompt.logger.debug(s)
            except:
                # this is only if the logger is closed when flush is called
                print(s)
        my_writer.spans = []


def get_tracer(name=TRACER_NAME_OTEL):
    """
    get the system wide otel tracer

    """
    resource = Resource(attributes={SERVICE_NAME: SERVICE_NAME_OTEL})
    # TODO load providers from environment
    provider = TracerProvider(resource=resource)
    # adding a really big delay because we can just pull the state at the end rather than see lots of logging
    processor = BatchSpanProcessor(
        ConsoleSpanExporter(out=my_writer),
        # set this to either be delayed or quicker - this is just a debugging tool
        schedule_delay_millis=os.environ.get(
            f"FP_OTEM_CONSOLE_FLUSH_DELAY_MILLIS", 100
        ),
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(name)

    return tracer
