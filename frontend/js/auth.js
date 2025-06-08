let currentNonce = null;

async function loginWithMetaMask() {
  const resultBox = document.getElementById("loginResult");
  resultBox.style.display = "none";

  try {
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
      body: JSON.stringify({ address, signature })
    });

    if (verifyRes.ok) {
      window.location.href = "/static/main.html";
    } else {
      const err = await verifyRes.json();
      throw new Error(err.detail || "서명 검증 실패");
    }

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

  // 🔁 계정 변경 감지
  if (window.ethereum) {
    window.ethereum.on("accountsChanged", (accounts) => {
      console.log("🔄 계정 변경됨:", accounts);
      localStorage.removeItem("token");
      currentNonce = null;
      alert("계정이 변경되었습니다. 다시 로그인 해주세요.");
      window.location.href = "/static/index.html";
    });
  }
});


async function loginAndGetJWT() {
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  const address = accounts[0];

  const nonceRes = await fetch(`/auth/nonce?address=${address}`, {
    credentials: "include"  // ✅ 필수!
  });
  if (!nonceRes.ok) return false;

  const { nonce } = await nonceRes.json();

  const signature = await window.ethereum.request({
    method: 'personal_sign',
    params: [nonce, address]
  });

  const verifyRes = await fetch('/auth/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: "include",  // ✅ 필수!
    body: JSON.stringify({ address, signature })
  });

  if (verifyRes.ok) {
    return true;
  }
  return false;
}
