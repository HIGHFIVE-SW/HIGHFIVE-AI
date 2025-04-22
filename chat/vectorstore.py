import os
from os.path import exists, join
import typing
from typing import Any
from datetime import datetime

import faiss
from dotenv import load_dotenv
from langchain_community.docstore import InMemoryDocstore
from langchain_community.document_loaders import SQLDatabaseLoader
from langchain_community.utilities import SQLDatabase
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, select, Table, MetaData, and_, or_, null

from .constants import vectorstore_dir, vectorstore_index_name, openai_dimension_size

if typing.TYPE_CHECKING:
    from .bot import Bot

load_dotenv()

host = os.getenv('MYSQL_DB_HOST')
username=os.getenv('MYSQL_DB_USER')
password=os.getenv('MYSQL_DB_PASSWORD')
database=os.getenv('MYSQL_DB_NAME')

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}/{database}",
    echo=False,  # True일 경우 SQL 로그 출력 (디버깅용)
    future=True
)

def get_page_content(row) -> str:
    return str(row["content"])

def get_metadata(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["activity_name"],
        # "type": row["activity_type"],
        "url": row["site_url"],
        # "keyword": row["keyword"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "source_site": row["source_site"],
   }

class VectorStoreMethods:
    @classmethod
    def initialize_vectorstore(cls: 'Bot') -> FAISS:
        faiss_file_path = join(vectorstore_dir, vectorstore_index_name + '.faiss')
        pkl_file_path = join(vectorstore_dir, vectorstore_index_name + '.pkl')
        if exists(faiss_file_path) and exists(pkl_file_path):
            vectorstore: FAISS = FAISS.load_local(folder_path=vectorstore_dir,
                                                  index_name=vectorstore_index_name,
                                                  embeddings=cls.embeddings,
                                                  allow_dangerous_deserialization=True)
        else:
            vectorstore: FAISS = FAISS(
                embedding_function=cls.embeddings,
                index=faiss.IndexFlatL2(openai_dimension_size), # IndexFlatL2는 정확도가 높고 속도가 느려, 작은 데이터셋에 적합한 인덱싱 함수.
                docstore=InMemoryDocstore(),
                index_to_docstore_id={}
            )

        return vectorstore

    @classmethod
    def update_vectorstore(cls:'Bot'):
        ##### 단계 1: 문서 로드(Load Documents) #####
        # vectorstore에 저장된 모든 id(=activity.activity_id) 확인
        ids_in_vectorstore:set[str] = {
            str(doc.metadata.get("id"))
            for doc_id in cls.vectorstore.index_to_docstore_id.values()
            for doc in [cls.vectorstore.docstore.search(doc_id)]
            if "id" in doc.metadata
        }

        # SQL alchemy로 activity 컬럼에서 모든 id 조회
        metadata = MetaData()
        activity_table = Table("activities", metadata, autoload_with=engine)
        now = datetime.now()
        stmt = select(activity_table.c.id).where(
            and_(
                or_(activity_table.c.start_date.is_(None), activity_table.c.start_date <= now),
                or_(activity_table.c.end_date.is_(None), activity_table.c.end_date >= now)
            )
        )
        # stmt에 조건을 추가하려면 .where(activity_table.c.end_date < datetime.now())와 같이 .where() 메서드를 사용
        print(str(stmt.compile(compile_kwargs={"literal_binds": True})))
        with engine.connect() as conn:
            results = conn.execute(stmt).fetchall()

        from server.logger import logger
        logger.debug(f"벡터스토어에서 retrieve: {len(results)}개의 활동 조회")
        # 결과 추출
        activity_ids:set[str] = {str(row[0]) for row in results}

        ids_to_add:list[str] = [
            doc_id for doc_id in activity_ids
            if not doc_id in ids_in_vectorstore
        ]
        ids_to_delete:list[str] = [
            doc_id for doc_id in ids_in_vectorstore
            if not doc_id in activity_ids
        ]

        # 제거할 문서는 제거
        if ids_to_delete: # delete() 메서드에 빈 배열 입력 시 오류 발생 -> 배열이 있을 때만 호출
            cls.vectorstore.delete(ids_to_delete)

        # 추가할 문서는 추가
        # placeholder와 parameters를 미리 지정해서 SQLAlchemy 방식(:param)으로 바인딩
        if not ids_to_add:
            return # 추가할 문서가 없을 경우 종료
        
        placeholders = []
        parameters = {}
        for i, val in enumerate(ids_to_add):
            key = f"id_{i}"
            placeholders.append(f":{key}")
            parameters[key] = val
        
        loader = SQLDatabaseLoader(query=f"""
        SELECT `id`, `activity_name`, `content`, `site_url`, `start_date`, `end_date`, `source_site` 
        FROM activities WHERE `id` IN ({",".join(placeholders)});""",
                                   parameters=parameters,
                                   db=SQLDatabase(engine),
                                   page_content_mapper=get_page_content,
                                   metadata_mapper=get_metadata)
        docs = loader.load()

        # 단계 2: 문서 분할(Split Documents)
        text_splitter:RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        split_documents:list[Document] = text_splitter.split_documents(docs)

        # 단계 3: 임베딩(Embedding) 생성
        # 임베딩을 생성한다.
        # embedding = OpenAIEmbeddings()  # -> self._embedding 으로 저장한다음 바로 참조하기 때문에 생략됨

        # 단계 4: DB 생성(Create DB) 및 저장
        # 벡터스토어를 생성하고, 저장한다.

        cls.vectorstore.add_documents(documents=split_documents, embedding=cls.embeddings)
        cls.vectorstore.save_local(folder_path=vectorstore_dir,
                                   index_name=vectorstore_index_name)