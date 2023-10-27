from loguru import logger
import os
from pathlib import Path
import uuid
import hashlib
from ._version import __version__

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


from . import io, ops
from .agent.AgentBase import AgentBase
from funkyprompt.ops import examples
from funkyprompt.ops.utils.inspector import describe_function

agent = AgentBase(modules=examples)
