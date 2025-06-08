let currentNonce = null;

async function logoutIfNeeded() {
  try {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
  } catch {
    // 무시
  }
}

async function loginAdmin() {
  const resultBox = document.getElementById("adminLoginResult");
  resultBox.style.display = "none";

  try {
    await logoutIfNeeded();

    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    const address = accounts[0];

    if (!currentNonce) {
      const nonceRes = await fetch(`/auth/nonce?address=${address}`);
      if (!nonceRes.ok) throw new Error("Nonce 요청 실패");
      const { nonce } = await nonceRes.json();
      currentNonce = nonce;
    }

    const message = `Sign this message: ${currentNonce}`;
    const signature = await window.ethereum.request({
      method: "personal_sign",
      params: [message, address],
    });

    const verifyRes = await fetch("/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ address, signature }),
    });

    if (!verifyRes.ok) {
      const err = await verifyRes.json();
      throw new Error(err.detail || "서명 검증 실패");
    }

    // 관리자 권한 확인
    const adminCheckRes = await fetch("/api/admin/check-admin", { credentials: "include" });
    if (adminCheckRes.ok) {
      // 권한 있으면 관리자 페이지로 이동
      window.location.href = "/static/admin.html";
    } else {
      throw new Error("관리자 권한이 없습니다.");
    }

  } catch (err) {
    resultBox.style.display = "block";
    resultBox.style.color = "red";
    resultBox.innerText = "❌ 로그인 실패: " + err.message;
  }

  currentNonce = null;
}

window.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("adminLoginBtn");
  if (loginBtn) loginBtn.addEventListener("click", loginAdmin);

  if (window.ethereum) {
    window.ethereum.on("accountsChanged", (accounts) => {
      console.log("🔄 계정 변경됨:", accounts);
      currentNonce = null;
      alert("계정이 변경되었습니다. 다시 로그인 해주세요.");
      window.location.href = "/static/index.html";
    });
  }
});
