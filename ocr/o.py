import torch
import os
import boto3
import numpy as np
import cv2
from dotenv import load_dotenv
from paddleocr import PaddleOCR
from openai import OpenAI
from io import BytesIO

# .env파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4"
ocr = PaddleOCR(lang="korean")

def download_image(img_path):
    """
    s3에서 이미지 다운로드 후 저장
    
    Args:
        img_path (str): s3상에 이미지 경로
    Returns:
        BytesIO: 이미지 데이터의 바이트스트림 객체
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")  # 원하는 리전
    )
    bucket_name='trendist'
    file_name = img_path
    image_stream = BytesIO()
    s3.download_fileobj(bucket_name, file_name, image_stream)
    image_stream.seek(0)

    return image_stream


def extract_text(image_stream):
    """
    BytesIO 객체의 이미지를 대상으로 OCR 수행
    
    Args:
        image_stream (BytesIO): 메모리에 저장된 이미지 데이터
    Returns:
        list: OCR 결과
    """
    # 스트림을 numpy 배열로 변환
    image_stream.seek(0)  # 읽기 위치 초기화
    file_bytes = np.frombuffer(image_stream.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)  # OpenCV를 사용하여 이미지 디코딩
    # OCR 수행
    ocr = PaddleOCR(lang='korean')  # 언어 설정 가능
    results = ocr.ocr(img, cls=True)
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