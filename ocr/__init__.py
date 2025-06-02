from flask import Blueprint, jsonify, request
from flasgger import Swagger, swag_from

from server.logger import logger
from .o import is_review_valid

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
                    'imageUrls': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': '검토할 이미지 URL 리스트'
                    },
                    'awardImageUrl': {
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

    imageUrls=data.get("imageUrls")
    awardImageUrl=data.get("awardImageUrl")
    title=data.get("title")

    # OCR 실행
    if imageUrls:
      # ocr결과의 기본값은 False
      ocr_result = "False"
      ocr_result=is_review_valid(title, imageUrls)    
    if awardImageUrl != None:
       print(awardImageUrl)
       awardImageUrlList=[awardImageUrl]
       award_ocr_result=is_review_valid(title,awardImageUrlList)
    else:
       award_ocr_result = "False"

    try:
        return jsonify({"ocrResult": ocr_result,
                        "awardOcrResult": award_ocr_result}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다."}), 500