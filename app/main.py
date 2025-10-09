from fastapi import FastAPI
import uvicorn
from router import router

# 독립 실행용 FastAPI 앱
app = FastAPI(
    title="Schedule Manager",
    description="일정 및 할일 관리 API",
    version="1.0.0"
)

# 라우터 등록
app.include_router(router, prefix="/schedule-manager")

# 루트 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "Schedule Manager API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )