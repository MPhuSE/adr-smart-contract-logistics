// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./SLAContract.sol";
import "./EvidenceVault.sol";
import "./DisputeRegistry.sol";

contract DisputeResolution is Pausable, ReentrancyGuard, Ownable {
    SLAContract public slaContract;
    EvidenceVault public evidenceVault;
    DisputeRegistry public registry;

    enum State {
        Created,
        Disputed,
        Tier1Resolved,
        Tier2Commit,
        Tier2Reveal,
        Tier2Resolved,
        Tier3Commit,
        Tier3Reveal,
        Tier3Resolved,
        Enforced,
        Cancelled
    }

    enum Ruling {
        None,
        BuyerWins,
        SellerWins
    }

    struct Dispute {
        uint256 id;
        uint256 slaId;
        uint256 clauseId;
        State state;
        Ruling finalRuling;
        uint256 deadline;
        
        address[] tier2Jury;
        mapping(address => bytes32) tier2Commits;
        mapping(address => Ruling) tier2Reveals;
        mapping(address => bool) tier2HasRevealed;
        
        address[] tier3Panel;
        mapping(address => bytes32) tier3Commits;
        mapping(address => Ruling) tier3Reveals;
        mapping(address => bool) tier3HasRevealed;

        uint256 appealBond;
        address appellant;
    }

    uint256 public disputeCounter;
    mapping(uint256 => Dispute) public disputes;

    uint256 public constant COMMIT_WINDOW = 1 days;
    uint256 public constant REVEAL_WINDOW = 1 days;
    uint256 public constant SLASH_AMOUNT = 0.1 ether;
    uint256 public constant APPEAL_BOND = 0.5 ether;

    event DisputeCreated(uint256 indexed disputeId, uint256 slaId, uint256 clauseId);
    event Tier1Resolved(uint256 indexed disputeId, Ruling ruling);
    event EscalatedToTier2(uint256 indexed disputeId);
    event VoteCommitted(uint256 indexed disputeId, address indexed arbitrator);
    event VoteRevealed(uint256 indexed disputeId, address indexed arbitrator, Ruling ruling);
    event Tier2Resolved(uint256 indexed disputeId, Ruling ruling);
    event AppealedToTier3(uint256 indexed disputeId, address indexed appellant);
    event Tier3Resolved(uint256 indexed disputeId, Ruling ruling);
    event Enforced(uint256 indexed disputeId, Ruling ruling);

    constructor(
        address _slaContract,
        address _evidenceVault,
        address _registry
    ) Ownable(msg.sender) {
        slaContract = SLAContract(_slaContract);
        evidenceVault = EvidenceVault(_evidenceVault);
        registry = DisputeRegistry(_registry);
    }

    function _assignJury(uint256 _disputeId, uint256 _count, bool _isTier3) internal {
        Dispute storage d = disputes[_disputeId];
        address[] memory assignees;
        if (_isTier3) {
            assignees = registry.selectExpertPanel(_disputeId, _count);
            d.tier3Panel = assignees;
        } else {
            assignees = registry.selectJury(_disputeId, _count);
            d.tier2Jury = assignees;
        }
        for (uint256 i = 0; i < assignees.length; i++) {
            registry.lockArbitrator(assignees[i]);
        }
    }

    function createDispute(uint256 _slaId, uint256 _clauseId, string calldata _initialEvidenceCID) external whenNotPaused returns (uint256) {
        uint256 dId = ++disputeCounter;
        Dispute storage d = disputes[dId];
        d.id = dId;
        d.slaId = _slaId;
        d.clauseId = _clauseId;
        d.state = State.Disputed;
        
        if (bytes(_initialEvidenceCID).length > 0) {
            evidenceVault.submitEvidence(dId, _initialEvidenceCID, keccak256(abi.encodePacked(_initialEvidenceCID)));
        }

        emit DisputeCreated(dId, _slaId, _clauseId);
        return dId;
    }

    function resolveTier1(uint256 _disputeId) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Disputed, "Invalid state");

        (SLAContract.DisputeType dType, , , ) = slaContract.getClause(d.slaId, d.clauseId);

        if (dType == SLAContract.DisputeType.Damage || dType == SLAContract.DisputeType.DeliveryDenial) {
            revert("Cannot auto-resolve subjective disputes");
        }

        (SLAContract.EvalStatus status, ) = slaContract.evaluateClause(d.slaId, d.clauseId);
        // A clause with no oracle measurement is not auto-resolvable; it must be
        // escalated rather than silently treated as "no breach".
        require(status != SLAContract.EvalStatus.NotEvaluable, "Clause not measured");
        bool isBreach = status == SLAContract.EvalStatus.Breach;

        Ruling ruling = Ruling.None;
        if (dType == SLAContract.DisputeType.PaymentDelay) {
            ruling = isBreach ? Ruling.SellerWins : Ruling.BuyerWins;
        } else {
            // LateDelivery, Shortage
            ruling = isBreach ? Ruling.BuyerWins : Ruling.SellerWins;
        }

        d.state = State.Tier1Resolved;
        d.finalRuling = ruling;
        emit Tier1Resolved(_disputeId, ruling);
    }

    function escalateToTier2(uint256 _disputeId) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Disputed || d.state == State.Tier1Resolved, "Invalid state");
        
        d.state = State.Tier2Commit;
        d.deadline = block.timestamp + COMMIT_WINDOW;
        _assignJury(_disputeId, 3, false);
        
        emit EscalatedToTier2(_disputeId);
    }

    function isJuryMember(uint256 _disputeId, address _voter, bool _isTier3) public view returns (bool) {
        Dispute storage d = disputes[_disputeId];
        address[] memory members = _isTier3 ? d.tier3Panel : d.tier2Jury;
        for (uint i = 0; i < members.length; i++) {
            if (members[i] == _voter) return true;
        }
        return false;
    }

    function commitVote(uint256 _disputeId, bytes32 _commitHash) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Tier2Commit || d.state == State.Tier3Commit, "Not in commit phase");
        require(block.timestamp <= d.deadline, "Commit window closed");
        
        bool isTier3 = d.state == State.Tier3Commit;
        require(isJuryMember(_disputeId, msg.sender, isTier3), "Not a jury member");

        if (isTier3) {
            require(d.tier3Commits[msg.sender] == bytes32(0), "Already committed");
            d.tier3Commits[msg.sender] = _commitHash;
        } else {
            require(d.tier2Commits[msg.sender] == bytes32(0), "Already committed");
            d.tier2Commits[msg.sender] = _commitHash;
        }

        emit VoteCommitted(_disputeId, msg.sender);
    }

    function transitionToReveal(uint256 _disputeId) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Tier2Commit || d.state == State.Tier3Commit, "Invalid state");
        require(block.timestamp > d.deadline, "Commit window active");
        
        if (d.state == State.Tier2Commit) {
            d.state = State.Tier2Reveal;
        } else {
            d.state = State.Tier3Reveal;
        }
        d.deadline = block.timestamp + REVEAL_WINDOW;
    }

    function revealVote(uint256 _disputeId, Ruling _vote, bytes32 _salt) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Tier2Reveal || d.state == State.Tier3Reveal, "Not in reveal phase");
        require(block.timestamp <= d.deadline, "Reveal window closed");
        
        bool isTier3 = d.state == State.Tier3Reveal;
        require(isJuryMember(_disputeId, msg.sender, isTier3), "Not a jury member");
        
        bytes32 expectedHash = keccak256(abi.encodePacked(uint8(_vote), _salt));

        if (isTier3) {
            require(!d.tier3HasRevealed[msg.sender], "Already revealed");
            require(d.tier3Commits[msg.sender] == expectedHash, "Invalid reveal");
            d.tier3Reveals[msg.sender] = _vote;
            d.tier3HasRevealed[msg.sender] = true;
        } else {
            require(!d.tier2HasRevealed[msg.sender], "Already revealed");
            require(d.tier2Commits[msg.sender] == expectedHash, "Invalid reveal");
            d.tier2Reveals[msg.sender] = _vote;
            d.tier2HasRevealed[msg.sender] = true;
        }

        emit VoteRevealed(_disputeId, msg.sender, _vote);
    }

    function finalizeVote(uint256 _disputeId) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Tier2Reveal || d.state == State.Tier3Reveal, "Not in reveal phase");
        require(block.timestamp > d.deadline, "Reveal window active");

        bool isTier3 = d.state == State.Tier3Reveal;
        address[] memory members = isTier3 ? d.tier3Panel : d.tier2Jury;
        
        uint256 buyerVotes = 0;
        uint256 sellerVotes = 0;
        
        for (uint i = 0; i < members.length; i++) {
            address m = members[i];
            bool hasRevealed = isTier3 ? d.tier3HasRevealed[m] : d.tier2HasRevealed[m];
            if (!hasRevealed) {
                registry.slash(m, SLASH_AMOUNT);
                registry.releaseArbitrator(m);
                continue;
            }
            Ruling r = isTier3 ? d.tier3Reveals[m] : d.tier2Reveals[m];
            if (r == Ruling.BuyerWins) buyerVotes++;
            else if (r == Ruling.SellerWins) sellerVotes++;
        }

        Ruling finalRuling = buyerVotes > sellerVotes ? Ruling.BuyerWins : (sellerVotes > buyerVotes ? Ruling.SellerWins : Ruling.None);
        
        // Reward voters coherent with the majority and release every revealed
        // voter. Good-faith minority voters are deliberately NOT slashed: with a
        // 3-member jury, slashing the minority creates a herding incentive to
        // vote with the expected majority rather than honestly, which defeats
        // the purpose of commit-reveal. Only non-revelation (a liveness fault,
        // slashed in the loop above) is penalised.
        for (uint i = 0; i < members.length; i++) {
            address m = members[i];
            bool hasRevealed = isTier3 ? d.tier3HasRevealed[m] : d.tier2HasRevealed[m];
            if (hasRevealed) {
                Ruling r = isTier3 ? d.tier3Reveals[m] : d.tier2Reveals[m];
                if (r == finalRuling) {
                    registry.reward(m, 0);
                }
                registry.releaseArbitrator(m);
            }
        }

        if (isTier3) {
            d.state = State.Tier3Resolved;
            d.finalRuling = finalRuling;
            emit Tier3Resolved(_disputeId, finalRuling);
        } else {
            d.state = State.Tier2Resolved;
            d.finalRuling = finalRuling;
            emit Tier2Resolved(_disputeId, finalRuling);
        }
    }

    function appealToTier3(uint256 _disputeId) external payable whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.state == State.Tier2Resolved, "Not resolved in Tier 2");
        require(msg.value == APPEAL_BOND, "Incorrect bond");
        
        d.state = State.Tier3Commit;
        d.deadline = block.timestamp + COMMIT_WINDOW;
        d.appealBond = msg.value;
        d.appellant = msg.sender;

        _assignJury(_disputeId, 5, true);
        
        emit AppealedToTier3(_disputeId, msg.sender);
    }

    function enforce(uint256 _disputeId) external nonReentrant whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(
            d.state == State.Tier1Resolved || 
            d.state == State.Tier2Resolved || 
            d.state == State.Tier3Resolved, 
            "Not resolved"
        );
        
        d.state = State.Enforced;
        emit Enforced(_disputeId, d.finalRuling);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function getTier2Jury(uint256 _disputeId) external view returns (address[] memory) {
        return disputes[_disputeId].tier2Jury;
    }

    function getTier3Panel(uint256 _disputeId) external view returns (address[] memory) {
        return disputes[_disputeId].tier3Panel;
    }
}
