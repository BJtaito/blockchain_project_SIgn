const hre = require("hardhat");
const fs = require("fs");
require("dotenv").config();

async function main() {
  const ContractRegistry = await hre.ethers.getContractFactory("ContractRegistry");
  const contract = await ContractRegistry.deploy();
  await contract.deployed();

  console.log("✅ Contract deployed to:", contract.address);

  // 계약 주소를 .env에 저장
  const envPath = ".env";
  const envContent = fs.readFileSync(envPath, "utf-8");
  const updatedEnv = envContent.replace(/CONTRACT_ADDRESS=.*/g, `CONTRACT_ADDRESS=${contract.address}`);
  fs.writeFileSync(envPath, updatedEnv);
  console.log("📦 CONTRACT_ADDRESS saved to .env");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
