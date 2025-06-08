from fastapi import FastAPI, UploadFile, Form, HTTPException, Query, Request, Depends, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from backend.utils import generate_pdf_hash, generate_trade_id
from backend.contract import register_contract_on_chain, get_contract_from_chain, contract, dao_contract, contract_files
from backend.auth import router as auth_router
from backend.auth import verify_jwt_token
import json
import os
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from backend.contract import router as contract_router
from typing import Optional
from web3 import Web3
from backend.contract import w3 as web3
from backend.admin import admin_router
from datetime import datetime, timezone, timedelta

app = FastAPI()

# 업로드 관련 디렉토리 생성
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PRIVATE_UPLOAD_DIR = "./private_uploads"
os.makedirs(PRIVATE_UPLOAD_DIR, exist_ok=True)



# DAO 컨트랙트 설정

# KST 타임존 정의
KST = timezone(timedelta(hours=9))

def format_timestamp_kst(timestamp: float) -> str:
    dt_kst = datetime.fromtimestamp(timestamp, KST)
    return dt_kst.strftime("%Y-%m-%d %H:%M:%S")

def finalize_contract(trade_id: str):
    info = contract_files.get(trade_id)
    if not info:
        return

    src = os.path.join(UPLOAD_DIR, info["filename"])
    dst = os.path.join(PRIVATE_UPLOAD_DIR, info["filename"])
    if os.path.exists(src):
        os.rename(src, dst)
        info["moved"] = True  # 상태 표시

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        max_upload_size = 10 * 1024 * 1024  # 10MB 제한
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_upload_size:
            return JSONResponse(status_code=413, content={"detail": "File too large"})
        return await call_next(request)

# CORS 및 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 배포 시 도메인 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LimitUploadSizeMiddleware)

app.include_router(auth_router, prefix="/auth")
app.include_router(contract_router)
app.include_router(admin_router, prefix="/api/admin")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in environment variables.")

security = HTTPBearer()



# 계약 등록 API
@app.post("/api/register")
async def register_contract(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    party_b: str = Form(...),
    user_address: str = Depends(verify_jwt_token)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file content.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")
    await file.close()

    # SHA256 해시 생성
    hash_value = generate_pdf_hash(content)

    # trade_id 및 스마트컨트랙트 등록
    trade_id = generate_trade_id()
    tx_hash = register_contract_on_chain(hash_value, asset_id, trade_id, user_address, party_b)

    # tx_hash를 기반으로 파일명 생성
    clean_tx_hash = tx_hash.lower()
    if clean_tx_hash.startswith("0x"):
        clean_tx_hash = clean_tx_hash[2:]
    filename = f"{clean_tx_hash}.pdf"

    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # trade_id → 파일 매핑 저장 (UTC 타임스탬프)
    contract_files[trade_id] = {
        "filename": filename,
        "timestamp": time.time()  # UTC timestamp
    }

    return {
        "message": "Contract registered",
        "trade_id": trade_id,
        "sha256": hash_value,
        "tx_hash": tx_hash
    }

# 계약 조회 API
@app.get("/api/contract")
def get_contract(trade_id: str = Query(...), tx_hash: Optional[str] = Query(None)):
    contract_data = get_contract_from_chain(trade_id, tx_hash)
    file_info = contract_files.get(trade_id)
    contract_data["fileMoved"] = file_info.get("moved", False) if file_info else True

    # KST 기준 timestamp 변환하여 응답에 추가
    if file_info and "timestamp" in file_info:
        contract_data["timestampKST"] = format_timestamp_kst(file_info["timestamp"])
    else:
        contract_data["timestampKST"] = None

    return contract_data

# 계약서 뷰어 API
@app.get("/api/contract/view")
def view_contract(trade_id: str):
    info = contract_files.get(trade_id)
    if not info or info.get("moved"):  # 이동된 파일은 비공개 처리
        raise HTTPException(status_code=404, detail="Not available")

    filepath = os.path.join(UPLOAD_DIR, info["filename"])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(filepath, media_type="application/pdf")

# 만료된 계약 파일 삭제 함수 (1일 = 86400초)
def delete_expired_contracts():
    now = time.time()
    expired = []

    for trade_id, info in contract_files.items():
        if now - info["timestamp"] > 86400:
            filepath = os.path.join(UPLOAD_DIR, info["filename"])
            if os.path.exists(filepath):
                os.remove(filepath)
            expired.append(trade_id)

    for trade_id in expired:
        del contract_files[trade_id]

# 루트 경로 index.html 반환 (로그인 화면)
@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# 계약서 정보 ABI 반환 API
@app.get("/api/contract-info")
def get_contract_info():
    abi_path = os.path.join(
        os.path.dirname(__file__),
        "../artifacts/contracts/ContractRegistry.sol/ContractRegistry.json"
    )
    with open(abi_path, "r", encoding="utf-8") as f:
        abi = json.load(f)["abi"]

    return {
        "contract_address": os.getenv("CONTRACT_ADDRESS"),
        "abi": abi
    }

# 투표 리스트 조회 API
@app.get("/api/vote-list")
def get_vote_list(user_address: str = Depends(verify_jwt_token)):
    results = []
    all_trade_ids = contract.functions.getAllTradeIds().call()
    for trade_id in all_trade_ids:
        try:
            party_a, party_b = contract.functions.getVoters(trade_id).call()
            if user_address.lower() in [party_a.lower(), party_b.lower()]:
                results.append(trade_id)
        except Exception:
            continue
    return {"eligible_trade_ids": results}

# 완료된 계약 조회 API (2차 DAO 결과 포함, timestampKST 추가)
@app.get("/api/finalized-contracts")
def get_finalized_contracts(user_address: str = Depends(verify_jwt_token)):
    finalized_results = []
    all_trade_ids = contract.functions.getAllTradeIds().call()
    for trade_id in all_trade_ids:
        try:
            party_a, party_b = contract.functions.getVoters(trade_id).call()
            vote_status = contract.functions.getVoteStatus(trade_id).call()
            voted_a, voted_b, approved_a, approved_b, finalized = vote_status

            is_related = user_address.lower() in [party_a.lower(), party_b.lower()]
            if is_related and finalized:
                data = get_contract_from_chain(trade_id)
                data["trade_id"] = trade_id
                data["voted"] = True
                data["finalized"] = True
                data["approvedA"] = approved_a
                data["approvedB"] = approved_b
                file_info = contract_files.get(trade_id, {})
                data["fileMoved"] = file_info.get("moved", True)

                # 2차 DAO 결과 포함
                try:
                    dao_vote = dao_contract.functions.getVoteResult(trade_id).call()
                    data["daoProcessed"] = dao_vote[2]  # processed
                    data["daoPassed"] = dao_vote[3]     # passed
                except Exception:
                    data["daoProcessed"] = False
                    data["daoPassed"] = None

                # KST 변환된 타임스탬프 추가
                if "timestamp" in file_info:
                    data["timestampKST"] = format_timestamp_kst(file_info["timestamp"])
                else:
                    data["timestampKST"] = None

                finalized_results.append(data)

        except Exception as e:
            print(f"Error processing trade_id {trade_id}: {e}")
            continue

    return {"finalized_contracts": finalized_results}
