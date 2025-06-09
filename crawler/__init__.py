from flask import Blueprint, jsonify, request
from crawler.main_crawler import run_crawlers
from server.logger import logger

import threading

crawler_bp = Blueprint('crawler', __name__, url_prefix='/crawler')

# 상태 관리 변수
status = {
    "state": "idle",     # idle | running | done | error
    "error": None,
    "targets": None
}
lock = threading.Lock()

def background_crawl(targets):
    global status

    try:
        with lock:
            status["state"] = "running"
            status["error"] = None
            status["targets"] = targets or "all"

        run_crawlers(targets)

        with lock:
            status["state"] = "done"
    except Exception as e:
        logger.error(f"크롤러 실행 중 오류: {e}")
        with lock:
            status["state"] = "error"
            status["error"] = str(e)
    finally:
        pass

@crawler_bp.route('/run', methods=['GET'])
def start_crawler():
    """크롤러를 시작하는 API 엔드포인트
    
    Query Parameters:
        targets (str, optional): 쉼표로 구분된 크롤링 대상 목록
                                예: "bbc,wevity"
                                미지정시 모든 대상을 크롤링
    
    Returns:
        JSON: 
            - 성공시 (202):
                {
                    "message": "크롤러 실행 시작됨",
                    "targets": "<target_list>" or "all"
                }
            - 실행 중일 때 (429):
                {
                    "message": "이미 크롤러가 실행 중입니다."
                }
    """
    targets_param = request.args.get('targets')
    targets = [t.strip() for t in targets_param.split(',')] if targets_param else None

    with lock:
        if status["state"] == "running":
            return jsonify({"message": "이미 크롤러가 실행 중입니다."}), 429

        thread = threading.Thread(target=background_crawl, args=(targets,))
        thread.start()

    return jsonify({"message": "크롤러 실행 시작됨", "targets": targets or "all"}), 202


@crawler_bp.route('/status', methods=['GET'])
def get_crawler_status():
    """현재 크롤러의 상태를 조회하는 API 엔드포인트
    
    Returns:
        JSON (200):
            {
                "state": "idle" | "running" | "done" | "error",
                "error": "오류 메시지" or null,
                "targets": ["대상1", "대상2"] or "all" or null
            }
    """
    with lock:
        return jsonify({
            "state": status["state"],
            "error": status["error"],
            "targets": status["targets"]
        }), 200