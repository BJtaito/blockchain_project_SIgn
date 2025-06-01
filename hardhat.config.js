require("@nomiclabs/hardhat-ethers");
require("dotenv").config();

module.exports = {
  solidity: "0.8.20",
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL,         // 수정: SEPOLIA_RPC → SEPOLIA_RPC_URL
      accounts: [process.env.PRIVATE_KEY.trim()] // 공백 제거
    }
  }
};
