#!/bin/bash

cd ~/HIGHFIVE-AI/ || exit

# 패키지 업데이트 및 설치
pip-compile requirements.in
pip install -r requirements.txt

# 애플리케이션 실행
screen -dmS cicd python app.py
echo "Flask is running in a screen session."