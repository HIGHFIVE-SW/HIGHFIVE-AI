import sqlite3
import typing
from typing import Literal, Annotated, Sequence, TypedDict, Union

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_teddynote.graphs import visualize_graph
from langchain_teddynote.models import get_model_name, LLMs
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from server.logger import logger
from .constants import indication_for_information_request, indication_for_recommendation_request
from .tools import tavily_search_tool, tavily_search_tool_node

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
    context: Annotated[Union[str, Sequence[BaseMessage]], "Context"]  # 문서의 검색 결과
    answer: Annotated[str, "Answer"]  # 답변
    debug: Annotated[bool, "Debug"]
    type: Annotated[Literal["information", "recommendation", "others"], "Type"]

def updated_state(state: GraphState, **updates) -> GraphState:
    """Graph의 State를 입력받고, 입력받은 State에서 **updates로 받은 딕셔너리를 반영해서 수정된 State를 반환하는 함수."""
    new_state: GraphState = state.copy()
    new_state.update(**updates)
    return new_state


def load_from_dict(data: dict, content_key: str, metadata_keys=None) -> Document:
    if metadata_keys is None:
        metadata_keys = []
    return Document(page_content=data[content_key],
                    metadata={key: data[key] for key in data.keys() if key in metadata_keys})


class LangGraphMethods:
    @staticmethod
    def ask_question(state: GraphState) -> GraphState:
        return updated_state(state, question=state.get("messages", [""])[-1].content)

    @staticmethod
    def classify_question(state: GraphState) -> Literal["information", "recommendation", "others"]:
        """
            사용자의 초기 질문을 바탕으로 정보 요청 질문인지, 추천 요청 질문인지, 기타 질문인지를 AI가 판단해서
            분류를 수행하는 함수.
            정보 요청일 경우 'information'을, '추천 요청일 경우 'recommendation'을, 기타 질문일 경우 'others'를 반환한다.
        """

        # 데이터 모델 정의
        class Classification(BaseModel):
            """A classification result for user question"""
            type: Literal["information", "recommendation", "others"] = Field(
                description="Response 'recommendation' if the user's question asks for a personal recommendation, "
                            "'information' if it requests newer information that can be searched on the web, "
                            "'others' if it requests general information, including those that reference previous conversation history."
            )

        # LLM 모델 초기화 -> 구조화된 출력을 위한 LLM 설정
        llm_with_structured_output = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True).with_structured_output(
            Classification)

        # 이진 분류를 요구하는 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a classifier responsible for categorizing user questions. 
            If the user's question asks for a personal recommendation, return 'recommendation'. 
            If the question requests newer information that can be searched on the web, return 'information'. 
            For the questions requests general information, including those that reference previous conversation history, return 'others'."""),
            ("human", "{question}")
        ])

        # prompt + llm 바인딩 체인 생성
        chain = prompt | llm_with_structured_output

        # 최초 질문 추출
        question = state["question"]

        # 질문 분류 실행
        classification_result = chain.invoke({"question": question})

        # AI의 결정에 따른 분기
        if classification_result.type == "information":
            if state.get("debug"):
                print("\n==== [DECISION: INFORMATION] ====\n")
            return "information"

        elif classification_result.type == "recommendation":
            if state.get("debug"):
                print("\n==== [DECISION: RECOMMENDATION] ====\n")
            state["context"] = ""
            return "recommendation"
        else:
            if state.get("debug"):
                print("\n==== [DECISION: OTHERS] ====\n")
            return "others"



    @staticmethod
    def search_web(state: GraphState) -> GraphState:
        # LLM 초기화
        llm = ChatOpenAI(model="gpt-4o-mini")

        # 도구와 LLM 결합, 툴이 반드시 tavily search tool을 호출하도록 고정
        llm_with_tools = llm.bind_tools([tavily_search_tool], tool_choice=tavily_search_tool.name)

        context_message = llm_with_tools.invoke(state["messages"][-1].content)

        return updated_state(state,
                             messages=[context_message],
                             context=context_message,
                             type="information")

    @staticmethod
    def recommend(state: GraphState, retriever_tool) -> GraphState:
        question = state["messages"][-1].content

        # LLM 모델 초기화
        model = ChatOpenAI(temperature=0, streaming=True, model=MODEL_NAME)

        # retriever tool 바인딩 & 도구를 호출하는 것을 강제
        model = model.bind_tools([retriever_tool], tool_choice=retriever_tool.name)

        # 에이전트 응답 생성
        context_message = model.invoke(question)

        return updated_state(state,
                             messages=[context_message],
                             context=context_message,
                             type="recommendation")

    # 모든 것이 검증된 후 context를 기반으로 답변을 생성하는 Graph Branch
    @staticmethod
    def generate(state: GraphState) -> GraphState:
        if state.get("debug"):
            print("\n=== NODE: generate ===\n")

        # prompt에 state["messages"]를 풀어서 같이 제공한다.
        # memory를 설정하면 state["messages"]에 계속해서 대화 기록이 저장되기 때문에,
        # 이를 AI가 받아서 이전 채팅 기록에 근거한 답변을 생성할 수 있게 된다.
        if state.get("context"):
            if state.get("type") == "recommendation":
                indication = indication_for_recommendation_request
            else:
                indication = indication_for_information_request
            prompt = ChatPromptTemplate.from_messages([
                *state["messages"],
                ("system", indication),
                ("human", "{question}"),
            ])
            # RAG 체인 구성.
            # StrOutParser()를 사용하면 결과가 문자열이 되어서 state["messages"]에 추가될 때 자동으로 HumanMessage로 타입이 변환되기 때문에,
            # Memory에 저장 후 AI에게 제공해도 AI가 이를 AI의 응답으로 인식하지 못한다.
            # 따라서 StrOutputParser는 사용하지 말자.
            rag_chain = prompt | ChatOpenAI(model_name=MODEL_NAME, temperature=0, streaming=True)

            # 답변 생성
            response = rag_chain.invoke({"context": state["messages"][-1].content, "question": state["question"]})
        else:
            response = ChatOpenAI(model_name=MODEL_NAME,
                                  temperature=0,
                                  streaming=True).invoke(state["messages"])

        return updated_state(state, node_name="generate", messages=[response])


    def build_graph(self: 'Bot') -> CompiledStateGraph:
        workflow: StateGraph = StateGraph(GraphState)

        workflow.add_node("ask_question", self.ask_question)
        workflow.add_node("search_web", self.search_web)
        workflow.add_node("tavily_search", tavily_search_tool_node)
        workflow.add_node("recommend", lambda state: self.recommend(state, self.retriever_tool))
        workflow.add_node("retrieve", self.retriever_tool_node)
        workflow.add_node("generate", self.generate)

        workflow.set_entry_point("ask_question")

        # 첫 분기(질문의 종류를 분류)
        workflow.add_conditional_edges(
            "ask_question",
            self.classify_question,
            {
                # 조건 출력을 그래프 노드에 매핑
                "recommendation": "recommend",
                "information": "search_web",
                "others": "generate",
            }
        )
        workflow.add_edge("search_web", "tavily_search")
        workflow.add_edge("tavily_search", "generate")
        workflow.add_edge("recommend", "retrieve")
        workflow.add_edge("retrieve", "generate")
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
        cursor.execute(query1, (self.id,))
        cursor.execute(query2, (self.id,))
        connection.commit()
        cursor.close()

    def visualize(self: 'Bot'):
        visualize_graph(self.graph)
