from flask import Blueprint, jsonify
from server.db import run_query
from server.logger import logger
from .o import download_image, extract_text, compare_texts

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
            ocr_result:
              type: "string"
              enum: ["True", "False"]
            award_ocr_result:
              type: "string"
              enum: ["True", "False", "None"]
            review_id:
              type: "string"
      500:
        description: 서버 오류 발생

    """
    # review_img_query="""SELECT ri.image_urls
    # FROM reviews r
    # JOIN review_image_urls ri ON r.review_id = ri.review_id
    # WHERE r.review_id = %s;"""
    review_img_query="""SELECT image_urls
                    FROM review_image_urls
                    WHERE HEX(review_id)=%s"""
    review_img_path = run_query(review_img_query, (review_id,))

    award_img_query = "SELECT award_image_url FROM reviews WHERE hex(review_id) = %s;"
    award_img_path=run_query(award_img_query, (review_id, ))

    compare_query="SELECT activity_name FROM reviews WHERE hex(review_id)=%s"
    compare_text = run_query(compare_query, (review_id,))

    # OCR 실행
    if review_img_path:
      # ocr결과의 기본값은 False
      ocr_result = "False"
      for img_url in review_img_path:
        image_stream = download_image(img_url)
        extracted_text = extract_text(image_stream)
        ocr_result = compare_texts(extracted_text, compare_text[0])
        if ocr_result == "True":
           break
    if award_img_path[0][0]:
      award_image_stream = download_image(award_img_path[0])
      award_text = extract_text(award_image_stream)
      award_ocr_result = compare_texts(award_text, compare_text[0])
    else:
       award_ocr_result = "None"

    try:
        return jsonify({"ocr_result": ocr_result,
                        "award_ocr_result": award_ocr_result,
                        "review_id": review_id}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다."}), 500