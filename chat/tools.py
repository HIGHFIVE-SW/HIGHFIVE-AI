from dotenv import load_dotenv
import typing
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolNode
from langchain_core.tools import create_retriever_tool, Tool
from langchain_core.prompts import PromptTemplate

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

class Tools:
    retriever_tool: Tool
    retriever_tool_node: ToolNode
    def __init__(self: 'Bot'):
        self.retriever_tool = self.create_retriever_tool()
        self.retriever_tool_node = self.create_retriever_tool_node()

    # 도구 초기화
    @classmethod
    def create_retriever_tool(cls: 'Bot') -> Tool:
        return create_retriever_tool(
            retriever=cls.vectorstore.as_retriever(search_kwargs={"k": 5}),  # 5개의 문서 검색,
            name="retrieve_global_activities",
            description="Searches and returns information of some activities that are most relevant to the question or keywords.",
            document_prompt=PromptTemplate.from_template(
                """
                <document>
                    <context>{page_content}</context>
                    <metadata>
                        <name>{name}</name>
                        <site_url>{url}</site_url>
                        <start_date>{start_date}</start_date>
                        <end_date>{end_date}</end_date>
                        <source_site>{source_site}</source_site>
                    </metadata>
                </document>
                """
            ),
        )

    @classmethod
    def create_retriever_tool_node(cls: 'Bot') -> ToolNode:
        return ToolNode([cls.retriever_tool])