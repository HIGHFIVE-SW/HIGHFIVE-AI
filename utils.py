from flask import jsonify
from typing import get_origin, get_args, Any, Union, Literal

def is_valid_type(value, expected_type):
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin is Union:
        # Union 타입 처리: 여러 타입 중 하나라도 만족하면 True
        return any(is_valid_type(value, arg) for arg in args)

    elif origin is Literal:
        # Literal 타입: 고정된 값 중 하나여야 함
        return value in args

    elif origin is list:
        if not isinstance(value, list):
            return False
        if args:  # e.g. list[str]
            return all(is_valid_type(item, args[0]) for item in value)
        return True

    elif origin is dict:
        if not isinstance(value, dict):
            return False
        if args:  # e.g. dict[str, int]
            key_type, value_type = args
            return all(is_valid_type(k, key_type) and is_valid_type(v, value_type)
                       for k, v in value.items())
        return True

    elif origin is tuple:
        if not isinstance(value, tuple):
            return False
        if args:
            return all(is_valid_type(v, t) for v, t in zip(value, args))
        return True

    elif isinstance(expected_type, type):
        return isinstance(value, expected_type)

    return False

def confirm_request(data: dict, required: dict[str, Any]):
    if not data:
        return jsonify({"error": "Please provide JSON request body."}), 400

    for key, expected_type in required.items():
        if key not in data:
            return jsonify({"error": f"Please provide '{key}' field in the JSON request body."}), 400
        if not is_valid_type(data[key], expected_type):
            return jsonify({
                "error": f"Field '{key}' has invalid datatype or value. "
                         f"Expected {expected_type}, got {data[key]!r} ({type(data[key]).__name__})"
            }), 400

    return None

def compare_dicts_sorted(
        dict1: dict[str, list[int]],
        dict2: dict[str, list[int]]
) -> bool:
    """두 개의 딕셔너리를 비교해서 원소가 완벽히 동일하면 참을, 그렇지 않으면 거짓을 반환하는 함수."""
    # 두 딕셔너리의 키 집합이 동일한지 확인
    if set(dict1.keys()) != set(dict2.keys()):
        return False

    # 각 키별로 정렬된 리스트를 비교 (중복을 고려)
    for key in dict1:
        if sorted(dict1[key]) != sorted(dict2[key]):
            return False

    return True


import requests

def request_api(**request_kwargs):
    """간단한 API 요청 함수."""
    if request_kwargs.get('method') == "GET":
        return requests.get(request_kwargs.get('url'), params=request_kwargs['params'])
    elif request_kwargs.get('method') == "POST":
        return requests.post(request_kwargs.get('url'), json=request_kwargs['data'])
    else:
        return requests.models.Response()

class ApiResponse:
    def __init__(self, response):
        self.status_code = response.status_code
        try:
            self.data = response.json()
        except Exception as e:
            self.data = response.reason

    def __repr__(self):
        string = f"status: {self.status_code}\nresponse:"
        if isinstance(self.data, dict):
            for key, value in self.data.items():
                string += f"\n\t{key}: {value}"
        else:
            string += f"\t{self.data}"
        return string

def api_test(**request_kwargs):
    return ApiResponse(request_api(**request_kwargs))