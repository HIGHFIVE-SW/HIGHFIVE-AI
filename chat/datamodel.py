from typing import Any, Literal, Annotated, Sequence, TypedDict, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, Json


# 데이터 모델 정의
class Classification(BaseModel):
    """Classification result for user question."""
    question_classification: Literal["data", "others"] = Field(
        description="""Response 'data' if the question is based on data of telegram channel and chats(e.g. channel id, send time, views, sale contact, recruitment, drug product type, sale place, price, discount event, how to buy etc.),
                       'others' if the question is just only general question(e.g. greetings, questions based on ONLY previous chat history NOT telegram channel or chats...)"""
    )

class GraphState(TypedDict):
    """
    에이전트 상태를 정의하는 타입 딕셔너리.
    메시지 시퀀스를 관리하고 추가 동작 정의
    """
    # add_messages reducer 함수를 사용하여 메시지 시퀀스를 관리
    messages: Annotated[Sequence[BaseMessage], add_messages]
    question: Annotated[str, "Question"]  # 질문
    debug: Annotated[bool, "Debug"]
    type: Annotated[Literal["web", "recommend", "others"], "Type"]