import numpy as np
import typing
from typing import Callable, Optional

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.documents import Document
from langchain_core.tools import tool
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

class Tools:
    def build_retriever_tool(self: 'Bot') -> Callable:
        user_id:bytes = self.id
        self.update_vectorstore()

        @tool
        def retriever_from_weaviate() -> str:
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
            limit = 2
            user_activity_history:list[bytes] = get_user_history(user_id)
            logger.info(f"사용자(uuid: {user_id})가 이미 활동한 {len(user_activity_history)}개의 활동을 제외합니다.")
            activity_id_list = [
                # bytes 객체이고, weaviate에는 문자열로 저장되어 있기 때문에 16진수 문자열로 변환
                Filter.by_property("activity_id").not_equal(activity_id.hex())
                for activity_id in user_activity_history if activity_id and isinstance(activity_id, bytes)
            ]
            filter_obj = Filter.all_of(activity_id_list) if activity_id_list else None

            user_customized_vector = get_user_customized_embedding(user_id)
            if not user_customized_vector:
                return "There is no activity history of this user!"

            with WeaviateClientContext() as client:
                collection = client.collections.get(weaviate_index_name)

                query = None
                # near_text or fetch_objects
                if query:
                    # rerank된 결과로 10개를 고정적으로 받아오고, 그 후 limit으로 잘라낸다.
                    response = collection.query.near_text(
                        query=query,
                        filters=filter_obj,
                        # sort: 벡터 검색 수행 시에는 sort 인자는 사용 불가!
                        limit=10  # limit은 사용 가능하긴 한데 벡터 검색 시에는 불필요함. 대신 rerank한 결과에서 나중에 limit만큼 잘라낼것
                    )
                else:
                    response = collection.query.near_vector(
                        near_vector=user_customized_vector,
                        filters=filter_obj,
                        # sort: 벡터 검색 수행 시에는 sort 인자는 사용 불가!
                        limit=limit
                    )

                # 결과를 LangChain Document로 변환
                documents = []
                for i, obj in enumerate(response.objects):
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

            message = "\n\n".join(
                f"<document><context>{doc.page_content}</context><metadata>{dict_to_xml(doc.metadata)}</metadata></document>"
                for doc in documents
            )

            return message

        return retriever_from_weaviate