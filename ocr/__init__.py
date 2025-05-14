from flask import Blueprint, jsonify
from server.db import run_query
from server.logger import logger
from .o import extract_text, compare_texts

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/<review_id>', methods=['GET'])
def evaluate_image(review_id):
    
    img_query="""SELECT ri.image_urls
    FROM reviews r
    JOIN review_image_urls ri ON r.review_id = ri.review_id
    WHERE r.review_id = '%s';"""
    img_path = run_query(img_query, (review_id,))
    compare_query="SELECT activity_name FROM reviews WHERE review_id='%s';"
    compare_text = run_query(compare_query, (review_id,))

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