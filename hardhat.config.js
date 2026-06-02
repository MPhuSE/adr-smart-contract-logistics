require("@nomicfoundation/hardhat-toolbox");
require("hardhat-gas-reporter");

module.exports = {
  solidity: "0.8.28",
  gasReporter: {
    enabled: true,
    currency: "USD",
    showTimeSpent: true,
  },
};