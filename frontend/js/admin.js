import { ethers } from "https://cdn.jsdelivr.net/npm/ethers@6.7.0/dist/ethers.min.js";

if (!window.ethereum) {
  alert("메타마스크가 설치되어 있지 않습니다. 설치 후 이용해 주세요.");
}

let contract;

async function initContract() {
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const res = await fetch("/api/dao/contract-info", { credentials: "include" });
  const { contract_address, abi } = await res.json();
  contract = new ethers.Contract(contract_address, abi, signer);
}

async function logout() {
  try {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    alert("로그아웃되었습니다.");
    window.location.href = "/static/index.html";
  } catch (err) {
    alert("로그아웃 중 오류 발생: " + err.message);
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

async function fetchPendingVotes() {
  const tbody = document.getElementById("pendingVotesBody");
  const addVoterMsg = document.getElementById("addVoterMsg");
  addVoterMsg.textContent = "";
  tbody.innerHTML = "<tr><td colspan='5'>불러오는 중...</td></tr>";

  try {
    const res = await fetch("/api/admin/dao-votes/pending", { credentials: "include" });
    const data = await res.json();
    const votes = data.pending_dao_votes;

    if (votes.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5'>현재 처리할 투표가 없습니다.</td></tr>";
      return;
    }

    tbody.innerHTML = "";
    for (const v of votes) {
      const totalVoters = (v.yesVoters?.length ?? 0) + (v.noVoters?.length ?? 0) + (v.notVoted?.length ?? 0);
      const approveCount = v.yesVoters?.length ?? 0;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(v.trade_id)}</td>
        <td>${escapeHtml(v.contractHash || "")}</td>
        <td>${approveCount} / ${totalVoters}</td>
        <td>${v.daoProcessed ? "✅ 처리됨" : "❌ 미처리"}</td>
        <td>
          <button class="btn-vote" data-trade="${escapeHtml(v.trade_id)}" data-approve="true">찬성</button>
          <button class="btn-vote" data-trade="${escapeHtml(v.trade_id)}" data-approve="false">반대</button>
        </td>
      `;

      const detailTr = document.createElement("tr");
      const detailTd = document.createElement("td");
      detailTd.colSpan = 5;
      detailTd.style.fontSize = "0.9em";
      detailTd.style.color = "#555";

      detailTd.innerHTML = `
        <strong>찬성 투표자:</strong> ${v.yesVoters?.join(", ") || "없음"}<br>
        <strong>반대 투표자:</strong> ${v.noVoters?.join(", ") || "없음"}<br>
        <strong>미투표자:</strong> ${v.notVoted?.join(", ") || "없음"}
      `;
      detailTr.appendChild(detailTd);

      tbody.appendChild(tr);
      tbody.appendChild(detailTr);
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='5' style="color:red;">오류 발생: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function voteOnChain(tradeId, approve) {
  if (!contract) await initContract();

  const confirmMsg = `Trade ID: ${tradeId}\n정말 ${approve ? "찬성" : "반대"} 투표하시겠습니까?`;
  if (!confirm(confirmMsg)) return;

  try {
    const tx = await contract.vote(tradeId, approve);
    await tx.wait();
    alert(`투표 완료! TxHash: ${tx.hash}`);
    await fetchPendingVotes();
  } catch (err) {
    alert("트랜잭션 실패: " + err.message);
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await initContract();
  document.getElementById("logoutBtn").addEventListener("click", logout);

  document.getElementById("pendingVotesBody").addEventListener("click", (e) => {
    const target = e.target;
    if (target.classList.contains("btn-vote")) {
      const tradeId = target.dataset.trade;
      const approve = target.dataset.approve === "true";
      voteOnChain(tradeId, approve);
    }
  });

  const addVoterBtn = document.getElementById("addVoterBtn");
  const newVoterInput = document.getElementById("newVoterAddress");
  const msgElem = document.getElementById("addVoterMsg");

  addVoterBtn.addEventListener("click", async () => {
    const addr = newVoterInput.value.trim();
    msgElem.textContent = "";

    if (!addr) {
      msgElem.style.color = "red";
      msgElem.textContent = "지갑 주소를 입력하세요.";
      return;
    }

    try {
      const res = await fetch("/api/admin/add-voter", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voter: addr }),
      });
      const data = await res.json();
      msgElem.style.color = res.ok ? "green" : "red";
      msgElem.textContent = data.message || data.detail || "오류 발생";
      if (res.ok) newVoterInput.value = "";
      await fetchPendingVotes();
    } catch (err) {
      msgElem.style.color = "red";
      msgElem.textContent = "네트워크 오류: " + err.message;
    }
  });

  await fetchPendingVotes();
});
