#!/bin/bash

cd ~/HIGHFIVE-AI/ || exit

# 패키지 업데이트 및 설치
pip-compile requirements.in
pip install -r requirements.txt

# 기존의 스크린 삭제 후 재실행
screen -S flask-server -X quit
screen -dmS flask-server bash -c "cd ~/HIGHFIVE-AI && python app.py"
echo "Flask is running in a screen session."