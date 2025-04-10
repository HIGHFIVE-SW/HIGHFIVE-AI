import sqlite3
from os.path import join, dirname, abspath

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from chat.base import BaseBot
from chat.graph import LangGraphMethods


class Bot(BaseBot, LangGraphMethods):
    SQLITE_CONNECTION_STRING: str = join(dirname(abspath(__file__)),
                                         f"chats.db")  # base.py와 같은 경로에 SQLITE memory file 생성
    def __init__(self, user_id):
        # 메모리 저장소 생성 (그래프에 사용되기 때문에, 반드시 그래프 생성 이전에 선행되어야 함)
        self.memory = SqliteSaver(sqlite3.connect(self.SQLITE_CONNECTION_STRING, check_same_thread=False))
        self.graph: CompiledStateGraph = self.build_graph()
        self.id = user_id # TODO: 사용자별로 고유한 bot_id 필요

