import sqlite3
import threading
from os.path import join, dirname, abspath
from typing import Union

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from .graph import LangGraphMethods
from .tools import Tools
from .vectorstore import VectorStoreMethods


class Bot(LangGraphMethods, VectorStoreMethods, Tools):
    _instances: dict[int, 'Bot'] = {}
    _lock: threading.Lock = threading.Lock()
    SQLITE_CONNECTION_STRING: str = join(dirname(abspath(__file__)),
                                         f"chats.db")  # base.py와 같은 경로에 SQLITE memory file 생성
    embeddings = OpenAIEmbeddings()
    vectorstore: FAISS

    def __new__(cls, *args, **kwargs):
        """
            싱글톤 객체의 변형 구현.
            입력받은 user id에 대응하는 챗봇이 없을 경우에 한해,
            고유한 Bot 객체를 새로 만들고 반환하는 동시에 _instances에 내부적으로 저장한다.

            만약 해당 user id에 대응하는 챗봇이 이미 생성되었을 경우,
            그 챗봇을 반환한다.
        """
        with cls._lock: # 챗봇이 호출될 때마다 Bot 클래스 속성인 vectorstore를 업데이트
            cls.vectorstore = getattr(cls, "vectorstore", None) or cls.initialize_vectorstore()
            cls.update_vectorstore()
            cls.retriever_tool = cls.create_retriever_tool()
            cls.retriever_tool_node = cls.create_retriever_tool_node()
        return super().__new__(cls)

    def __init__(self, user_id):
        # 메모리 저장소 생성 (그래프에 사용되기 때문에, 반드시 그래프 생성 이전에 선행되어야 함)
        super(Tools).__init__()
        self.memory = SqliteSaver(sqlite3.connect(self.SQLITE_CONNECTION_STRING, check_same_thread=False))
        self.graph: CompiledStateGraph = self.build_graph()
        self.id = user_id # TODO: 사용자별로 고유한 bot_id 필요

