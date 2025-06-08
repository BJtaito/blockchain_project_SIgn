let contract = null;
let userAddress = null;

// ✅ 로그인 확인 (쿠키 기반)
async function checkLoginStatus() {
  try {
    const res = await fetch("/auth/me", { credentials: "include" });
    if (res.status === 401) {
      alert("로그인이 필요합니다.");
      window.location.href = "/static/index.html";
    } else {
      const user = await res.json();
      userAddress = user.address.toLowerCase();
    }
  } catch (err) {
    console.error("세션 확인 오류:", err);
    alert("네트워크 오류로 로그인 상태를 확인할 수 없습니다.");
    window.location.href = "/static/index.html";
  }
}

// ✅ 로그아웃 처리
async function logout() {
  await fetch("/auth/logout", {
    method: "POST",
    credentials: "include"
  });
  alert("로그아웃되었습니다.");
  window.location.href = "/static/index.html";
}

// ✅ 초기화
window.addEventListener("DOMContentLoaded", async () => {
  await checkLoginStatus();

  try {
    const contractRes = await fetch("/api/contract-info");
    const { abi, contract_address } = await contractRes.json();
    const web3 = new Web3(window.ethereum);
    contract = new web3.eth.Contract(abi, contract_address);

    await loadEligibleVotes();
  } catch (err) {
    console.error("🚨 초기화 실패:", err);
    alert("초기 로딩 중 오류 발생");
  }
});

// ✅ 투표 가능한 계약 목록 불러오기
async function loadEligibleVotes() {
  const container = document.getElementById("voteListSection");
  container.innerHTML = "⏳ 로딩 중...";

  try {
    const allTradeIds = await contract.methods.getAllTradeIds().call();
    const eligible = [];
    const completed = [];

    const checks = await Promise.all(allTradeIds.map(async (tradeId) => {
      try {
        const voterTuple = await contract.methods.getVoters(tradeId).call();
        const partyA = voterTuple[0];
        const partyB = voterTuple[1];

        const status = await contract.methods.getVoteStatus(tradeId).call();

        return { tradeId, partyA, partyB, status };
      } catch (e) {
        console.warn(`❌ tradeId ${tradeId} 처리 중 오류`, e);
        return null;
      }
    }));

    checks.filter(Boolean).forEach(({ tradeId, partyA, partyB, status }) => {
      const isA = userAddress === partyA.toLowerCase();
      const isB = userAddress === partyB.toLowerCase();
      const voted = isA ? status[0] : isB ? status[1] : false;

      if ((isA || isB) && !voted) {
        eligible.push(tradeId);
      } else if ((isA && status[0]) || (isB && status[1])) {
        completed.push(tradeId);
      }
    });

    let html = "";

    if (eligible.length > 0) {
      html += `<h3>🟢 투표할 계약 (${eligible.length})</h3><ul>`;
      for (let tradeId of eligible) {
        html += `<li style="cursor:pointer;" onclick="showVoteSection('${tradeId}')">📄 ${tradeId}</li>`;
      }
      html += `</ul>`;
    } else {
      html += "✅ 현재 투표 가능한 계약이 없습니다.";
    }

    if (completed.length > 0) {
      html += `<h3 style="margin-top: 20px;">🗂️ 이미 투표 완료한 계약 (${completed.length})</h3><ul>`;
      for (let tradeId of completed) {
        html += `<li style="cursor:pointer; color:gray;" onclick="showVoteSection('${tradeId}')">📁 ${tradeId}</li>`;
      }
      html += `</ul>`;
    }

    container.innerHTML = html;

  } catch (err) {
    console.error("❌ 투표 목록 로딩 실패:", err);
    container.innerHTML = "🚨 계약 정보를 불러오는 중 오류가 발생했습니다.";
  }
}

// ✅ 투표 상세 정보 표시
async function showVoteSection(tradeId) {
  const voteSection = document.getElementById("voteSection");
  const selectedTradeId = document.getElementById("selectedTradeId");
  selectedTradeId.textContent = tradeId;

  try {
    const res = await fetch(`/api/contract?trade_id=${encodeURIComponent(tradeId)}`, {
      credentials: "include"
    });
    if (!res.ok) throw new Error("계약 정보 조회 실패");
    const contractData = await res.json();

    const voterInfo = await contract.methods.getVoters(tradeId).call();
    const partyA = voterInfo[0];
    const partyB = voterInfo[1];

    const voteStatusRaw = await contract.methods.getVoteStatus(tradeId).call();
    const votedA = voteStatusRaw[0];
    const votedB = voteStatusRaw[1];
    const approvedA = voteStatusRaw[2];
    const approvedB = voteStatusRaw[3];
    const finalized = voteStatusRaw[4];
    const normalized = [partyA, partyB].map(a => a.toLowerCase());

    let html = `<div class="contract-info">`;
    html += `<h2>📄 선택한 계약: <span style="color:#5a32e8;">${tradeId}</span></h2>`;

    if (finalized) {
    // ✅ 최종 승인된 계약: 요약 정보만
    html += `
        <p><strong>🔗 Hash:</strong> ${contractData.contractHash}</p>
        <p><strong>등록일:</strong> ${contractData.datetime}</p>
        <p class="status-message">✅ 이 계약은 이미 <strong>최종 처리</strong>되었습니다.</p>
        <p>🗳️ <strong>A의 투표:</strong> ${approvedA ? "✔ 승인" : "❌ 거절"}</p>
        <p>🗳️ <strong>B의 투표:</strong> ${approvedB ? "✔ 승인" : "❌ 거절"}</p>
    `;
    } else {
    // ✅ 진행 중인 계약: 전체 정보 표시
    html += `
        <p><strong>🔗 Hash:</strong> ${contractData.contractHash}</p>
        <p><strong>🏷 Asset ID:</strong> ${contractData.assetId}</p>
        <p><strong>👤 등록자:</strong> ${contractData.registrant}</p>
        <p><strong>👥 당사자 A:</strong> ${contractData.partyA}</p>
        <p><strong>👥 당사자 B:</strong> ${contractData.partyB}</p>
        <p><strong>🕒 등록일:</strong> ${contractData.datetime}</p>
    `;

    if (contractData.fileMoved !== true) {
        html += `
        <p><strong>📄 계약서 미리보기:</strong></p>
        <iframe src="/api/contract/view?trade_id=${encodeURIComponent(tradeId)}"
                width="100%" height="400px"
                style="border:1px solid #ccc; border-radius:5px; margin-top:10px;"></iframe>
        `;
    } else {
        html += `<p class="status-message">⚠️ 계약서 원본은 더 이상 조회할 수 없습니다 (보관 처리됨).</p>`;
    }

    html += `<hr>`;
    html += `
        <p>🗳️ <strong>A (${partyA.slice(0, 6)}...${partyA.slice(-4)}):</strong> 
            ${votedA ? (approvedA ? "✔ 승인" : "❌ 거절") : "⏳ 미투표"}
        </p>
        <p>🗳️ <strong>B (${partyB.slice(0, 6)}...${partyB.slice(-4)}):</strong> 
            ${votedB ? (approvedB ? "✔ 승인" : "❌ 거절") : "⏳ 미투표"}
        </p>
        `;
    // ✅ 투표 상태에 따른 메시지
    if (normalized.includes(userAddress)) {
        const isA = userAddress === partyA.toLowerCase();
        const alreadyVoted = isA ? votedA : votedB;
        const approved = isA ? approvedA : approvedB;

        if (alreadyVoted) {
        html += `<p class="status-message">🎯 당신은 이미 <strong>${approved ? "승인" : "거절"}</strong> 투표를 완료했습니다.</p>`;
        } else {
        html += `
            <div class="vote-buttons">
            <button class="approve" onclick="submitVote('${tradeId}', true)">✅ 승인</button>
            <button class="reject" onclick="submitVote('${tradeId}', false)">❌ 거절</button>
            </div>
        `;
        }
    } else {
        html += `<p class="status-message">⚠️ 이 계약에 대한 투표 권한이 없습니다.</p>`;
    }
    }

    html += `</div>`;
    voteSection.innerHTML = html;


  } catch (err) {
    console.error("❌ 계약 정보 또는 getVoters 실패:", err);
    voteSection.innerHTML = "❌ 계약 정보 또는 투표자 정보를 확인할 수 없습니다.";
  }
}
// ✅ 투표 전송
async function submitVote(tradeId, approval) {
  try {
    const accounts = await ethereum.request({ method: "eth_requestAccounts" });
    await contract.methods.voteOnContract(tradeId, approval).send({
      from: accounts[0]
    });

    document.getElementById("voteSection").innerHTML = "🎉 투표가 완료되었습니다. 감사합니다.";
    await loadEligibleVotes(); // ✅ 목록 갱신
  } catch (err) {
    console.error("❌ 투표 실패:", err);
    alert("투표 처리 중 오류가 발생했습니다.");
  }
}
