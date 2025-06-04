import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Literal

# .env 파일에서 환경변수 로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = 'gemini-2.0-flash-lite'
DELAY = 2.5 # 무료티어 RPM 제한 (분당 30회) 방지
KEYWORDS = ['Economy','Environment','PeopleAndSociety','Technology']
DEFAULT_KEYWORD = KEYWORDS[0]

class Issue(BaseModel):
    title: str
    summary: str
    keyword: Literal['Economy','Environment','PeopleAndSociety','Technology']

def translate_and_categorize(title: str, summary: str) -> tuple[str, str, str]:
    """
    GEMINI API를 이용하여 영문 뉴스기사를 한글로 번역하고 키워드를 추출합니다.

    Parameters:
        title (str): 번역할 뉴스기사의 제목
        summary (str): 번역할 뉴스기사의 요약

    Returns:
        Tuple[str, str, str]: 한글로 번역된 뉴스기사의 제목과 요약 (오류 발생 시 원문 반환), 키워드 (오류 발생 시 기본값 반환)
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return title, summary, DEFAULT_KEYWORD # 기본값 반환

    time.sleep(DELAY) # 무료티어 제한 (분당 30회) 회피를 위해 일정시간 대기
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=MODEL,
            contents=f"""
                Translate the following English news article's title and summary into Korean.
                Additionally, categorize the article into one of the following keywords based on its content: {', '.join(KEYWORDS)}.

                Title: {title}
                Summary: {summary}""",
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=Issue,
            )
        )
        
        issue = Issue.model_validate_json(response.text)
        return issue.title, issue.summary, issue.keyword

    except Exception as e:
        print(f"❌ 번역 중 오류 발생, 원문을 반환합니다. : {e}")
        return title, summary, DEFAULT_KEYWORD

if __name__ == "__main__":
    title = "From cat urine to gunpowder: Exploring the peculiar smells of outer space"
    summary = "Scientists are analysing the smells of space – from Earth's nearest neighbours to planets hundreds of light years away – to learn about the make-up of the Universe."
    title, summary, keyword = translate_and_categorize(title, summary)
    print(f"출력결과\n번역된 제목 : {title}\n번역된 요약 : {summary}\n키워드 : {keyword}")