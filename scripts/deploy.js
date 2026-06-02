const { ethers } = require("hardhat");

async function main() {
    const SLAContract = await ethers.getContractFactory("SLAContract");
    const slaContract = await SLAContract.deploy();
    await slaContract.waitForDeployment();

    console.log("SLAContract:", await slaContract.getAddress());

    const DisputeRegistry = await ethers.getContractFactory("DisputeRegistry");
    const registry = await DisputeRegistry.deploy();
    await registry.waitForDeployment();

    console.log("DisputeRegistry:", await registry.getAddress());

    const EvidenceVault = await ethers.getContractFactory("EvidenceVault");
    const evidenceVault = await EvidenceVault.deploy();
    await evidenceVault.waitForDeployment();

    console.log("EvidenceVault:", await evidenceVault.getAddress());

    const DisputeResolution = await ethers.getContractFactory("DisputeResolution");
    const disputeResolution = await DisputeResolution.deploy(
        await slaContract.getAddress(),
        await registry.getAddress()
    );
    await disputeResolution.waitForDeployment();

    console.log("DisputeResolution:", await disputeResolution.getAddress());
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});