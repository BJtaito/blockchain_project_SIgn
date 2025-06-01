// JWT 확인 (없으면 로그인 페이지로 이동)
const token = localStorage.getItem("token");
if (!token) {
  alert("로그인이 필요합니다.");
  window.location.href = "/static/index.html";
}
async function logout() {
  await fetch("/auth/logout", {
    method: "POST",
    credentials: "include"
  });
  alert("로그아웃되었습니다.");
  window.location.href = "/static/index.html";
}
// 등록 처리
const uploadForm = document.getElementById("uploadForm");
const registerResult = document.getElementById("registerResult");

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("file", document.getElementById("file").files[0]);
  formData.append("asset_id", document.getElementById("asset_id").value);

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      body: formData,
      credentials: "include"
    });

    if (res.status === 401) {
      alert("세션이 만료되었습니다. 다시 로그인 해주세요.");
      localStorage.removeItem("token");
      window.location.href = "/static/index.html";
      return;
    }

    
    if (!res.ok) {
      registerResult.innerHTML = `❌ 등록 실패`;
      registerResult.style.color = "red";
      registerResult.style.display = "block";
      return;
    }

    const data = await res.json();
    registerResult.innerHTML = `✅ 등록 완료:<br>
      📌 Trade ID: ${data.trade_id}<br>
      🔗 Tx Hash: <a href="https://sepolia.etherscan.io/tx/${data.tx_hash}" target="_blank">${data.tx_hash}</a><br>
      🔒 SHA256: ${data.sha256}`;
    registerResult.style.color = "black";
    registerResult.style.display = "block";
  } catch (err) {
    registerResult.innerHTML = `❌ 네트워크 오류 또는 서버 문제 발생`;
    registerResult.style.color = "red";
    registerResult.style.display = "block";
  }
});

// 조회 처리
const lookupForm = document.getElementById("lookupForm");
const lookupResult = document.getElementById("lookupResult");

lookupForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const tradeId = document.getElementById("lookup_trade_id").value;
  const txHash = document.getElementById("lookup_tx_hash").value;

  try {
    const res = await fetch(`/api/contract?trade_id=${encodeURIComponent(tradeId)}&tx_hash=${encodeURIComponent(txHash)}`, {credentials: "include"});

    if (res.status === 401) {
      alert("세션이 만료되었습니다. 다시 로그인 해주세요.");
      localStorage.removeItem("token");
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
    lookupResult.innerHTML = `📄 계약 내용:<br>
      🧾 Hash: ${data.contractHash}<br>
      🏷 Asset ID: ${data.assetId}<br>
      👤 등록자: ${data.registrant}<br>
      📅 등록일: ${data.datetime}`;
    lookupResult.style.color = "black";
    lookupResult.style.display = "block";
  } catch (err) {
    lookupResult.innerHTML = `❌ 네트워크 오류 또는 서버 문제 발생`;
    lookupResult.style.color = "red";
    lookupResult.style.display = "block";
  }
});
