from openai import OpenAI
import os
from dotenv import load_dotenv

# .env파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4"

def summarize_translate_en_to_ko(text: str) -> str:
    """
    영어 텍스트를 한국어로 번역하고 요약.

    Args:
        text (str): 번역하고자 하는 원문(영어) 텍스트
    Returns: 
        str: 요약된 한국어 번역 결과
    """
    prompt = f"""
    Translate and summarize the following English text **into Korean** in **one or two sentences only**.
    Focus on capturing the key message, and write naturally in Korean.

    Text:
    {text}
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional translator and summarizer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=600
    )

    return response.choices[0].message.content.strip()