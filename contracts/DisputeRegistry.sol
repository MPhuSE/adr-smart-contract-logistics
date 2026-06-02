// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract DisputeRegistry {
    struct Arbitrator {
        bool registered;
        bool expert;
        uint256 stake;
        uint256 correctVotes;
        uint256 wrongVotes;
    }

    mapping(address => Arbitrator) public arbitrators;
    address[] public arbitratorList;
    address[] public expertList;

    uint256 public constant MIN_STAKE = 0.01 ether;

    event ArbitratorRegistered(address indexed arbitrator, bool expert);
    event StakeSlashed(address indexed arbitrator, uint256 amount);

    function registerArbitrator(bool _expert) external payable {
        require(!arbitrators[msg.sender].registered, "Already registered");
        require(msg.value >= MIN_STAKE, "Stake too low");

        arbitrators[msg.sender] = Arbitrator({
            registered: true,
            expert: _expert,
            stake: msg.value,
            correctVotes: 0,
            wrongVotes: 0
        });

        if (_expert) {
            expertList.push(msg.sender);
        } else {
            arbitratorList.push(msg.sender);
        }

        emit ArbitratorRegistered(msg.sender, _expert);
    }

    function isArbitrator(address _user) external view returns (bool) {
        return arbitrators[_user].registered;
    }

    function isExpert(address _user) external view returns (bool) {
        return arbitrators[_user].registered && arbitrators[_user].expert;
    }

    function getArbitrator(uint256 _index) external view returns (address) {
        return arbitratorList[_index];
    }

    function getExpert(uint256 _index) external view returns (address) {
        return expertList[_index];
    }

    function getArbitratorCount() external view returns (uint256) {
        return arbitratorList.length;
    }

    function getExpertCount() external view returns (uint256) {
        return expertList.length;
    }

    function recordVoteResult(address _arbitrator, bool _correct) external {
        require(arbitrators[_arbitrator].registered, "Not arbitrator");

        if (_correct) {
            arbitrators[_arbitrator].correctVotes++;
        } else {
            arbitrators[_arbitrator].wrongVotes++;

            uint256 penalty = arbitrators[_arbitrator].stake / 10;
            arbitrators[_arbitrator].stake -= penalty;

            emit StakeSlashed(_arbitrator, penalty);
        }
    }
}