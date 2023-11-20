"""
CORE, TODO: Schema management and migration with function proxies over the spaces - key to good RAGs. A DocumentGraph Model is key here
"""

from loguru import logger
import os
from pathlib import Path
import uuid
import sys
import hashlib
from ._version import __version__
from getpass import getuser
from datetime import datetime
from .ops.observability import get_tracer
from opentelemetry import trace

"""
primary config
"""

USER_HOME = Path.home()
DEFAULT_HOME = f"{USER_HOME}/.funkyprompt"
STORE_ROOT = os.environ.get("FP_STORE_HOME", DEFAULT_HOME).rstrip("/")
VECTOR_STORE_ROOT_URI = f"{STORE_ROOT}/vector-store"
COLUMNAR_STORE_ROOT_URI = f"{STORE_ROOT}/columnar-store"

logger.remove()
logger.add(sys.stderr, level=os.environ.get("FP_LOG_LEVEL", "DEBUG"))

"""
some basic global utils and init
"""

if not Path(DEFAULT_HOME).exists():
    Path(DEFAULT_HOME).mkdir(exist_ok=True, parents=True)


def str_hash(s=None, m=5, prefix="fpr"):
    s = (s or str(uuid.uuid1())).encode()
    h = hashlib.shake_256(s).hexdigest(m).upper()
    return f"{prefix}{h}"


utc_now_str = lambda: datetime.utcnow().isoformat()


"""
set up some otel bits
"""

tracer = get_tracer()


def add_span_attribute(key, value):
    current_span = trace.get_current_span()
    current_span.set_attribute(key, value)


"""
setup some funkyprompt bits
"""

from . import io, ops
from funkyprompt.io.stores import FunkyRegistry
from funkyprompt.model.func import describe_function
from funkyprompt.ops import examples
from .agent.AgentBase import AgentBase

agent = AgentBase(modules=examples)
