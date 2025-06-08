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
checkLoginStatus(); // 페이지 로드 시 로그인 확인

// ✅ 로그아웃 처리
async function logout() {
  await fetch("/auth/logout", {
    method: "POST",
    credentials: "include"
  });
  alert("로그아웃되었습니다.");
  window.location.href = "/static/index.html";
}

// 📤 계약서 등록
const uploadForm = document.getElementById("uploadForm");
const registerResult = document.getElementById("registerResult");

if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById("file");
    const assetIdInput = document.getElementById("asset_id");
    const partyBInput = document.getElementById("party_b");

    if (!fileInput.files.length || !assetIdInput.value || !partyBInput.value) {
      alert("모든 항목을 입력해주세요.");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("asset_id", assetIdInput.value);
    formData.append("party_b", partyBInput.value);

    try {
      const res = await fetch("/api/register", {
        method: "POST",
        body: formData,
        credentials: "include"
      });

      if (res.status === 401) {
        alert("세션이 만료되었습니다. 다시 로그인 해주세요.");
        window.location.href = "/static/index.html";
        return;
      }

      if (!res.ok) {
        const errText = await res.text();
        console.error("❌ 등록 실패:", errText);
        registerResult.innerHTML = `❌ 등록 실패: ${errText}`;
        registerResult.style.color = "red";
        registerResult.style.display = "block";
        return;
      }

      const data = await res.json();
      registerResult.innerHTML = `
        ✅ 등록 완료:<br>
        📌 Trade ID: ${data.trade_id}<br>
        🔗 Tx Hash: <a href="https://sepolia.etherscan.io/tx/${data.tx_hash}" target="_blank">${data.tx_hash}</a><br>
        🔒 SHA256: ${data.sha256}`;
      registerResult.style.color = "black";
      registerResult.style.display = "block";
    } catch (err) {
      console.error("❌ 네트워크 오류:", err);
      registerResult.innerHTML = `❌ 네트워크 오류 또는 서버 문제 발생`;
      registerResult.style.color = "red";
      registerResult.style.display = "block";
    }
  });
}
