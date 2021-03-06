from time import sleep
from flask import Flask, request
from flask.logging import default_handler
from opentelemetry import trace
from opentelemetry.exporter import jaeger
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
import logging
import os
from time import strftime

AGENT_HOSTNAME = os.getenv("AGENT_HOSTNAME", "localhost")
AGENT_PORT = int(os.getenv("AGENT_PORT", "6831"))


class SpanFormatter(logging.Formatter):
    def format(self, record):
        trace_id = trace.get_current_span().get_span_context().trace_id
        if trace_id == 0:
            record.trace_id = None
        else:
            record.trace_id = "{trace:032x}".format(trace=trace_id)
        return super().format(record)


jaeger_exporter = jaeger.JaegerSpanExporter(
    service_name="service-bar",
    # configure agent
    agent_host_name=AGENT_HOSTNAME,
    agent_port=AGENT_PORT,
)

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchExportSpanProcessor(jaeger_exporter)
)

app = Flask(__name__)

FlaskInstrumentor().instrument_app(app)

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
app.logger.setLevel(logging.INFO)
default_handler.setFormatter(
    SpanFormatter(
        'time="%(asctime)s" service=%(name)s level=%(levelname)s %(message)s trace_id=%(trace_id)s'
    )
)


@app.route("/bar")
def bar():
    return "bar"


@app.after_request
def after_request(response):
    app.logger.info(
        'addr="%s" method=%s scheme=%s path="%s" status=%s',
        request.remote_addr,
        request.method,
        request.scheme,
        request.full_path,
        response.status_code,
    )
    return response
