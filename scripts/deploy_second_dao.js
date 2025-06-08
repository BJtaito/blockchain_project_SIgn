const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const SecondDAO = await hre.ethers.getContractFactory("SecondDAO");

  // 초기 허용 멤버 배열, 실제 주소로 변경 필요
  const initialVoters = [
    "0x7315C7AD21E501faBFc86f3D546a8898be6D39b6",
    "0x08ae1529BeBF0eDe319A2A6bd546D1Cd3bD428BD"
  ];

  const secondDAO = await SecondDAO.deploy(initialVoters);
  await secondDAO.deployed();

  console.log("SecondDAO deployed to:", secondDAO.address);

  // .env 경로
  const envPath = path.resolve(__dirname, "../.env");

  // 기존 .env 읽기
  let envConfig = "";
  if (fs.existsSync(envPath)) {
    envConfig = fs.readFileSync(envPath, { encoding: "utf8" });
  }

  // 줄 단위로 배열화 후 DAO_CONTRACT_ADDRESS 제거
  let envLines = envConfig.split("\n");
  envLines = envLines.filter(line => !line.startsWith("DAO_CONTRACT_ADDRESS="));

  // 새 주소 추가
  envLines.push(`DAO_CONTRACT_ADDRESS=${secondDAO.address}`);

  const newEnvConfig = envLines.join("\n");
  fs.writeFileSync(envPath, newEnvConfig, { encoding: "utf8" });

  console.log(".env 파일에 DAO_CONTRACT_ADDRESS가 저장되었습니다.");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
