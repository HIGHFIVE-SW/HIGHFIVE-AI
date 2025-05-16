from flask import Blueprint, jsonify
from server.db import run_query
from server.logger import logger
from .o import extract_text, compare_texts

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/<review_id>', methods=['GET'])
def evaluate_image(review_id):
    """
    이미지 평가 API
    ---
    parameters:
      - name: review_id
        in: path
        type: "string"
        required: true
        description: 리뷰 ID
    responses:
      200:
        description: 성공적으로 평가됨
        schema:
          type: object
          properties:
            llm_validation:
              type: boolean
            review_id:
              type: "string"
      500:
        description: 서버 오류 발생

    """
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

   # 문자열 "True" 또는 "False"를 실제 Boolean 값으로 변환
    if result == "True":
        result = True
    elif result == "False":
        result = False
    else:
        result = False  # 예상치 못한 값이면 False로 처리

    try:
        return jsonify({"llm_validation": result,
                        "review_id": review_id}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다."}), 500