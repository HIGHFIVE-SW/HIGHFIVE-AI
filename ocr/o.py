import os

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

# .env파일 로드
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"

def is_review_valid(title: str, image_urls: list[str]) -> bool:
    """
    리뷰 제목과 이미지들을 기반으로 리뷰가 유효한지 판단합니다.
    
    Args:
        title (str): 리뷰 제목
        image_urls (list[str]): 이미지 URL 리스트 (최대 5개 권장)
        
    Returns:
        bool: 리뷰가 유효하면 True, 그렇지 않으면 False
    """
    
    image_parts = []

    # 각 이미지 URL을 순회하며 이미지 바이트를 가져와 types.Part 객체로 변환
    for url in image_urls[:5]: # 최대 5개 이미지만 처리
        if url: # URL이 비어있지 않은지 확인
            try:
                response = requests.get(url, timeout=5) # 타임아웃 추가
                response.raise_for_status() # HTTP 오류 (4xx, 5xx) 발생 시 예외 발생
                
                # MIME 타입 확인 (없으면 기본값 사용)
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                
                # 이미지 바이트를 types.Part 객체로 변환하고 리스트에 추가
                image_part = types.Part.from_bytes(data=response.content, mime_type=content_type) 
                image_parts.append(image_part)
            except requests.exceptions.RequestException as e:
                print(f"경고: 이미지를 가져오거나 처리하는 데 실패했습니다. URL: {url}, 오류: {e}")
                continue
            except Exception as e:
                print(f"경고: 이미지 {url} 처리 중 예상치 못한 오류 발생: {e}")
                continue

    if not image_parts:
        print("경고: 유효한 이미지를 찾거나 가져오지 못했습니다. False를 반환합니다.")
        return False # 이미지가 없거나 모두 실패하면 유효하지 않다고 판단

    prompt = f"""리뷰 제목: "{title}"
    리뷰의 제목과, 이미지들에 포함된 텍스트를 하나씩 비교합니다. 
    하나라도 맞는 경우 문자열 True를 모두 아닐 경우 False를 반환합니다.
    """

    # 텍스트 프롬프트와 모든 이미지 파트를 contents 리스트로 결합
    contents = [prompt] + image_parts

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config={
                # 응답형식을 True, False로 제한
                #'response_mime_type': 'text/x.enum',
                #'response_schema': {
                #    "type": "STRING",
                #    "enum": ["True", "False"]
                }
            }
        )

        print("responsetext: ",response.text)
        return response.text.strip() == "True"

    except Exception as e:
        print(f"API 호출 실패: {e}")
        return False # API 호출 실패 시 유효하지 않다고 판단