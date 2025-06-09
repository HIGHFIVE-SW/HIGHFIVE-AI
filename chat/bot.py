import sqlite3
import threading
from os.path import join, dirname, abspath
from typing import Union, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from .graph import LangGraphMethods
from .nodes import LangGraphNodes
from .tools import Tools
from .vectorstore import VectorStoreMethods

class Bot(LangGraphMethods, VectorStoreMethods, Tools, LangGraphNodes):
    _instances: dict[bytes, 'Bot'] = {}
    _lock: threading.Lock = threading.Lock()
    SQLITE_CONNECTION_STRING: str = join(dirname(abspath(__file__)),
                                         f"chats.db")  # base.py와 같은 경로에 SQLITE memory file 생성
    vectorstore:Optional[WeaviateVectorStore] = None

    def __new__(cls, user_id: bytes, *args, **kwargs):
        """
            싱글톤 객체의 변형 구현.
            입력받은 user id에 대응하는 챗봇이 없을 경우에 한해,
            고유한 Bot 객체를 새로 만들고 반환하는 동시에 _instances에 내부적으로 저장한다.

            만약 해당 user id에 대응하는 챗봇이 이미 생성되었을 경우,
            그 챗봇을 반환한다.
        """
        with cls._lock:
            # user_id에 해당하는 인스턴스가 있는지 확인
            if user_id not in cls._instances:
                # 없다면 새로 생성
                instance = super().__new__(cls)
                cls._instances[user_id] = instance
                return instance
            
            # 있다면 기존 인스턴스 반환
            return cls._instances[user_id]

    def __init__(self, user_id:bytes):
        # 메모리 저장소 생성 (그래프에 사용되기 때문에, 반드시 그래프 생성 이전에 선행되어야 함)
        # 챗봇이 호출될 때마다 Bot 클래스 속성인 vectorstore를 업데이트
        with Bot._lock:
            if hasattr(self, "_initialized"):
                return
            self._initialized = True
        self.memory = SqliteSaver(sqlite3.connect(self.SQLITE_CONNECTION_STRING, check_same_thread=False))
        self.id: bytes = user_id
        self.graph: CompiledStateGraph = self.build_graph()

Bot.vectorstore = Bot.get_vectorstore()