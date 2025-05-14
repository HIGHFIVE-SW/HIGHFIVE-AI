import torch
import os
from dotenv import load_dotenv
from paddleocr import PaddleOCR
from openai import OpenAI

# .env파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4"
ocr = PaddleOCR(lang="korean")

def extract_text(img_path):
    """ 
    이미지에서 텍스트 추출 
    
    Args:
        img_path (str): 이미지의 경로(url)
    Returns:
        str : ocr이미지에서 추출한 문자열 반환
    """
    results = ocr.ocr(img_path, cls=True)
    return " ".join(text for result in results for _, (text, _) in result)

def compare_texts(text1, text2):
    """ 
    ocr로 추출한 텍스트와 활동 제목 간의 관계 분석

    Args:
        text1 (str): 이미지에서 추출한 문자열
        text2 (str): 활동 제목에서의 문자열
    Returns:
         str: 관련이 있다 판단 시 True / 없다 판단 시 False를 반환
    """
    prompt = f"""
    Analyze the relationship between the following two texts. Determine whether they are conceptually or contextually related.
    If they are related, return True; otherwise, return False without additional explanation

    Text 1:
    {text1}
    Text 2:
    {text2}
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an objective analyst. Compare the following two texts and determine their relationship strictly based on content."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=600
    )

    return response.choices[0].message.content.strip()