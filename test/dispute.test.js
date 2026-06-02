const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Automated Dispute Resolution System", function () {
    let owner, buyer, seller, arb1, arb2, arb3, expert1;
    let slaContract, registry, disputeResolution;

    beforeEach(async function () {
        [owner, buyer, seller, arb1, arb2, arb3, expert1] = await ethers.getSigners();

        const SLAContract = await ethers.getContractFactory("SLAContract");
        slaContract = await SLAContract.deploy();

        const DisputeRegistry = await ethers.getContractFactory("DisputeRegistry");
        registry = await DisputeRegistry.deploy();

        const DisputeResolution = await ethers.getContractFactory("DisputeResolution");
        disputeResolution = await DisputeResolution.deploy(
            await slaContract.getAddress(),
            await registry.getAddress()
        );

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
    });

    it("Should create SLA", async function () {
        await slaContract.createSLA(1000, 2000, 100, 5, 10, 20, 3);

        const sla = await slaContract.slas(1);

        expect(sla.requiredQuantity).to.equal(100);
        expect(sla.latePenalty).to.equal(5);
        expect(sla.active).to.equal(true);
    });

    it("Should auto resolve late delivery dispute", async function () {
        await slaContract.createSLA(1000, 2000, 100, 5, 10, 20, 3);

        await disputeResolution.openDispute(
            1,
            buyer.address,
            seller.address,
            0,
            ethers.parseEther("1")
        );

        await disputeResolution.autoResolveLateDelivery(1, 1500);

        const dispute = await disputeResolution.disputes(1);

        expect(dispute.winner).to.equal(buyer.address);
        expect(dispute.status).to.equal(1);
    });

    it("Should auto resolve shortage dispute", async function () {
        await slaContract.createSLA(1000, 2000, 100, 5, 10, 20, 3);

        await disputeResolution.openDispute(
            1,
            buyer.address,
            seller.address,
            1,
            ethers.parseEther("1")
        );

        await disputeResolution.autoResolveShortage(1, 80);

        const dispute = await disputeResolution.disputes(1);

        expect(dispute.winner).to.equal(buyer.address);
    });

    it("Should auto resolve payment delay dispute", async function () {
        await slaContract.createSLA(1000, 2000, 100, 5, 10, 20, 3);

        await disputeResolution.openDispute(
            1,
            buyer.address,
            seller.address,
            3,
            ethers.parseEther("1")
        );

        await disputeResolution.autoResolvePaymentDelay(1, 3000);

        const dispute = await disputeResolution.disputes(1);

        expect(dispute.winner).to.equal(seller.address);
    });

    it("Should resolve damage dispute by peer voting", async function () {
        await slaContract.createSLA(1000, 2000, 100, 5, 10, 20, 3);

        await disputeResolution.openDispute(
            1,
            buyer.address,
            seller.address,
            2,
            ethers.parseEther("1")
        );

        await disputeResolution.startPeerVoting(1);

        await disputeResolution.connect(arb1).vote(1, true);
        await disputeResolution.connect(arb2).vote(1, true);
        await disputeResolution.connect(arb3).vote(1, false);

        await disputeResolution.finalizeVoting(1);

        const dispute = await disputeResolution.disputes(1);

        expect(dispute.winner).to.equal(buyer.address);
        expect(dispute.status).to.equal(4);
    });

    it("Should submit evidence", async function () {
        const EvidenceVault = await ethers.getContractFactory("EvidenceVault");
        const evidenceVault = await EvidenceVault.deploy();

        const cid = "QmTestCID123";
        const hash = ethers.keccak256(ethers.toUtf8Bytes("damaged goods image"));

        await evidenceVault.connect(buyer).submitEvidence(1, cid, hash);

        const evidence = await evidenceVault.evidences(1);

        expect(evidence.ipfsCID).to.equal(cid);
        expect(evidence.submitter).to.equal(buyer.address);
    });
});