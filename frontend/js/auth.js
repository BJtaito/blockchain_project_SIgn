let currentNonce = null;

async function logoutIfNeeded() {
  try {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
  } catch {
    // 무시, 실패해도 로그인 진행
  }
}

async function loginWithMetaMask() {
  const resultBox = document.getElementById("loginResult");
  resultBox.style.display = "none";

  try {
    await logoutIfNeeded();

    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const address = accounts[0];

    if (!currentNonce) {
      const nonceRes = await fetch(`/auth/nonce?address=${address}`);
      if (!nonceRes.ok) throw new Error("Nonce 요청 실패");
      const { nonce } = await nonceRes.json();
      currentNonce = nonce;
    }

    const message = `Sign this message: ${currentNonce}`;
    const signature = await window.ethereum.request({
      method: 'personal_sign',
      params: [message, address]
    });

    const verifyRes = await fetch('/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: "include",
      body: JSON.stringify({ address, signature })
    });

    if (!verifyRes.ok) {
      const err = await verifyRes.json();
      throw new Error(err.detail || "서명 검증 실패");
    }

    // 일반 로그인은 권한 확인 없이 바로 메인 페이지로 이동
    window.location.href = "/static/main.html";

  } catch (err) {
    resultBox.style.display = "block";
    resultBox.style.color = "red";
    resultBox.innerText = "❌ 로그인 실패: " + err.message;
  }

  currentNonce = null;
}

window.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("loginBtn");
  if (loginBtn) loginBtn.addEventListener("click", loginWithMetaMask);

  if (window.ethereum) {
    window.ethereum.on("accountsChanged", (accounts) => {
      console.log("🔄 계정 변경됨:", accounts);
      currentNonce = null;
      alert("계정이 변경되었습니다. 다시 로그인 해주세요.");
      window.location.href = "/static/index.html";
    });
  }
});