from fastapi import APIRouter, Depends, HTTPException, Body
from backend.auth import verify_jwt_token
from backend.contract import contract, dao_contract, contract_files, get_contract_from_chain
import logging
import traceback
from typing import List
from web3 import Web3
from backend.contract import ACCOUNT_ADDRESS, PRIVATE_KEY, w3
import os

admin_router = APIRouter()

ADMIN_ADDRESSES = {
    "0x7315C7AD21E501faBFc86f3D546a8898be6D39b6".lower(),
    "0x08ae1529BeBF0eDe319A2A6bd546D1Cd3bD428BD".lower(),
}

@admin_router.get("/check-admin")
def check_admin(user_address: str = Depends(verify_jwt_token)):
    if user_address.lower() in ADMIN_ADDRESSES:
        return {"is_admin": True}
    else:
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")
    
def is_admin(address: str) -> bool:
    return address.lower() in ADMIN_ADDRESSES

@admin_router.get("/dao-votes/all")
def get_all_dao_votes(user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    all_votes = []
    all_trade_ids = contract.functions.getAllTradeIds().call()

    for trade_id in all_trade_ids:
        try:
            party_a, party_b = contract.functions.getVoters(trade_id).call()
            vote_status = contract.functions.getVoteStatus(trade_id).call()
            voted_a, voted_b, approved_a, approved_b, finalized = vote_status

            dao_vote = dao_contract.functions.getVoteResult(trade_id).call()
            processed = dao_vote[2]

            if finalized:
                data = get_contract_from_chain(trade_id)
                data.update({
                    "trade_id": trade_id,
                    "approvedA": approved_a,
                    "approvedB": approved_b,
                    "fileMoved": contract_files.get(trade_id, {}).get("moved", True),
                    "daoProcessed": processed,
                    "daoPassed": dao_vote[3] if processed else None,
                })
                all_votes.append(data)
        except Exception:
            logging.error(f"Error fetching DAO vote for trade_id {trade_id}:\n{traceback.format_exc()}")
            continue

    return {"dao_votes": all_votes}

@admin_router.get("/dao-votes/pending")
def get_pending_dao_votes(user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    pending_results = []
    all_trade_ids = contract.functions.getAllTradeIds().call()

    # 전체 DAO 투표자 목록 조회
    all_voters = dao_contract.functions.getVotersList().call()

    for trade_id in all_trade_ids:
        try:
            vote_status = contract.functions.getVoteStatus(trade_id).call()
            finalized = vote_status[4]

            if not finalized:
                continue

            dao_vote = dao_contract.functions.getVoteResult(trade_id).call()
            processed = dao_vote[2]

            if not processed:
                yes_voters = []
                no_voters = []
                not_voted = []

                # 각 투표자별 투표 상태 조회
                for voter in all_voters:
                    voted, approved = dao_contract.functions.getVoterVote(trade_id, voter).call()
                    if not voted:
                        not_voted.append(voter)
                    elif approved:
                        yes_voters.append(voter)
                    else:
                        no_voters.append(voter)

                data = get_contract_from_chain(trade_id)
                data.update({
                    "trade_id": trade_id,
                    "daoProcessed": processed,
                    "daoPassed": None,
                    "yesVoters": yes_voters,
                    "noVoters": no_voters,
                    "notVoted": not_voted,
                })
                pending_results.append(data)

        except Exception:
            logging.error(f"Error fetching pending DAO vote for trade_id {trade_id}:\n{traceback.format_exc()}")
            continue

    return {"pending_dao_votes": pending_results}

@admin_router.post("/dao-votes/finalize")
def finalize_dao_vote(
    trade_id: str = Body(...),
    passed: bool = Body(...),
    user_address: str = Depends(verify_jwt_token)
):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    try:
        # ✅ 최소 1명 이상이 vote() 했는지 확인
        voters = dao_contract.functions.getVotersList().call()
        voted_count = 0
        for voter in voters:
            voted, _ = dao_contract.functions.getVoterVote(trade_id, voter).call()
            if voted:
                voted_count += 1

        if voted_count == 0:
            raise HTTPException(status_code=400, detail="아직 DAO 투표가 시작되지 않았습니다. 최소 한 명 이상이 투표해야 완료할 수 있습니다.")

        # ✅ 트랜잭션 준비
        nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
        tx = dao_contract.functions.finalizeVote(trade_id).build_transaction({
            "from": ACCOUNT_ADDRESS,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.to_wei('30', 'gwei'),
            "chainId": int(os.getenv("CHAIN_ID", "11155111"))  # 기본값: Sepolia
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if tx_receipt.status != 1:
            raise RuntimeError("트랜잭션이 실패했습니다. TxHash: " + w3.to_hex(tx_hash))

        return {"success": True, "message": "2차 DAO 투표가 완료되었습니다.", "tx_hash": w3.to_hex(tx_hash)}

    except HTTPException:
        raise  # 위에서 raise한 HTTP 오류는 그대로 유지
    except Exception as e:
        logging.error(f"Error finalizing DAO vote for trade_id {trade_id}:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"트랜잭션 실패: {str(e)}")

@admin_router.post("/add-voter")
def add_voter(voter: str = Body(...), user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    try:
        tx = dao_contract.functions.addVoter(voter).buildTransaction({
            "from": user_address,
            # nonce, gas 등 설정 필요
        })

        # 서명 및 전송 별도 구현

        return {"success": True, "message": "새 투표 권한이 부여되었습니다."}
    except Exception:
        logging.error(f"Error adding voter {voter}:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="권한 부여 실패")


@admin_router.get("/dao-votes/voters")
def get_voters(user_address: str = Depends(verify_jwt_token)) -> List[str]:
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    try:
        voters = dao_contract.functions.getVotersList().call()
        return voters
    except Exception:
        logging.error(f"Error fetching voters list:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="투표자 목록 조회 실패")

@admin_router.get("/dao-votes/vote-status")
def get_voter_vote_status(trade_id: str, voter: str, user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    try:
        voted, approved = dao_contract.functions.getVoterVote(trade_id, voter).call()
        return {"voted": voted, "approved": approved}
    except Exception:
        logging.error(f"Error fetching vote status for voter {voter} and trade_id {trade_id}:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="투표 상태 조회 실패")

@admin_router.get("/dao-votes/completed")
def get_completed_dao_votes(user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    completed_votes = []
    all_trade_ids = contract.functions.getAllTradeIds().call()

    for trade_id in all_trade_ids:
        try:
            vote_status = contract.functions.getVoteStatus(trade_id).call()
            finalized = vote_status[4]

            if not finalized:
                continue

            dao_vote = dao_contract.functions.getVoteResult(trade_id).call()
            processed = dao_vote[2]

            if processed:
                data = get_contract_from_chain(trade_id)
                data.update({
                    "trade_id": trade_id,
                    "daoProcessed": processed,
                    "daoPassed": dao_vote[3],
                })
                # 찬성/반대자 리스트를 위한 추가 정보 로딩 (별도 함수로 만들면 좋음)
                # 예) data["yesVoters"], data["noVoters"] = get_vote_details(trade_id)

                completed_votes.append(data)
        except Exception as e:
            logging.error(f"Error fetching completed DAO vote for trade_id {trade_id}:\n{traceback.format_exc()}")
            continue

    return {"completed_dao_votes": completed_votes}

@admin_router.get("/check-admin")
def check_admin(user_address: str = Depends(verify_jwt_token)):
    if not is_admin(user_address):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")
    return {"message": "관리자 권한 확인됨"}