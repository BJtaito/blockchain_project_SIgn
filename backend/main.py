from fastapi import FastAPI, UploadFile, Form, HTTPException, Query, File, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from backend.utils import generate_pdf_hash, generate_trade_id
from backend.contract import register_contract_on_chain, get_contract_from_chain, contract
from backend.auth import router as auth_router
import json
import os, jwt, time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from backend.contract import router as contract_router
from typing import Optional
import uuid
from web3 import Web3
from backend.contract import w3 as web3


app = FastAPI()
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PRIVATE_UPLOAD_DIR = "./private_uploads"
os.makedirs(PRIVATE_UPLOAD_DIR, exist_ok=True)
contract_files = {}

DAO_CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("DAO_CONTRACT_ADDRESS"))
with open("./artifacts/contracts/SecondDAO.sol/SecondDAO.json") as f:
    dao_abi = json.load(f)["abi"]

dao_contract = web3.eth.contract(address=DAO_CONTRACT_ADDRESS, abi=dao_abi)

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
app.include_router(contract_router)
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
    party_b: str = Form(...),
    user_address: str = Depends(verify_jwt_token)
):
    print("✅ 요청 도착")
    print(f"📦 file: {file.filename}")
    print(f"🧾 asset_id: {asset_id}")
    print(f"👤 party_b: {party_b}")
    print(f"🧑‍💼 user_address: {user_address}")    

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file content.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")
    await file.close()

    # ✅ SHA256 해시
    hash_value = generate_pdf_hash(content)

    # ✅ trade_id 및 스마트컨트랙트 등록
    trade_id = generate_trade_id()
    tx_hash = register_contract_on_chain(hash_value, asset_id, trade_id, user_address, party_b)

    # ✅ 파일 저장
    filename = f"{int(time.time())}_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # ✅ trade_id → 파일 매핑 저장 (1일 후 삭제용)
    contract_files[trade_id] = {
        "filename": filename,
        "timestamp": time.time()
    }

    return {
        "message": "Contract registered",
        "trade_id": trade_id,
        "sha256": hash_value,
        "tx_hash": tx_hash
    }
# 계약 조회
@app.get("/api/contract")
def get_contract(trade_id: str = Query(...), tx_hash: Optional[str] = Query(None)):
    contract_data = get_contract_from_chain(trade_id, tx_hash)
    file_info = contract_files.get(trade_id)
    contract_data["fileMoved"] = file_info.get("moved", False) if file_info else True
    return contract_data

@app.get("/api/contract/view")
def view_contract(trade_id: str):
    info = contract_files.get(trade_id)
    if not info or info.get("moved"):  # ✅ 이동된 파일은 비공개 처리
        raise HTTPException(status_code=404, detail="Not available")

    filepath = os.path.join(UPLOAD_DIR, info["filename"])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(filepath, media_type="application/pdf")

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
        
# 루트 경로 index.html 반환 (예: 로그인 화면)
@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

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
                data["fileMoved"] = contract_files.get(trade_id, {}).get("moved", True)

                # 2차 DAO 결과 포함
                try:
                    dao_vote = dao_contract.functions.getVoteResult(trade_id).call()
                    data["daoProcessed"] = dao_vote[2]  # processed
                    data["daoPassed"] = dao_vote[3]     # passed
                except Exception:
                    data["daoProcessed"] = False
                    data["daoPassed"] = False  # 미처리 상태 시 결과 표시 안 하려면 False로 초기화

                finalized_results.append(data)

        except Exception as e:
            print(f"Error processing trade_id {trade_id}: {e}")
            continue

    return {"finalized_contracts": finalized_results}