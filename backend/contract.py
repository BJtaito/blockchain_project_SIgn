from web3 import Web3
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from fastapi import APIRouter
from typing import Optional
from starlette.requests import Request
from fastapi import Depends
from fastapi.responses import JSONResponse

router = APIRouter()
load_dotenv()
contract_files = {}
w3 = Web3(Web3.HTTPProvider(os.getenv("SEPOLIA_RPC_URL")))

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = w3.eth.account.from_key(PRIVATE_KEY).address
ABI_FILE_PATH ="./artifacts/contracts/SecondDAO.sol/SecondDAO.json"
DAO_CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("DAO_CONTRACT_ADDRESS"))
with open(ABI_FILE_PATH) as f:
    dao_abi = json.load(f)["abi"]
dao_contract = w3.eth.contract(address=DAO_CONTRACT_ADDRESS, abi=dao_abi)


# ABI 및 주소 불러오기
ABI_PATH = os.path.join(
    os.path.dirname(__file__),
    "../artifacts/contracts/ContractRegistry.sol/ContractRegistry.json"
)

with open(ABI_PATH, "r", encoding="utf-8") as f:
    abi = json.load(f)["abi"]
contract = w3.eth.contract(address=os.getenv("CONTRACT_ADDRESS"), abi=abi)

def register_contract_on_chain(contract_hash: str, asset_id: str, trade_id: str, party_a: str, party_b: str) -> str:
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    # ✅ 주소를 체크섬 형식으로 변환
    party_a = Web3.to_checksum_address(party_a)
    party_b = Web3.to_checksum_address(party_b)

    # 📌 사전 Gas Estimate 수행
    try:
        gas_estimate = contract.functions.registerContract(
            contract_hash, asset_id, trade_id, party_a, party_b
        ).estimate_gas({"from": ACCOUNT_ADDRESS})
        print("⛽ Estimated gas:", gas_estimate)
    except Exception as e:
        print("❌ Gas estimation failed:", e)
        raise

    # ✅ 트랜잭션 구성
    tx = contract.functions.registerContract(
        contract_hash, asset_id, trade_id, party_a, party_b
    ).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": int(gas_estimate * 1.3),
        "gasPrice": w3.to_wei("30", "gwei"),
        "chainId": int(os.getenv("CHAIN_ID"))
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return w3.to_hex(tx_hash)


def get_contract_from_chain(trade_id: str, tx_hash: Optional[str] = None) -> dict:
    # ABI 로드
    ABI_PATH = os.path.join(
        os.path.dirname(__file__),
        "../artifacts/contracts/ContractRegistry.sol/ContractRegistry.json"
    )
    with open(ABI_PATH, "r", encoding="utf-8") as f:
        abi = json.load(f)["abi"]

    contract_address = os.getenv("CONTRACT_ADDRESS")
    if not contract_address or not Web3.is_address(contract_address):
        raise ValueError(f"Invalid or missing CONTRACT_ADDRESS: {contract_address}")
    contract = w3.eth.contract(Web3.to_checksum_address(contract_address), abi=abi)

    # 🔍 트랜잭션 검증 (tx_hash가 있을 경우만)
    if tx_hash:
        try:
            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt["to"].lower() != contract_address.lower():
                raise ValueError("Tx hash is not related to the target contract.")
        except Exception as e:
            raise RuntimeError(f"Failed to validate tx_hash: {e}")

    # 🔎 실제 데이터 조회
    try:
        contract_hash, asset_id, registrant, timestamp = contract.functions.getContract(trade_id).call()
        party_a, party_b = contract.functions.getVoters(trade_id).call()
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "contractHash": contract_hash,
            "assetId": asset_id,
            "registrant": registrant,
            "partyA": party_a,
            "partyB": party_b,
            "timestamp": timestamp,
            "datetime": dt
        }
    except Exception as e:
        raise RuntimeError(f"Failed to fetch contract from chain: {e}")


@router.get("/api/dao/contract-info")
async def get_contract_info():
    try:
        with open(ABI_FILE_PATH, "r", encoding="utf-8") as f:
            contract_json = json.load(f)
            abi = contract_json.get("abi")
        return {
            "contract_address": DAO_CONTRACT_ADDRESS,
            "abi": abi
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"ABI 로드 오류: {str(e)}"})
