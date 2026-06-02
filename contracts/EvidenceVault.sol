// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract EvidenceVault {
    struct Evidence {
        uint256 disputeId;
        address submitter;
        string ipfsCID;
        bytes32 evidenceHash;
        uint256 timestamp;
    }

    uint256 public evidenceCounter;
    mapping(uint256 => Evidence) public evidences;
    mapping(uint256 => uint256[]) public disputeEvidences;

    event EvidenceSubmitted(
        uint256 indexed evidenceId,
        uint256 indexed disputeId,
        address indexed submitter,
        string ipfsCID
    );

    function submitEvidence(
        uint256 _disputeId,
        string memory _ipfsCID,
        bytes32 _evidenceHash
    ) external returns (uint256) {
        evidenceCounter++;

        evidences[evidenceCounter] = Evidence({
            disputeId: _disputeId,
            submitter: msg.sender,
            ipfsCID: _ipfsCID,
            evidenceHash: _evidenceHash,
            timestamp: block.timestamp
        });

        disputeEvidences[_disputeId].push(evidenceCounter);

        emit EvidenceSubmitted(evidenceCounter, _disputeId, msg.sender, _ipfsCID);
        return evidenceCounter;
    }

    function getEvidenceIds(uint256 _disputeId) external view returns (uint256[] memory) {
        return disputeEvidences[_disputeId];
    }
}