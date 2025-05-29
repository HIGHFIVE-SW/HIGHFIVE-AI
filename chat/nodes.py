from typing import Callable, Literal

from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_teddynote.models import get_model_name, LLMs

from .datamodel import GraphState
from .indications import Indications
from .tools import tavily_search_tool

# 최신 모델이름 가져오기
MODEL_NAME = get_model_name(LLMs.GPT4o)

def update_state(state: GraphState, node_name: str, **updates) -> GraphState:
    """Graph의 State를 입력받고, 입력받은 State에서 **updates로 받은 딕셔너리를 반영해서 수정된 State를 반환하는 함수.

    Args:
        state (GraphState): 기존 상태 객체
        node_name (str): 노드 이름
        **updates: 추가로 반영할 상태 값들

    Returns:
        GraphState: 업데이트된 상태 객체
    """
    new_state: GraphState = state.copy()
    new_state.update(**updates)
    return new_state



class LangGraphNodes:
    """LangGraph 기반 RAG 워크플로우의 각 노드(질문, 분류, 검색, 생성 등)를 정의하는 클래스입니다."""
    # Root Nodes
    @staticmethod
    def ask_question(state: GraphState) -> GraphState:
        """질문 노드: 사용자의 질문을 State에 저장합니다.

        Args:
            state (GraphState): 현재 상태

        Returns: v
            GraphState: 질문이 반영된 새로운 상태
        """
        if state.get("debug"):
            print("\n=== NODE: question ===\n")
        question = state["messages"][-1].content
        return update_state(state,
                            node_name="question",
                            question=question,
                            type="others"
                            )

    @staticmethod
    def classify_question(state: GraphState) -> Literal["web", "recommend", "others"]:
        """
            사용자의 초기 질문을 바탕으로 정보 요청 질문인지, 추천 요청 질문인지, 기타 질문인지를 AI가 판단해서
            분류를 수행하는 함수.
            정보 요청일 경우 'information'을, '추천 요청일 경우 'recommendation'을, 기타 질문일 경우 'others'를 반환한다.
        """

        # 데이터 모델 정의
        class Classification(BaseModel):
            """A classification result for user question"""
            type: Literal["web", "recommend", "others"] = Field(
                description="Response 'recommend' if the user's question asks for a personal recommendation, "
                            "'web' if it requests newer information that can be searched on the web, "
                            "'others' if it requests general information, including those that reference previous conversation history."
            )

        # LLM 모델 초기화 -> 구조화된 출력을 위한 LLM 설정
        llm_with_structured_output = ChatOpenAI(temperature=0, model=MODEL_NAME, streaming=True).with_structured_output(
            Classification)

        # 이진 분류를 요구하는 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            ("system", Indications.CLASSIFY),
            ("human", "{question}")
        ])

        # prompt + llm 바인딩 체인 생성
        chain = prompt | llm_with_structured_output

        # 최초 질문 추출
        question = state["question"]

        # 질문 분류 실행
        classification_result = chain.invoke({"question": question})

        # AI의 결정에 따른 분기
        if classification_result.type == "web":
            if state.get("debug"):
                print("\n==== [DECISION: INFORMATION] ====\n")
            return "web"

        elif classification_result.type == "recommend":
            if state.get("debug"):
                print("\n==== [DECISION: RECOMMENDATION] ====\n")
            return "recommend"
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

        ai_msg = llm_with_tools.invoke(state["question"])

        return update_state(state,
                            messages=[ai_msg],
                            node_name="search_web",
                            type="web")

    tavily_search_tool_node = ToolNode([tavily_search_tool])

    @staticmethod
    def execute_search(state: GraphState, retriever_from_weaviate: Callable) -> GraphState:
        """Weaviate에서 사용자의 활동 기록에 맞는 추천 활동을 검색하고, 결과를 state에 반영합니다.

        Args:
            state (GraphState): 현재 상태
            retriever_from_weaviate (Tool): 검색할 user_id가 반영된 retriever tool

        Returns:
            GraphState: 검색 결과가 반영된 새로운 상태
        """
        if state.get("debug"):
            print("\n=== NODE: execute_search ===\n")

        llm_with_tools = ChatOpenAI(temperature=0,
                                    model=MODEL_NAME,
                                    streaming=True).bind_tools([retriever_from_weaviate])

        prompt = ChatPromptTemplate.from_messages([
            # ("system", indication),
            ("human", "{question}"),
        ])
        chain = prompt | llm_with_tools

        ai_msg = chain.invoke({"question": "Call the retriever tool."})

        messages = [ai_msg]
        # 결과를 ToolMessage로 변환
        for tool_call in ai_msg.tool_calls:
            selected_tool = {
                "retriever_from_weaviate": retriever_from_weaviate,
            }[tool_call["name"].lower()]
            tool_msg = selected_tool.invoke(tool_call)
            messages.append(tool_msg)

        return update_state(state,
                            node_name="execute_search",
                            messages=messages,
                            type="recommend",
                            )

    @staticmethod
    def handle_error(state: GraphState) -> GraphState:
        """에러 발생 시 상태를 업데이트하는 노드입니다.

        Args:
            state (GraphState): 현재 상태

        Returns:
            GraphState: 에러 노드가 반영된 상태
        """
        if state.get("debug"):
            print("\n=== NODE: handle error ===\n")
        return update_state(state, node_name="handle_error")

    # 모든 것이 검증된 후 context를 기반으로 답변을 생성하는 Graph Branch
    @staticmethod
    def generate(state: GraphState) -> GraphState:
        """최종 답변을 생성하는 노드입니다.

        Args:
            state (GraphState): 현재 상태

        Returns:
            GraphState: 답변 메시지가 추가된 상태
        """
        if state.get("debug"):
            print("\n=== NODE: generate ===\n")

        match state["type"]:
            case "web":         indication = Indications.WEB
            case "recommend":   indication = Indications.RECOMMENDATION
            case _:             indication = Indications.OTHERS

        # 기존 state["messages"]에 새로운 지시와 질문을 더해서 같이 제공한다.
        # memory를 설정하면 state["messages"]에 계속해서 대화 기록이 저장되기 때문에,
        # 이를 AI가 받아서 이전 채팅 기록에 근거한 답변을 생성할 수 있게 된다.
        # 메시지 슬라이스 길이 제한
        max_messages = 50

        # 1. 최근 메시지 최대 50개 가져오기
        recent_messages = state["messages"][-min(len(state["messages"]), max_messages):]

        # 2. 첫 system/human 메시지부터 시작하도록 자르기
        def trim_to_first_valid_start(messages):
            for idx, message in enumerate(messages):
                if isinstance(message, HumanMessage) or isinstance(message, SystemMessage):
                    return messages[idx:]
            return []  # 유효한 시작점이 없으면 빈 리스트 반환

        # 3. ChatPromptTemplate 생성
        trimmed_messages = trim_to_first_valid_start(recent_messages)

        prompt = ChatPromptTemplate.from_messages([
            # 최대 50개 대화 메세지를 기억으로 저장. toolmessage 등도 다 반영되기 때문에 실제로는 10번 정도의 질의응답 상호작용을 기억할 것.
            *trimmed_messages,
            ("system", indication),
            ("human", "{question}"),
        ])

        # RAG 체인 구성.
        # StrOutParser()를 사용하면 결과가 문자열이 되어서 state["messages"]에 추가될 때 자동으로 HumanMessage로 타입이 변환되기 때문에,
        # Memory에 저장 후 AI에게 제공해도 AI가 이를 AI의 응답으로 인식하지 못한다.
        # 따라서 StrOutputParser는 사용하지 말자.
        rag_chain = prompt | ChatOpenAI(model_name=MODEL_NAME, temperature=0)

        # 답변 생성
        response = rag_chain.invoke({"question": state.get("question", "")})

        return update_state(state,
                            node_name="recommend",
                            messages=[response],
                            )