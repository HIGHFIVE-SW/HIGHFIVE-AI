import sqlite3
import typing
from typing import Literal, Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_teddynote.graphs import visualize_graph
from langchain_teddynote.models import get_model_name, LLMs
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from server.logger import logger

load_dotenv()

if typing.TYPE_CHECKING:
    from .bot import Bot

# 최신 모델이름 가져오기
MODEL_NAME = get_model_name(LLMs.GPT4o_MINI)


# 에이전트 상태를 정의하는 타입 딕셔너리. 메시지 시퀀스를 관리하고 추가 동작 정의
class GraphState(TypedDict):
    # add_messages reducer 함수를 사용하여 메시지 시퀀스를 관리
    messages: Annotated[Sequence[BaseMessage], add_messages]
    question: Annotated[str, "Question"]  # 질문
    debug: Annotated[bool, "Debug"]
    type: Annotated[Literal["information", "recommendation", "others"], "Type"]


class LangGraphMethods:
    def build_graph(self: 'Bot') -> CompiledStateGraph:
        workflow: StateGraph = StateGraph(GraphState)

        workflow.add_node("ask_question", self.ask_question)
        workflow.add_node("search_web", self.search_web)
        workflow.add_node("tavily", self.tavily_search_tool_node)
        workflow.add_node("execute_search", lambda state: self.execute_search(state, self.build_retriever_tool()))
        workflow.add_node("generate", self.generate)

        workflow.set_entry_point("ask_question")

        # 첫 분기(질문의 종류를 분류)
        workflow.add_conditional_edges(
            "ask_question",
            self.classify_question,
            {
                # 조건 출력을 그래프 노드에 매핑
                "recommend": "execute_search",
                "web": "search_web",
                "others": "generate",
            }
        )
        workflow.add_edge("search_web", "tavily")
        workflow.add_edge("tavily", "generate")
        workflow.add_edge("execute_search", "generate")
        workflow.set_finish_point("generate")

        compiled_workflow: CompiledStateGraph = workflow.compile(checkpointer=self.memory)

        return compiled_workflow

    def ask(self: 'Bot', question: str) -> str:
        self.update_vectorstore()
        inputs = {
            "messages": [
                ("user", question)
            ]
        }
        # config 설정(재귀 최대 횟수, thread_id)
        config = RunnableConfig(recursion_limit=10, configurable={"thread_id": self.id})

        # RecursionError에 대비해서 미리 상태 백업
        saved_state = self.graph.get_state(config)
        try:
            answer = self.graph.invoke(
                inputs,
                config=config,
            )["messages"][-1].content if self.graph else "그래프가 생성되지 않았습니다."
        except RecursionError as e:
            # RecursionError 발생 시, answer에 대응 메세지를 대입하고 graph를 안전한 상태로 롤백
            answer = "답변을 생성하지 못했습니다. 질문이 이해하기 어렵거나, 서비스와 관련 없는 내용인 것 같습니다. 질문을 바꿔서 다시 입력해 보세요."
            self.graph.update_state(config, saved_state.values)

            logger.info(f"Chatbot answered to a question. Q: '{question}', A: '{answer}'")

        return answer

    def clear_message_history(self: 'Bot'):
        """
            주어진 세션(session_id)에 해당하는 메시지 히스토리를 삭제하는 메서드.
        """
        query1 = "DELETE FROM `checkpoints` WHERE `thread_id` = ?"
        query2 = "DELETE FROM `writes` WHERE `thread_id` = ?"
        connection = sqlite3.connect(self.SQLITE_CONNECTION_STRING, check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute(query1, (repr(self.id),))
        cursor.execute(query2, (repr(self.id),))
        connection.commit()
        cursor.close()

    def visualize(self: 'Bot'):
        visualize_graph(self.graph)
