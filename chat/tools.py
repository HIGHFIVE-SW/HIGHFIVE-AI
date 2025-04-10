from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode

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

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import SQLDatabaseLoader
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import create_retriever_tool
from langchain_core.prompts import PromptTemplate
import os
from typing import Any

host = os.getenv('MYSQL_DB_HOST')
username=os.getenv('MYSQL_DB_USER')
password=os.getenv('MYSQL_DB_PASSWORD')
database=os.getenv('MYSQL_DB_NAME')

from langchain_community.vectorstores import FAISS
from langchain_sqlserver.vectorstores import SQLServer_VectorStore
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import create_engine
from os.path import dirname, join

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}/{database}",
    echo=False,  # True일 경우 SQL 로그 출력 (디버깅용)
    future=True
)

def get_page_content(row) -> str:
    return str(row["activity_content"])

def get_metadata(row) -> dict[str, Any]:
    return {
       "id": row["activity_id"],
       "name": row["activity_name"],
       "type": row["activity_type"],
       "url": row["site_url"],
       "keyword": row["activity_id"],
       "start_date": row["start_date"],
       "end_date": row["end_date"],
   }

loader = SQLDatabaseLoader(query="SELECT `activity_id`, `activity_name`, `activity_content`, `activity_type`, `keyword`, `site_url`, `start_date`, `end_date`"
                                 "FROM activity;",
                           db=SQLDatabase(engine),
                           page_content_mapper=get_page_content,
                           metadata_mapper=get_metadata)
docs = loader.load()

# 단계 2: 문서 분할(Split Documents)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
split_documents = text_splitter.split_documents(docs)

# 단계 3: 임베딩(Embedding) 생성
# 임베딩을 생성한다.
# embedding = OpenAIEmbeddings()  # -> self._embedding 으로 저장한다음 바로 참조하기 때문에 생략됨

# 단계 4: DB 생성(Create DB) 및 저장
# 벡터스토어를 생성하고, 저장한다.
vectorstore = FAISS.from_documents(documents=split_documents, embedding=OpenAIEmbeddings())
vectorstore.save_local(folder_path = join(dirname(__file__), 'vectorstore'),
                       index_name="activity")
retriever = vectorstore.as_retriever()

# 도구 초기화
retriever_tool = create_retriever_tool(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 2}),  # 2개의 문서 검색,
    name="retrieve_global_activities",
    description="Searches and returns a few chat messages from the Telegram channel that are most relevant to the question or keywords.",
    document_prompt=PromptTemplate.from_template(
        """
        <document>
            <context>{page_content}</context>
            <metadata>
                <name>{name}</name>
                <type>{type}</type>
                <keyword>{keyword}</keyword>
                <start_date>{start_date}</start_date>
                <end_date>{end_date}</end_date>
            </metadata>
        </document>
        """
    ),
)

retriever_tool_node = ToolNode([retriever_tool])