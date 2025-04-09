from flask import Blueprint, request, jsonify
from utils import confirm_request
from server.logger import logger
from .bot import Bot

chat_bp = Blueprint('chat', __name__, url_prefix='/chatbot')

@chat_bp.route('/<chat_id>', methods=['GET'])
def chat_with_watson():
    data = request.json
    if response_for_invalid_request := confirm_request(data, {
        'question': str
    }):
        return response_for_invalid_request


    bot = Bot()

    try:
        return jsonify({"answer": bot.ask(data['question'])}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다. 시스템, 또는 AI를 제공하는 외부 API의 문제일 수 있습니다."}), 500


