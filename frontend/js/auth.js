async function loginWithMetaMask() {
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  const address = accounts[0];
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address })
  });
  if (res.ok) {
    const data = await res.json();
    localStorage.setItem("token", data.token);
    window.location.href = "/static/register.html";
  } else {
    alert("로그인 실패");
  }
}

async function loginAndGetJWT() {
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  const address = accounts[0];
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address })
  });
  if (res.ok) {
    const data = await res.json();
    localStorage.setItem("token", data.token);
    return true;
  }
  return false;
}
