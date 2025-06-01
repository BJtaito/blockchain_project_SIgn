from fastapi import FastAPI, UploadFile, Form, HTTPException, Query, File, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from backend.utils import generate_pdf_hash, generate_trade_id
from backend.contract import register_contract_on_chain, get_contract_from_chain
from backend.auth import router as auth_router
import os, jwt, time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

app = FastAPI()

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        max_upload_size = 10 * 1024 * 1024  # 10MB
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_upload_size:
            return JSONResponse(status_code=413, content={"detail": "File too large"})
        return await call_next(request)
    
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에만 허용, 배포 시 도메인 지정 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LimitUploadSizeMiddleware)
app.include_router(auth_router, prefix="/auth")

# 정적 파일 서빙
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in environment variables.")
JWT_EXPIRE_SECONDS = 1800  # 30분
security = HTTPBearer()

# JWT 검증

def verify_jwt_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS512"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
# 계약 등록
@app.post("/api/register")
async def register_contract(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    user_address: str = Depends(verify_jwt_token)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()

    if not content.startswith(b"%PDF"):
        print("📛 업로드된 파일의 시그니처가 유효하지 않음")
        raise HTTPException(status_code=400, detail="Invalid PDF file content.")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")
    await file.close()
    hash_value = generate_pdf_hash(content)
    trade_id = generate_trade_id()
    tx_hash = register_contract_on_chain(hash_value, asset_id, trade_id)

    return {
        "message": "Contract registered",
        "trade_id": trade_id,
        "sha256": hash_value,
        "tx_hash": tx_hash
    }

# 계약 조회
@app.get("/api/contract")
def get_contract(trade_id: str = Query(...), tx_hash: str = Query(...)):
    return get_contract_from_chain(trade_id, tx_hash)


# 루트 경로 index.html 반환 (예: 로그인 화면)
@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
