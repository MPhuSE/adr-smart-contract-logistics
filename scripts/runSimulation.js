const { ethers } = require("hardhat");
const fs = require("fs");

const DISPUTE_TYPES = {
    LATE_DELIVERY: 0,
    SHORTAGE: 1,
    DAMAGE: 2,
    PAYMENT_DELAY: 3,
};

function winnerLabel(actualWinner, buyer, seller) {
    if (actualWinner.toLowerCase() === buyer.address.toLowerCase()) return "buyer";
    if (actualWinner.toLowerCase() === seller.address.toLowerCase()) return "seller";
    return "none";
}

async function main() {
    const [owner, buyer, seller, arb1, arb2, arb3, expert1, expert2, expert3] =
        await ethers.getSigners();

    console.log("Deploying contracts...");

    const SLAContract = await ethers.getContractFactory("SLAContract");
    const slaContract = await SLAContract.deploy();
    await slaContract.waitForDeployment();

    const DisputeRegistry = await ethers.getContractFactory("DisputeRegistry");
    const registry = await DisputeRegistry.deploy();
    await registry.waitForDeployment();

    const EvidenceVault = await ethers.getContractFactory("EvidenceVault");
    const evidenceVault = await EvidenceVault.deploy();
    await evidenceVault.waitForDeployment();

    const DisputeResolution = await ethers.getContractFactory("DisputeResolution");
    const disputeResolution = await DisputeResolution.deploy(
        await slaContract.getAddress(),
        await registry.getAddress()
    );
    await disputeResolution.waitForDeployment();

    console.log("Registering arbitrators...");

    await registry.connect(arb1).registerArbitrator(false, {
        value: ethers.parseEther("0.01"),
    });
    await registry.connect(arb2).registerArbitrator(false, {
        value: ethers.parseEther("0.01"),
    });
    await registry.connect(arb3).registerArbitrator(false, {
        value: ethers.parseEther("0.01"),
    });

    await registry.connect(expert1).registerArbitrator(true, {
        value: ethers.parseEther("0.01"),
    });
    await registry.connect(expert2).registerArbitrator(true, {
        value: ethers.parseEther("0.01"),
    });
    await registry.connect(expert3).registerArbitrator(true, {
        value: ethers.parseEther("0.01"),
    });

    console.log("Creating SLA...");

    await slaContract.createSLA(
        1000, // deliveryDeadline
        2000, // paymentDeadline
        100,  // requiredQuantity
        5,    // latePenalty
        10,   // shortagePenalty
        20,   // damagePenalty
        3     // paymentDelayPenalty
    );

    const rows = [];
    rows.push(
        "disputeId,type,tier,expectedWinner,actualWinner,correct,openGas,resolveGas,totalGas,resolutionTimeMinutes"
    );

    const totalCases = 1000;

    let correctCount = 0;
    let tier1Count = 0;
    let tier2Count = 0;
    let tier3Count = 0;

    let totalGas = 0n;

    console.log("Running simulation...");

    for (let i = 1; i <= totalCases; i++) {
        let typeName;
        let typeId;
        let tier;
        let expectedWinner;
        let resolveTx;
        let openReceipt;
        let resolveReceipt;

        // 30% late delivery
        if (i <= 300) {
            typeName = "LateDelivery";
            typeId = DISPUTE_TYPES.LATE_DELIVERY;
            tier = "Tier1";
            expectedWinner = "buyer";
            tier1Count++;

            const openTx = await disputeResolution.openDispute(
                1,
                buyer.address,
                seller.address,
                typeId,
                ethers.parseEther("1")
            );
            openReceipt = await openTx.wait();

            resolveTx = await disputeResolution.autoResolveLateDelivery(1 + i - 1, 1500);
            resolveReceipt = await resolveTx.wait();
        }

        // 30% shortage
        else if (i <= 600) {
            typeName = "Shortage";
            typeId = DISPUTE_TYPES.SHORTAGE;
            tier = "Tier1";
            expectedWinner = "buyer";
            tier1Count++;

            const openTx = await disputeResolution.openDispute(
                1,
                buyer.address,
                seller.address,
                typeId,
                ethers.parseEther("1")
            );
            openReceipt = await openTx.wait();

            resolveTx = await disputeResolution.autoResolveShortage(i, 80);
            resolveReceipt = await resolveTx.wait();
        }

        // 20% damage -> Tier2 voting
        else if (i <= 800) {
            typeName = "Damage";
            typeId = DISPUTE_TYPES.DAMAGE;
            tier = "Tier2";
            expectedWinner = "buyer";
            tier2Count++;

            const openTx = await disputeResolution.openDispute(
                1,
                buyer.address,
                seller.address,
                typeId,
                ethers.parseEther("1")
            );
            openReceipt = await openTx.wait();

            const evidenceHash = ethers.keccak256(
                ethers.toUtf8Bytes(`damage-evidence-${i}`)
            );

            await evidenceVault
                .connect(buyer)
                .submitEvidence(i, `QmDamageCID${i}`, evidenceHash);

            await disputeResolution.startPeerVoting(i);

            const vote1 = await disputeResolution.connect(arb1).vote(i, true);
            const vote2 = await disputeResolution.connect(arb2).vote(i, true);
            const vote3 = await disputeResolution.connect(arb3).vote(i, false);

            const r1 = await vote1.wait();
            const r2 = await vote2.wait();
            const r3 = await vote3.wait();

            resolveTx = await disputeResolution.finalizeVoting(i);
            resolveReceipt = await resolveTx.wait();

            resolveReceipt.gasUsed =
                resolveReceipt.gasUsed + r1.gasUsed + r2.gasUsed + r3.gasUsed;
        }

        // 20% payment delay
        else {
            typeName = "PaymentDelay";
            typeId = DISPUTE_TYPES.PAYMENT_DELAY;
            tier = "Tier1";
            expectedWinner = "seller";
            tier1Count++;

            const openTx = await disputeResolution.openDispute(
                1,
                buyer.address,
                seller.address,
                typeId,
                ethers.parseEther("1")
            );
            openReceipt = await openTx.wait();

            resolveTx = await disputeResolution.autoResolvePaymentDelay(i, 3000);
            resolveReceipt = await resolveTx.wait();
        }

        const dispute = await disputeResolution.disputes(i);

        const actualWinner = winnerLabel(dispute.winner, buyer, seller);
        const correct = actualWinner === expectedWinner;

        if (correct) correctCount++;

        const openGas = openReceipt.gasUsed;
        const resolveGas = resolveReceipt.gasUsed;
        const caseGas = openGas + resolveGas;

        totalGas += caseGas;

        // giả lập thời gian xử lý để đưa vào bảng nghiên cứu
        let resolutionTimeMinutes = 0;

        if (tier === "Tier1") resolutionTimeMinutes = 5;
        if (tier === "Tier2") resolutionTimeMinutes = 12;
        if (tier === "Tier3") resolutionTimeMinutes = 18;

        rows.push(
            [
                i,
                typeName,
                tier,
                expectedWinner,
                actualWinner,
                correct,
                openGas.toString(),
                resolveGas.toString(),
                caseGas.toString(),
                resolutionTimeMinutes,
            ].join(",")
        );
    }

    fs.writeFileSync("results.csv", rows.join("\n"));

    const avgGas = totalGas / BigInt(totalCases);
    const correctness = (correctCount / totalCases) * 100;

    console.log("Simulation completed.");
    console.log("Total cases:", totalCases);
    console.log("Correct cases:", correctCount);
    console.log("Correctness:", correctness.toFixed(2) + "%");
    console.log("Tier1 cases:", tier1Count);
    console.log("Tier2 cases:", tier2Count);
    console.log("Tier3 cases:", tier3Count);
    console.log("Average gas:", avgGas.toString());
    console.log("CSV exported: results.csv");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});