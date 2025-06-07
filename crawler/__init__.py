from flask import Blueprint, jsonify, request
from crawler.main_crawler import run_crawlers
from server.logger import logger

crawler_bp = Blueprint('crawler', __name__, url_prefix='/crawler') 

@crawler_bp.route('/', methods=['GET'])
def crawler():
    # GET 파라미터에서 targets 가져오기
    targets_param = request.args.get('targets')  # 예: 'bbc,wevity'

    # 파라미터가 있다면 리스트로 분할
    if targets_param:
        targets = [t.strip() for t in targets_param.split(',')]
    else:
        targets = None  # 전체 실행

    try:
        run_crawlers(targets)
        return jsonify({"message": "크롤러 실행 완료", "targets": targets or "all"}), 200
    except Exception as e:
        logger.error(f"크롤러 실행 중 오류: {e}")
        return jsonify({"error": str(e)}), 500