import os
from dotenv import load_dotenv
from datetime import datetime
from uuid import UUID
import typing
from contextlib import contextmanager
from typing import Any

from langchain_community.document_loaders import SQLDatabaseLoader
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, select, MetaData, Table, bindparam

if typing.TYPE_CHECKING:
    from .bot import Bot

from typing import Optional

from langchain_weaviate import WeaviateVectorStore
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter
from weaviate.client import WeaviateClient

from server.logger import logger
from .constants import weaviate_index_name, model
from .weaviate import connect_weaviate, WeaviateClientContext

from server.db import run_query

load_dotenv()

def get_page_content(row) -> str:
    return str(row["activity_content"])

metadata_mapping = {
    "activity_id": "activity_id",
    "activity_name": "activity_name",
    "activity_type": "activity_type",
    "site_url": "url",
    "keyword": "keyword",
    "start_date": "start_date",
    "end_date": "end_date",
}

def get_metadata(row) -> dict[str, Any]:
    metadata = {}

    # 필드명을 매핑된 키로 변환
    for k, v in row.items():
        if v is not None and (new_key:=metadata_mapping.get(k)):
            if isinstance(v, datetime):
                # RFC3339 타입. weaviate에서는 date 속성에 대해 이 타입의 문자열을 기대하기 때문에, 이렇게 하지 않으면 에러 발생
                metadata[new_key] = v.isoformat(timespec="seconds") + "Z"
            elif isinstance(v, bytes):
                metadata[new_key] = v.hex()
            else:
                metadata[new_key] = v

    return metadata

class VectorStoreMethods:
    """Weaviate 벡터스토어 연동 및 동기화 관련 메서드를 제공하는 클래스입니다."""

    @staticmethod
    def get_vectorstore(weaviate_client: Optional[WeaviateClient] = None) -> WeaviateVectorStore:
        """Weaviate 벡터스토어 인스턴스를 반환합니다.

        Args:
            weaviate_client (Optional[WeaviateClient]): 외부에서 전달받은 클라이언트 (없으면 새로 연결)

        Returns:
            WeaviateVectorStore: 벡터스토어 인스턴스
        """
        # 먼저 스키마 등록
        with WeaviateClientContext() as client:
            VectorStoreMethods.register_schema(client)

        return WeaviateVectorStore(
            client=weaviate_client if weaviate_client else connect_weaviate(),
            index_name="Activities",
            text_key="activity_content",
        )

    @staticmethod
    def register_schema(weaviate_client: WeaviateClient) -> None:
        """Weaviate에 스키마를 등록합니다.

        Args:
            weaviate_client (WeaviateClient): Weaviate 클라이언트
        """
        # 먼저 클래스가 존재하는지 확인
        if weaviate_index_name in weaviate_client.collections.list_all().keys():
            logger.info(f"{weaviate_index_name} already exists in Weaviate.")
            return

        weaviate_client.collections.create(
            weaviate_index_name,
            description="Activity information of Trendist",
            reranker_config=Configure.Reranker.cohere(),
            vectorizer_config=Configure.Vectorizer.text2vec_huggingface(
                    model="BAAI/bge-m3",  # The model to use, e.g. "nomic-embed-text"
                ),
            properties=[  # properties configuration is optional
                Property(name="activity_id", data_type=DataType.TEXT),
                Property(name="activity_name", data_type=DataType.TEXT),
                Property(name="activity_type", data_type=DataType.TEXT),
                Property(name="activity_content", data_type=DataType.TEXT),
                Property(name="keyword", data_type=DataType.TEXT),
                Property(name="url", data_type=DataType.TEXT),
                Property(name="start_date", data_type=DataType.DATE),
                Property(name="end_date", data_type=DataType.DATE),
            ]
        )
        logger.info("Activities vectorstore schema is created in Weaviate.")

    @classmethod
    def update_vectorstore(cls: 'Bot'):
        """MySQL과 Weaviate 벡터스토어를 동기화합니다.

        Returns:
            None
        """
        with WeaviateClientContext() as weaviate_client:
            weaviate_client.connect()
            ##### 1. Weaviate에서 activity_id 필터로 모든 _id 가져오기 #####
            weaviate_ids: set[str] = set()

            collection = weaviate_client.collections.get(weaviate_index_name)
            response = collection.query.fetch_objects(
                limit=10000,  # 10000이 최대인듯. 100000으로 하면 query maximum result exceeded 오류 발생
            )

            # 중복 제거용 dict: {(channelId, chatId): [uuid1, uuid2, ...]}
            duplicates: dict[str, list[str]] = {}

            for o in response.objects:
                props = o.properties or {}
                uuid = o.uuid
                activity_id = props.get("activity_id")
                weaviate_ids.add(activity_id)

                # activity_id가 중복되는 object의 uuid를 기록
                duplicates.setdefault(activity_id, []).append(uuid)

            # 중복된 activity id에서 첫 번째를 제외한 나머지를 삭제
            for activity_id, uuid_list in duplicates.items():
                if len(uuid_list) > 1:
                    # 첫 번째는 유지, 나머지 삭제
                    to_delete = uuid_list[1:]
                    if to_delete:
                        logger.warning(
                            f"Deleting duplicate Weaviate object: "
                            f"activity_id={activity_id}, "
                            f"uuid=(survived: {uuid_list[0]}, killed: {to_delete})")

                        collection.data.delete_many(
                            where=Filter.any_of([
                                Filter.by_id().equal(uuid) for uuid in uuid_list
                            ])
                        )


            ##### 2. MySQL에서 전체 id 리스트 확보 #####
            mysql_ids = {row['activity_id'].hex() for row in run_query("SELECT activity_id FROM activities")}
            logger.debug(f"MySQL에서 전체 activity id 리스트 확보: {len(mysql_ids)}개")

            ##### 3. 차집합: MySQL에는 있고 Weaviate에는 없는 id #####
            missing_activity_ids:list[bytes] = [UUID(aid).bytes for aid in (mysql_ids - weaviate_ids)]
            logger.info(f"MySQL에는 있고 Weaviate에는 업데이트되지 않은 activity id 리스트 확보: {len(mysql_ids)}개")


            ##### 4. MySQL에서 레코드 로드 후 Weaviate에 추가 #####
            if missing_activity_ids:
                with cls.build_loader(missing_activity_ids) as loader:
                    if docs := loader.load():  # 문서 목록이 비어 있지 않을 때만 추가(비어 있을 경우 add_documents() 에서 오류 발생)
                        # 단계 4: DB 생성(Create DB) 및 저장
                        # 벡터스토어를 생성하고, 저장한다.
                        docs = [doc for doc in docs if doc]
                        print(docs)
                        logger.debug(f"Adding documents to the vectorstore.")
                        cls.vectorstore.add_documents(docs)

            if weaviate_client.batch.failed_objects:
                for failed in weaviate_client.batch.failed_objects:
                    logger.error(f"Failed to insert documents into weaviate: {failed}")

    @staticmethod
    @contextmanager
    def build_loader(ids: list[bytes]) -> SQLDatabaseLoader:
        """MySQL에서 지정된 ID의 채팅 데이터를 로드하는 Document 로더를 반환합니다.

        Args:
            ids (list[str]): 로드할 채팅의 activity_id 목록

        Returns:
            SQLDatabaseLoader: MySQL Database 로더
        """
        host = os.getenv('MYSQL_DB_HOST')
        username = os.getenv('MYSQL_DB_USER')
        password = os.getenv('MYSQL_DB_PASSWORD')
        database = os.getenv('MYSQL_DB_NAME')

        # 연결 및 DB 유틸리티 생성
        engine = create_engine(
            f"mysql+pymysql://{username}:{password}@{host}/{database}",
            echo=True,  # SQL 로그 출력 (디버깅용)
            future=True
        )
        db = SQLDatabase(engine)

        # 테이블 메타정보 준비
        metadata = MetaData()
        activities = Table("activities", metadata, autoload_with=engine)

        # Select 객체 + 리스트 바인딩. Select 객체가 아닌 문자열만 사용하면 리스트 바인딩은 불가능.
        query = (
            select(activities)
            .where(activities.c.activity_id.in_(bindparam("ids", expanding=True)))
        )

        # SQLDatabaseLoader 생성
        loader = SQLDatabaseLoader(
            query=query,
            db=db,
            parameters={"ids": ids},  # 리스트 바인딩
            page_content_mapper=get_page_content,
            metadata_mapper=get_metadata
        )


        try:
            yield loader
        finally:
            engine.dispose()  # 안전하게 연결 종료