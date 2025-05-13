from flask import Blueprint, request, jsonify
from server.logger import logger
from .o import extract_text, compare_texts

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/<review_id>', methods=['GET'])
def evaluate_image(review_id):
    
    # 데이터베이스에서 review_id를를 토대로 데이터를 가져옴(미구현)
    img_path=""
    compare_text = ""

    # OCR 실행
    extracted_text = extract_text(img_path)
    
    # 비교 실행
    result = compare_texts(extracted_text, compare_text)

    try:
        return jsonify({"llm_validation": result,
                        "review_id": review_id}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다."}), 500