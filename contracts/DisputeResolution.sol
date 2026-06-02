// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./SLAContract.sol";
import "./DisputeRegistry.sol";

contract DisputeResolution {
    enum Status { Open, Resolved, VotingActive, VotingEnded, Finalized }

    struct Dispute {
        uint256 slaId;
        address buyer;
        address seller;
        uint256 reason;
        uint256 amount;
        address winner;
        Status status;
        uint256 votesForBuyer;
        uint256 votesForSeller;
    }

    uint256 public disputeCounter;
    mapping(uint256 => Dispute) public disputes;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    SLAContract public slaContract;
    DisputeRegistry public registry;

    constructor(address _slaContract, address _registry) {
        slaContract = SLAContract(_slaContract);
        registry = DisputeRegistry(_registry);
    }

    function openDispute(
        uint256 _slaId,
        address _buyer,
        address _seller,
        uint256 _reason,
        uint256 _amount
    ) external returns (uint256) {
        disputeCounter++;
        disputes[disputeCounter] = Dispute({
            slaId: _slaId,
            buyer: _buyer,
            seller: _seller,
            reason: _reason,
            amount: _amount,
            winner: address(0),
            status: Status.Open,
            votesForBuyer: 0,
            votesForSeller: 0
        });
        return disputeCounter;
    }

    function autoResolveLateDelivery(uint256 _disputeId, uint256 _deliveryTime) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.reason == 0, "Not late delivery");
        require(dispute.status == Status.Open, "Not open");

        bool isLate = slaContract.checkLateDelivery(dispute.slaId, _deliveryTime);
        if (isLate) {
            dispute.winner = dispute.buyer;
        } else {
            dispute.winner = dispute.seller;
        }
        dispute.status = Status.Resolved;
    }

    function autoResolveShortage(uint256 _disputeId, uint256 _deliveredQuantity) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.reason == 1, "Not shortage");
        require(dispute.status == Status.Open, "Not open");

        bool isShortage = slaContract.checkShortage(dispute.slaId, _deliveredQuantity);
        if (isShortage) {
            dispute.winner = dispute.buyer;
        } else {
            dispute.winner = dispute.seller;
        }
        dispute.status = Status.Resolved;
    }

    function autoResolvePaymentDelay(uint256 _disputeId, uint256 _paymentTime) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.reason == 3, "Not payment delay");
        require(dispute.status == Status.Open, "Not open");

        bool isDelay = slaContract.checkPaymentDelay(dispute.slaId, _paymentTime);
        if (isDelay) {
            dispute.winner = dispute.seller;
        } else {
            dispute.winner = dispute.buyer;
        }
        dispute.status = Status.Resolved;
    }

    function startPeerVoting(uint256 _disputeId) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == Status.Open, "Not open");
        dispute.status = Status.VotingActive;
    }

    function vote(uint256 _disputeId, bool _supportBuyer) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == Status.VotingActive, "Voting not active");
        require(registry.isArbitrator(msg.sender), "Not an arbitrator");
        require(!hasVoted[_disputeId][msg.sender], "Already voted");

        hasVoted[_disputeId][msg.sender] = true;

        if (_supportBuyer) {
            dispute.votesForBuyer++;
        } else {
            dispute.votesForSeller++;
        }
    }

    function finalizeVoting(uint256 _disputeId) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == Status.VotingActive, "Voting not active");
        
        if (dispute.votesForBuyer > dispute.votesForSeller) {
            dispute.winner = dispute.buyer;
        } else {
            dispute.winner = dispute.seller;
        }
        
        dispute.status = Status.Finalized;
    }
}