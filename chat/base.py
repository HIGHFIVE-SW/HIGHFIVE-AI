import typing
from typing import Optional

from langgraph.graph.state import CompiledStateGraph

if typing.TYPE_CHECKING:
    from .bot import Bot


class BaseBot:
    pass
