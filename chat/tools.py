import numpy as np
import typing
from typing import Callable, Optional, Literal

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.documents import Document
from langchain_core.tools import tool, Tool
from langgraph.prebuilt import ToolNode
from weaviate.collections.classes.filters import Filter

from server.db import run_query
from server.logger import logger
from utils import dict_to_xml
from .weaviate import WeaviateClientContext
from .constants import embed, weaviate_index_name

if typing.TYPE_CHECKING:
    from .bot import Bot
load_dotenv()

# 도구 생성
tavily_search_tool = TavilySearchResults(
    max_results=6,
    include_answer=True,
    include_raw_content=True,
    # include_images=True,
    # search_depth="advanced", # or "basic"
    include_domains=["google.com", "naver.com"],
    # exclude_domains = []
)

tavily_search_tool_node = ToolNode([tavily_search_tool])


def get_user_customized_embedding(user_id: bytes) -> Optional[list[float]]:
    vectors_of_user_history = [embed(row['activity_content']) for row in run_query("""
        SELECT activity_content
        FROM activities
        WHERE activity_id IN (
            SELECT activity_id
            FROM reviews
            WHERE user_id = %s
        );
    """, (user_id,)) if row['activity_content'] and isinstance(row['activity_content'], str)]

    return np.mean(np.array(vectors_of_user_history), axis=0).tolist() if vectors_of_user_history else None

def get_user_history(user_id: bytes):
    return [row['activity_id'] for row in run_query("""
        SELECT activity_id
        FROM reviews
        WHERE user_id = %s;
    """, (user_id,))]

def generate_documents(weaviate_response, limit:int=10) -> list[Document]:
    documents = []
    for i, obj in enumerate(weaviate_response.objects):
        if i >= limit:
            break
        page_content = obj.properties.get("activity_content") or ""
        metadata = {
            "activity name": obj.properties.get("activity_name"),
            "activity type": obj.properties.get("activity_type"),
            "site url": obj.properties.get("url"),
            "keyword": obj.properties.get("keyword"),
            "start date": obj.properties.get("start_date"),
            "end date": obj.properties.get("end_date"),
        }
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents

class Tools:
    def build_retriever_tool(self: 'Bot'):
        user_id:bytes = self.id

        def _build_exclusion_filter(history_ids: list[bytes]) -> Optional[Filter]:
            """
            사용자가 이미 리뷰한 activity_id를 제외하는 Weaviate 필터를 생성합니다.
            """
            filters = []
            for activity_id in history_ids:
                if activity_id and isinstance(activity_id, bytes):
                    # Weaviate에 저장된 activity_id는 16진수 문자열이므로 hex()로 변환
                    filters.append(
                        Filter.by_property("activity_id").not_equal(activity_id.hex())
                    )
            return Filter.all_of(filters) if filters else None

        @tool
        def retrieve_by_keyword(query: list[str]) -> str:
            """
            Retrieves a list of recommended activity documents for a specific user based on a natural language keyword query.

            This tool queries a Weaviate vector store to fetch activities that are semantically relevant to the provided keywords,
            excluding items the user has already interacted with. It returns the top N most relevant results.

            The result is formatted as an XML-style string containing both context (text content) and structured metadata fields
            (e.g., activity name, type, keyword, dates, etc.).

            Intended for use by agents needing to provide activity suggestions to users based on user's question.

            Args:
                query (list[str]): List of keyword strings for the search.
            Returns:
                str: A concatenated string of XML-formatted <document> blocks containing context and metadata for each activity.
            """
            limit = 10
            user_history_ids = get_user_history(user_id)
            logger.info(f"사용자(uuid: {user_id})가 이미 본 {len(user_history_ids)}개의 활동을 제외합니다.")
            exclusion_filter = _build_exclusion_filter(user_history_ids)

            with WeaviateClientContext() as client:
                collection = client.collections.get(weaviate_index_name)
                response = collection.query.near_text(
                    query=query,
                    filters=exclusion_filter,
                    limit=limit,
                )

            documents = generate_documents(response, limit)
            message = "\n\n".join(
                f"<document><context>{doc.page_content}</context>"
                f"<metadata>{dict_to_xml(doc.metadata)}</metadata></document>"
                for doc in documents
            )
            return message

        @tool
        def retrieve_by_history() -> str:
            """
            Retrieves a personalized list of recommended activity documents for a specific user based on their vector profile.

            This tool queries a Weaviate vector store to fetch activities that are semantically relevant to the user's interests,
            excluding items the user has already interacted with. It uses either a user-customized vector or a natural language
            query for retrieval, and returns the top N most relevant results.

            The result is formatted as an XML-style string containing both context (text content) and structured metadata fields
            (e.g., activity name, type, keyword, dates, etc.).

            Intended for use by agents needing to provide activity suggestions to users based on historical preferences.

            Returns:
                str: A concatenated string of XML-formatted <document> blocks containing context and metadata for each activity.
            """
            limit = 10
            user_history_ids = get_user_history(user_id)
            logger.info(f"사용자(uuid: {user_id})가 이미 본 {len(user_history_ids)}개의 활동을 제외합니다.")
            exclusion_filter = _build_exclusion_filter(user_history_ids)

            user_vector = get_user_customized_embedding(user_id)
            if not user_vector:
                return "사용자 이력이 없어 추천할 활동이 없습니다."

            with WeaviateClientContext() as client:
                collection = client.collections.get(weaviate_index_name)
                response = collection.query.near_vector(
                    near_vector=user_vector,
                    filters=exclusion_filter,
                    limit=limit,
                )

            documents = generate_documents(response, limit)
            message = "\n\n".join(
                f"<document><metadata>{dict_to_xml(doc.metadata)}</metadata>"
                f"<context>{doc.page_content}</context></document>"
                for doc in documents
            )
            return message

        return retrieve_by_keyword, retrieve_by_history