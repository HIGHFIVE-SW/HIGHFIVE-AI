"""Weaviate 벡터스토어 연결 및 컨텍스트 관리 유틸리티 모듈."""
import weaviate
from weaviate import WeaviateClient
from weaviate.classes.init import Auth
from dotenv import load_dotenv
import os

from .constants import weaviate_headers
from server.logger import logger
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import Sort

load_dotenv()

weaviate_url = os.getenv("WEAVIATE_URL")
weaviate_api_key = os.getenv("WEAVIATE_API_KEY")


def connect_weaviate() -> WeaviateClient:
    """로컬 Weaviate 인스턴스에 연결합니다.

    Returns:
        WeaviateClient: 연결된 Weaviate 클라이언트
    """

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
        headers=weaviate_headers,
    )

    if client.is_ready():
        logger.info(f"Weaviate Client is in ready.")
    else:
        logger.critical(f"Weaviate Client is not in ready!")

    return client


class WeaviateClientContext:
    """with 문에서 Weaviate 클라이언트 연결을 관리하는 컨텍스트 매니저 클래스입니다."""
    def __enter__(self):
        """컨텍스트 진입 시 Weaviate 클라이언트 연결을 반환합니다."""
        self.client = connect_weaviate()
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 종료 시 클라이언트 연결을 닫습니다."""
        if hasattr(self.client, "close"):
            self.client.close()


def parse_filter_node(node: dict):
    """Weaviate 필터 노드를 재귀적으로 파싱하여 Filter 객체로 변환합니다.

    Args:
        node (dict): 필터 조건 노드

    Returns:
        _Filters: 변환된 Weaviate Filter 객체
    """
    if "and" in node:
        return Filter.all_of([parse_filter_node(sub) for sub in node["and"]])
    if "or" in node:
        return Filter.any_of([parse_filter_node(sub) for sub in node["or"]])
    if "field" in node and "op" in node:
        field = node["field"]
        op = node["op"]
        value = node["value"]
        base = Filter.by_property(field)

        match op:
            case "eq": return base.equal(value)
            case "neq": return base.not_equal(value)
            case "gt": return base.greater_than(value)
            case "gte": return base.greater_or_equal(value)
            case "lt": return base.less_than(value)
            case "lte": return base.less_or_equal(value)
            case "like": return base.like(value)
            case "contains_any": return base.contains_any(value)
            case "contains_all": return base.contains_all(value)
            case "isnull": return base.is_none(value)
            case _: raise ValueError(f"Unsupported operator: {op}")

    raise ValueError("Invalid filter node structure")

def parse_sort_list(sort_json: list[dict]):
    """
        Converts a list of sort conditions into a chained Sort object.

        Each element in sort_json must be a dict like:
            { "field": "views", "direction": "desc" }

        Returns:
            Sort object with multiple fields chained via .by_property()
    """
    sort_obj = None
    for i, item in enumerate(sort_json):
        if i == 0:
            sort_obj = Sort.by_property(
                name=item["field"],
                ascending=(item["direction"] == "asc")
            )
        else:
            sort_obj = sort_obj.by_property(
                name=item["field"],
                ascending=(item["direction"] == "asc")
            )
    return sort_obj