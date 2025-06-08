// ✅ 로그인 확인 (쿠키 기반)
async function checkLoginStatus() {
  try {
    const res = await fetch("/auth/me", { credentials: "include" });
    if (res.status === 401) {
      alert("로그인이 필요합니다.");
      window.location.href = "/static/index.html";
    }
  } catch (err) {
    console.error("세션 확인 오류:", err);
    alert("네트워크 오류로 로그인 상태를 확인할 수 없습니다.");
    window.location.href = "/static/index.html";
  }
}

checkLoginStatus(); // 페이지 로드 시 실행

// ✅ 로그아웃 처리
async function logout() {
  await fetch("/auth/logout", {
    method: "POST",
    credentials: "include"
  });
  alert("로그아웃되었습니다.");
  window.location.href = "/static/index.html";
}

// ✅ 계약 조회 처리
document.addEventListener("DOMContentLoaded", () => {
  const lookupForm = document.getElementById("lookupForm");
  const lookupResult = document.getElementById("lookupResult");

  if (!lookupForm) return;

  lookupForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const tradeId = document.getElementById("lookup_trade_id").value.trim();
    const txHash = document.getElementById("lookup_tx_hash").value.trim();

    if (!tradeId || !txHash) {
      alert("Trade ID와 Tx Hash를 모두 입력해주세요.");
      return;
    }

    try {
      const res = await fetch(`/api/contract?trade_id=${encodeURIComponent(tradeId)}&tx_hash=${encodeURIComponent(txHash)}`, {
        credentials: "include"
      });

      if (res.status === 401) {
        alert("세션이 만료되었습니다. 다시 로그인 해주세요.");
        window.location.href = "/static/index.html";
        return;
      }

      if (!res.ok) {
        lookupResult.innerHTML = `❌ 조회 실패`;
        lookupResult.style.color = "red";
        lookupResult.style.display = "block";
        return;
      }

      const data = await res.json();
      lookupResult.innerHTML = `
        📄 계약 내용:<br>
        🧾 Hash: ${data.contractHash}<br>
        🏷 Asset ID: ${data.assetId}<br>
        👤 등록자 (PartyA): ${data.partyA}<br>
        👥 상대방 (PartyB): ${data.partyB}<br>
        📅 등록일: ${data.datetime}
      `;
      lookupResult.style.color = "black";
      lookupResult.style.display = "block";
    } catch (err) {
      console.error("조회 오류:", err);
      lookupResult.innerHTML = `❌ 네트워크 오류 또는 서버 문제 발생`;
      lookupResult.style.color = "red";
      lookupResult.style.display = "block";
    }
  });

  // 🔽 내 완료 계약 버튼 처리
  const finalizedBtn = document.getElementById("myFinalizedBtn");
  const finalizedContainer = document.getElementById("myFinalizedContracts");

  if (finalizedBtn && finalizedContainer) {
    finalizedBtn.addEventListener("click", async () => {
      finalizedContainer.innerHTML = "⏳ 불러오는 중...";
      try {
        const res = await fetch("/api/finalized-contracts", {
          credentials: "include"
        });

        if (!res.ok) {
          finalizedContainer.innerHTML = "❌ 계약 목록을 불러오지 못했습니다.";
          return;
        }

        const data = await res.json();
        const contracts = data.finalized_contracts;

        if (contracts.length === 0) {
          finalizedContainer.innerHTML = "✅ 완료된 계약이 없습니다.";
          return;
        }

        let html = "<h3>📁 완료된 계약 목록</h3>";
        for (const c of contracts) {
          html += `
            <div class="finalized-card" style="border:1px solid #ccc; padding:10px; margin:10px 0;">
                <p><strong>📄 Trade ID:</strong> ${c.trade_id}</p>
                <p><strong>🔗 Hash:</strong> ${c.contractHash}</p>
                <p><strong>📅 등록일:</strong> ${c.datetime}</p>
                <p><strong>🗳 A 투표:</strong> ${c.approvedA ? "✔ 승인" : "❌ 거절"}</p>
                <p><strong>🗳 B 투표:</strong> ${c.approvedB ? "✔ 승인" : "❌ 거절"}</p>
                <p><strong>📁 계약서:</strong> ${c.fileMoved ? "🔒 보관됨 (미리보기 불가)" : "✅ 미리보기 가능"}</p>
                <p><strong>2차 DAO 처리:</strong> ${c.daoProcessed ? "✅ 처리됨" : "❌ 미처리"}</p>
                ${
                  c.daoProcessed
                    ? `<p><strong>2차 DAO 결과:</strong> ${c.daoPassed ? "✔ 통과" : "❌ 거부"}</p>`
                    : ""
                }
            </div>
          `;
        }
        finalizedContainer.innerHTML = html;
      } catch (err) {
        console.error("❌ 완료 계약 조회 실패:", err);
        finalizedContainer.innerHTML = "❌ 네트워크 오류 또는 세션 만료";
      }
    });
  }
});
