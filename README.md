
# 📦 블록체인 계약 등록 시스템

## 📌 전체 시스템 구성

### 1. 🔐 프론트엔드 (HTML + JS + Web3.js)
- **MetaMask 지갑 연결 및 로그인**
  - 서명 인증 후 JWT 발급 → `HttpOnly` 쿠키로 저장
- **계약 등록**
  - PDF 파일을 업로드
  - 자사 ID 입력
  - 파일 해시(SHA256) 생성 및 서버에 전송
- **결과 표시**
  - 등록 완료 후 `Trade ID`, `Tx Hash`, `SHA256` 결과 출력
- **계약 조회**
  - `Trade ID + Tx Hash` 조합으로 서버에서 스마트컨트랙트 질의

### 2. 📄 스마트컨트랙트 (Solidity)
- `registerContract(tradeId, sha256, assetId)` 함수로 등록
- `getContract(tradeId, txHash)` 함수로 조회
- `mapping(tradeId => ...)` 구조로 데이터 저장

### 3. 🌐 이더리움 네트워크 (Sepolia 테스트넷)
- MetaMask를 통해 서명 및 트랜잭션 처리
- 트랜잭션 해시 및 스마트컨트랙트 주소는 Etherscan에서 검증 가능

### 4. 🧠 백엔드 서버 (FastAPI)
- **인증**
  - JWT 기반 로그인 (`HttpOnly` 쿠키 사용)
  - 토큰 만료: 30분
- **파일 업로드 및 계약 등록**
  - PDF 파일만 허용 (`.pdf`, `Content-Type`, 시그니처 `%PDF` 확인)
  - 업로드 용량 제한: 10MB
  - 등록 시 해시 생성 + Trade ID 자동 생성 + 스마트컨트랙트 호출
- **조회 API**
  - `/contract?trade_id=...&tx_hash=...` 요청으로 계약 내용 반환
- **보안**
  - CORS 허용 제한 (현재는 개발용으로 `*` 허용)
  - CSRF 우회를 방지하기 위한 `SameSite=Lax`, `HttpOnly` 쿠키 설정
  - 인증 없이 업로드 불가 (JWT 검증 필수)

---

## ✅ 실행 방법

### 1. 환경 변수 설정
`.env` 파일에 다음 항목을 설정하세요:

```env
JWT_SECRET_KEY=your_secret_key
```

### 2. 백엔드 실행
```bash
uvicorn backend.main:app --reload
```

### 3. 프론트엔드 접근
- 브라우저에서 `http://localhost:8000/static/index.html` 접속
- 로그인 → 계약 등록 / 조회

---

## 🔒 보안 체크리스트

- [x] JWT를 `HttpOnly` 쿠키로 설정
- [x] 파일 확장자 및 MIME 타입 검사
- [x] PDF 시그니처(`%PDF`) 확인
- [x] 업로드 용량 제한
- [x] 토큰 만료 시 자동 로그아웃 처리
- [x] 미로그인 시 업로드 불가

---

## 🛠 향후 개선 방향

- [ ] 프론트엔드 라우팅 개선 (SPA 방식 적용)
- [ ] 관리자 페이지 및 트랜잭션 로그 대시보드
- [ ] IPFS 기반 계약서 저장 기능 연동
- [ ] 로컬 DB 연동을 통한 캐시 및 검색 최적화
