from loguru import logger
import os
from pathlib import Path

USER_HOME = Path.home()
DEFAULT_HOME = f"{USER_HOME}/.funkyprompt"
STORE_ROOT = os.environ.get("FP_STORE_HOME", DEFAULT_HOME)
if not Path(DEFAULT_HOME).exists():
    Path(DEFAULT_HOME).mkdir(exist_ok=True, parents=True)


from .agent.AgentBase import AgentBase

from funkyprompt.ops import examples

agent = AgentBase(modules=examples)
