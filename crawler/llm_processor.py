import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from enum import Enum

# .env 파일에서 환경변수 로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = 'gemini-2.0-flash-lite'
DELAY = 2.5 # 무료티어 RPM 제한 (분당 30회) 방지

class Keyword(str, Enum):
    ECONOMY = 'Economy'
    ENVIRONMENT = 'Environment'
    PEOPLE_AND_SOCIETY = 'PeopleAndSociety'
    TECHNOLOGY = 'Technology'

DEFAULT_KEYWORD = Keyword.PEOPLE_AND_SOCIETY
KEYWORDS = [k.value for k in Keyword]

class Issue(BaseModel):
  title: str
  summary: str
  keyword: Keyword

class Activity(BaseModel):
  keyword: Keyword

def summarize_and_categorize_issue(title: str, content: str) -> tuple[str, str, str]:
  """
  GEMINI API를 이용하여 영문 뉴스기사를 한글로 번역, 요약하고 키워드를 추출합니다.

  Parameters:
    title (str): 번역할 뉴스기사의 제목
    content (str): 번역할 뉴스기사의 내용

  Returns:
    Tuple[str, str, str]: 한글로 번역된 뉴스기사의 제목과 요약 (오류 발생 시 원문 반환), 키워드 (오류 발생 시 기본값 반환)
  """

  if not GEMINI_API_KEY:
    print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    return title, content, DEFAULT_KEYWORD # 기본값 반환

  time.sleep(DELAY) # 무료티어 제한 (분당 30회) 회피를 위해 일정시간 대기
  try:
    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
      model=MODEL,
      contents=f"""
        You are a professional assistant that helps translate and summarize English news articles into Korean.
        Please perform the following tasks based on the article provided below:

        1. Translate the title into Korean.
        2. Summarize the content in **3 sentences** in Korean.
        3. Choose **one most relevant keyword** that best represents the article. Select only from this list: {', '.join(KEYWORDS)}.

        Respond strictly in the following JSON format:
        {{
            "title": "<Korean translated title>",
            "summary": "<3-sentence Korean summary>",
            "keyword": "<one keyword from the list>"
        }}

        ---
        Title: {title}

        Content: {content}
        """,
      config=types.GenerateContentConfig(
        system_instruction="You are an assistant that helps translate English news articles into Korean and summarizes them.",
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=Issue,
      )
    )
    
    issue = Issue.model_validate_json(response.text)
    return issue.title, issue.summary, issue.keyword.value

  except Exception as e:
    print(f"❌ 번역 중 오류 발생, 원문을 반환합니다. : {e}")
    return title, content, DEFAULT_KEYWORD
    
def extract_activity_keyword(content: str) -> str:
  """
  GEMINI API를 이용하여 활동 내용에 적절한 키워드를 반환합니다.

  Parameters:
      content (str): 활동 내용

  Returns:
      str: 활동 내용에 맞는 키워드
  """

  if not GEMINI_API_KEY:
    print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    return DEFAULT_KEYWORD # 기본값 반환
  
  time.sleep(DELAY)
  try:
    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
      model=MODEL,
      contents=f"""
        Read the following activity description and choose the **most appropriate keyword** from the provided list.
        Only output **one keyword**, exactly as it appears in the list. Do not add any extra words or punctuation.

        Volunteer Description:
        {content}

        Keyword List:
        {', '.join(KEYWORDS)}
        """,
      config=types.GenerateContentConfig(
        system_instruction="Choose one of the keywords given that best describes activity.",
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=Activity,
      )
    )

    activity = Activity.model_validate_json(response.text)
    return activity.keyword.value
  
  except Exception as e:
    print(f"❌ 키워드 추출 중 오류 발생, 기본 키워드를 반환합니다. : {e}")
    return DEFAULT_KEYWORD