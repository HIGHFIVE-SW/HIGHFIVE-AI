import os
import sys
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flasgger import Swagger
from server.logger import logger
from crawler.scheduler import start_scheduler, shutdown_scheduler

# test
# 현재 app.py 파일의 디렉토리 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 현재 작업 디렉토리 (실행 시, 커맨드라인에서 지정된 디렉토리)
current_working_directory = os.getcwd()
# 경로 비교 시 경로 형식을 통일하기 위해 normpath()를 사용
if os.path.normpath(current_working_directory) != os.path.normpath(current_dir):
    raise Exception(f"현재 작업 디렉토리({current_working_directory})가 기대하는 디렉토리({current_dir})가 아닙니다.")

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

swagger=Swagger(app)

# 모든 Blueprint 등록
from chat import chat_bp
app.register_blueprint(chat_bp)

from ocr import ocr_bp
app.register_blueprint(ocr_bp)

if __name__ == "__main__":
    logger.info("Flask server has started!")
    start_scheduler() # 스케줄러 실행
    try:
        app.run(host="0.0.0.0", port=5000, use_reloader=False)  # use_reloader=False로 스케줄러 중복 실행 방지
    except (KeyboardInterrupt, SystemExit): # 에러 발생시 스케줄러 종료
        shutdown_scheduler() 
        logger.info("Scheduler shut down due to server stop.")