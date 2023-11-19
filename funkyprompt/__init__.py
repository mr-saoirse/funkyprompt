"""
CORE, TODO: Schema management and migration with function proxies over the spaces - key to good RAGs. A DocumentGraph Model is key here
"""

from loguru import logger
import os
from pathlib import Path
import uuid
import hashlib
from ._version import __version__
from getpass import getuser

USER_HOME = Path.home()
DEFAULT_HOME = f"{USER_HOME}/.funkyprompt"
STORE_ROOT = os.environ.get("FP_STORE_HOME", DEFAULT_HOME).rstrip("/")
VECTOR_STORE_ROOT_URI = f"{STORE_ROOT}/vector-store"
COLUMNAR_STORE_ROOT_URI = f"{STORE_ROOT}/columnar-store"


if not Path(DEFAULT_HOME).exists():
    Path(DEFAULT_HOME).mkdir(exist_ok=True, parents=True)


def str_hash(s=None, m=5, prefix="fpr"):
    s = (s or str(uuid.uuid1())).encode()
    h = hashlib.shake_256(s).hexdigest(m).upper()
    return f"{prefix}{h}"


from datetime import datetime

utc_now_str = lambda: datetime.utcnow().isoformat()

from .ops.observability import get_tracer

tracer = get_tracer()

from . import io, ops
from funkyprompt.io.stores import FunkyRegistry
from funkyprompt.model.func import describe_function
from funkyprompt.ops import examples
from .agent.AgentBase import AgentBase

agent = AgentBase(modules=examples)
