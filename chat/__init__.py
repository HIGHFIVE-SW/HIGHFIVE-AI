from flask import Blueprint, request, jsonify
from typing import Literal
from uuid import UUID
from utils import confirm_request
from server.logger import logger
from .bot import Bot

chat_bp = Blueprint('chat', __name__, url_prefix='/chatbot')

@chat_bp.route('/<uuid:user_id>/web', methods=['GET'])
def ask_web_to_watson(user_id:UUID):
    """
        웹 검색 기반 질문 응답 API
        ---
        parameters:
          - name: user_id
            in: path
            type: string
            required: true
            description: 사용자 UUID
          - name: question
            in: query
            type: string
            required: true
            description: 사용자의 질문
          - name: request
            in: query
            type: string
            enum: ["ask", "reset"]
            required: true
            description: "요청 유형 (ask: 질문, reset: 대화 초기화)"
        responses:
          200:
            description: 성공 응답
            schema:
              type: object
              properties:
                answer:
                  type: string
        """
    return chat_with_watson(user_id, "web")
@chat_bp.route('/<uuid:user_id>/keyword-recommendation', methods=['GET'])
def ask_keyword_to_watson(user_id:UUID):
    """
        키워드 추천 질문 응답 API
        ---
        parameters:
          - name: user_id
            in: path
            type: string
            required: true
            description: 사용자 UUID
          - name: question
            in: query
            type: string
            required: true
            description: 키워드 추천 관련 질문
          - name: request
            in: query
            type: string
            enum: ["ask", "reset"]
            required: true
            description: "요청 유형 (ask: 질문, reset: 대화 초기화)"
        responses:
          200:
            description: 성공 응답
            schema:
              type: object
              properties:
                answer:
                  type: string
        """
    return chat_with_watson(user_id, "keyword")
@chat_bp.route('/<uuid:user_id>/history-recommendation', methods=['GET'])
def ask_history_to_watson(user_id:UUID):
    """
        활동 이력 기반 추천 질문 응답 API
        ---
        parameters:
          - name: user_id
            in: path
            type: string
            required: true
            description: 사용자 UUID
          - name: question
            in: query
            type: string
            required: true
            description: 이력 기반 추천 관련 질문
          - name: request
            in: query
            type: string
            enum: ["ask", "reset"]
            required: true
            description: "요청 유형 (ask: 질문, reset: 대화 초기화)"
        responses:
          200:
            description: 성공 응답
            schema:
              type: object
              properties:
                answer:
                  type: string
        """
    return chat_with_watson(user_id, "history")
@chat_bp.route('/<uuid:user_id>/others', methods=['GET'])
def ask_others_to_watson(user_id:UUID):
    """
        기타 질문 응답 API
        ---
        parameters:
          - name: user_id
            in: path
            type: string
            required: true
            description: 사용자 UUID
          - name: question
            in: query
            type: string
            required: true
            description: 기타 질문
          - name: request
            in: query
            type: string
            enum: ["ask", "reset"]
            required: true
            description: "요청 유형 (ask: 질문, reset: 대화 초기화)"
        responses:
          200:
            description: 성공 응답
            schema:
              type: object
              properties:
                answer:
                  type: string
        """
    return chat_with_watson(user_id, "others")

def chat_with_watson(user_id:UUID, question_type:Literal["web", "keyword", "history", "others"]):
    user_id:bytes = user_id.bytes
    data = request.args
    if response_for_invalid_request := confirm_request(data, {
        'question': str,
        'request': Literal["ask", "reset"]
    }):
        return response_for_invalid_request

    if data['request'] == "ask":
        return jsonify({"answer": Bot(user_id).ask(data['question'], question_type)}), 200
        # try:
        #     return jsonify({"answer": Bot(user_id).ask(data['question'])}), 200
        # except Exception as e:
        #     logger.error(e)
        #     return jsonify({"answer": f"죄송합니다. 에러가 발생했습니다. 시스템, 또는 AI를 제공하는 외부 API의 문제일 수 있습니다."}), 500
    else:
        Bot(user_id).clear_message_history() # TODO: 버그 발생중. 확인 필요
        return jsonify({"message": "success"}), 200


