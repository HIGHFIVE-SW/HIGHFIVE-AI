import torch
from paddleocr import PaddleOCR
from openai import OpenAI


client = OpenAI(api_key="") # 나중에 api키 교체
model = "gpt-4"
ocr = PaddleOCR(lang="korean")

def extract_text(img_path):
    """ 이미지에서 텍스트 추출 """
    results = ocr.ocr(img_path, cls=True)
    return " ".join(text for result in results for _, (text, _) in result)

def compare_texts(text1, text2):
    """ 두 텍스트 간의 관계 분석 """
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