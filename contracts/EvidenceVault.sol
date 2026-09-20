// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceVault {
    struct Evidence {
        uint256 disputeId;
        address submitter;
        string ipfsCID;
        bytes32 evidenceHash;
        uint256 timestamp;
    }

    mapping(uint256 => Evidence[]) public disputeEvidences;
    mapping(bytes32 => bool) public isEvidenceSubmitted;

    event EvidenceSubmitted(uint256 indexed disputeId, address indexed submitter, string ipfsCID);

    function submitEvidence(uint256 _disputeId, string calldata _ipfsCID, bytes32 _evidenceHash) external {
        bytes32 uniqueHash = keccak256(abi.encodePacked(_disputeId, _ipfsCID, _evidenceHash));
        require(!isEvidenceSubmitted[uniqueHash], "Evidence already submitted");

        disputeEvidences[_disputeId].push(Evidence({
            disputeId: _disputeId,
            submitter: msg.sender,
            ipfsCID: _ipfsCID,
            evidenceHash: _evidenceHash,
            timestamp: block.timestamp
        }));

        isEvidenceSubmitted[uniqueHash] = true;
        emit EvidenceSubmitted(_disputeId, msg.sender, _ipfsCID);
    }

    function verifyEvidence(uint256 _disputeId, uint256 _evidenceIndex, bytes32 _computedHash) external view returns (bool) {
        require(_evidenceIndex < disputeEvidences[_disputeId].length, "Invalid index");
        return disputeEvidences[_disputeId][_evidenceIndex].evidenceHash == _computedHash;
    }

    function getEvidenceCount(uint256 _disputeId) external view returns (uint256) {
        return disputeEvidences[_disputeId].length;
    }

    function getEvidence(uint256 _disputeId, uint256 _evidenceIndex) external view returns (Evidence memory) {
        return disputeEvidences[_disputeId][_evidenceIndex];
    }
}
