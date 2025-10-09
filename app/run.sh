#!/bin/bash

# Schedule Manager 독립 실행 스크립트
echo "📅 Schedule Manager 시작 중..."

# 가상환경이 있으면 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 가상환경 활성화됨"
fi

# 의존성 설치
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ 의존성 설치 완료"
fi

# FastAPI 서버 실행
echo "🌐 Schedule Manager API 서버 실행 (포트: 8002)"
python main.py