from flask import Blueprint, jsonify, request
from flasgger import Swagger, swag_from

from server.logger import logger
from .o import download_image, extract_text, compare_texts

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/', methods=['POST'])
@swag_from({
    'summary': 'OCR 이미지 비교 API',
    'description': '이미지에서 텍스트를 추출하고 비교하는 API',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'image_urls': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': '검토할 이미지 URL 리스트'
                    },
                    'award_img_urls': {
                        'type': 'string',
                        'description': '수상 이미지의 URL'
                    },
                    'title': {
                        'type': 'string',
                        'description': '비교할 기준 텍스트'
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'OCR 결과 반환',
            'schema': {
                'type': 'object',
                'properties': {
                    'ocrResult': {'type': 'string', 'description': 'OCR 비교 결과'},
                    'awardOcrResult': {'type': 'string', 'description': '수상 이미지 OCR 비교 결과'}
                }
            }
        },
        500: {
            'description': '서버 에러 발생',
            'schema': {
                'type': 'object',
                'properties': {
                    'answer': {'type': 'string', 'description': '에러 메시지'}
                }
            }
        }
    }
})

def evaluate_image():


    data=request.get_json()

    review_img_path=data.get("imageUrls")
    award_img_path=data.get("awardImgUrl")
    compare_text=data.get("title")

    print(review_img_path)
    print(award_img_path)
    print(compare_text)
    # OCR 실행
    if review_img_path:
      # ocr결과의 기본값은 False
      ocr_result = "False"
      for img_url in review_img_path:
        image_stream = download_image(img_url)
        extracted_text = extract_text(image_stream)
        print(extracted_text)
        ocr_result = compare_texts(extracted_text, compare_text)
        if ocr_result == "True":
           break
    if award_img_path != None:
      award_image_stream = download_image(award_img_path)
      award_text = extract_text(award_image_stream)
      award_ocr_result = compare_texts(award_text, compare_text)
    else:
       award_ocr_result = "False"

    try:
        return jsonify({"ocrResult": ocr_result,
                        "awardOcrResult": award_ocr_result}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다."}), 500