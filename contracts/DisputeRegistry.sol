// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract DisputeRegistry is AccessControl, ReentrancyGuard {
    bytes32 public constant EXPERT_ROLE = keccak256("EXPERT_ROLE");
    bytes32 public constant RESOLUTION_ROLE = keccak256("RESOLUTION_ROLE"); // Granted to DisputeResolution.sol

    uint256 public constant ARBITRATOR_STAKE = 1 ether;
    uint256 public constant EXPERT_STAKE = 2 ether;

    struct ArbitratorProfile {
        bool isRegistered;
        uint256 stakedAmount;
        uint256 activeDisputes;
        uint256 correctVotes;
        uint256 wrongVotes;
    }

    mapping(address => ArbitratorProfile) public arbitrators;
    address[] public registeredArbitrators;
    
    mapping(address => ArbitratorProfile) public experts;
    address[] public registeredExperts;

    event ArbitratorRegistered(address indexed arbitrator, uint256 amount);
    event ExpertRegistered(address indexed expert, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event Slashed(address indexed user, uint256 amount);
    event Rewarded(address indexed user, uint256 amount);

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    function registerArbitrator() external payable nonReentrant {
        require(msg.value == ARBITRATOR_STAKE, "Incorrect stake");
        require(!arbitrators[msg.sender].isRegistered, "Already registered");

        arbitrators[msg.sender] = ArbitratorProfile({
            isRegistered: true,
            stakedAmount: msg.value,
            activeDisputes: 0,
            correctVotes: 0,
            wrongVotes: 0
        });
        registeredArbitrators.push(msg.sender);
        emit ArbitratorRegistered(msg.sender, msg.value);
    }

    function registerExpert() external payable nonReentrant {
        require(msg.value == EXPERT_STAKE, "Incorrect stake");
        require(!experts[msg.sender].isRegistered, "Already registered");

        experts[msg.sender] = ArbitratorProfile({
            isRegistered: true,
            stakedAmount: msg.value,
            activeDisputes: 0,
            correctVotes: 0,
            wrongVotes: 0
        });
        registeredExperts.push(msg.sender);
        _grantRole(EXPERT_ROLE, msg.sender);
        emit ExpertRegistered(msg.sender, msg.value);
    }

    function unstake() external nonReentrant {
        if (arbitrators[msg.sender].isRegistered) {
            require(arbitrators[msg.sender].activeDisputes == 0, "Active disputes");
            uint256 amount = arbitrators[msg.sender].stakedAmount;
            arbitrators[msg.sender].isRegistered = false;
            arbitrators[msg.sender].stakedAmount = 0;
            payable(msg.sender).transfer(amount);
            emit Unstaked(msg.sender, amount);
        } else if (experts[msg.sender].isRegistered) {
            require(experts[msg.sender].activeDisputes == 0, "Active disputes");
            uint256 amount = experts[msg.sender].stakedAmount;
            experts[msg.sender].isRegistered = false;
            experts[msg.sender].stakedAmount = 0;
            _revokeRole(EXPERT_ROLE, msg.sender);
            payable(msg.sender).transfer(amount);
            emit Unstaked(msg.sender, amount);
        } else {
            revert("Not registered");
        }
    }

    function lockArbitrator(address _arbitrator) external onlyRole(RESOLUTION_ROLE) {
        if (arbitrators[_arbitrator].isRegistered) {
            arbitrators[_arbitrator].activeDisputes++;
        } else if (experts[_arbitrator].isRegistered) {
            experts[_arbitrator].activeDisputes++;
        }
    }

    function releaseArbitrator(address _arbitrator) external onlyRole(RESOLUTION_ROLE) {
        if (arbitrators[_arbitrator].isRegistered) {
            if (arbitrators[_arbitrator].activeDisputes > 0) {
                arbitrators[_arbitrator].activeDisputes--;
            }
        } else if (experts[_arbitrator].isRegistered) {
            if (experts[_arbitrator].activeDisputes > 0) {
                experts[_arbitrator].activeDisputes--;
            }
        }
    }

    function slash(address _user, uint256 _amount) external onlyRole(RESOLUTION_ROLE) nonReentrant {
        if (arbitrators[_user].isRegistered) {
            uint256 slashAmount = arbitrators[_user].stakedAmount >= _amount ? _amount : arbitrators[_user].stakedAmount;
            arbitrators[_user].stakedAmount -= slashAmount;
            arbitrators[_user].wrongVotes++;
        } else if (experts[_user].isRegistered) {
            uint256 slashAmount = experts[_user].stakedAmount >= _amount ? _amount : experts[_user].stakedAmount;
            experts[_user].stakedAmount -= slashAmount;
            experts[_user].wrongVotes++;
        }
        emit Slashed(_user, _amount);
    }

    function reward(address _user, uint256 _amount) external onlyRole(RESOLUTION_ROLE) {
        if (arbitrators[_user].isRegistered) {
            arbitrators[_user].correctVotes++;
        } else if (experts[_user].isRegistered) {
            experts[_user].correctVotes++;
        }
        if (_amount > 0) {
            emit Rewarded(_user, _amount);
        }
    }

    // Pseudo-random selection for prototype (NOT secure for prod)
    function selectJury(uint256 _seed, uint256 _count) external view returns (address[] memory) {
        require(registeredArbitrators.length >= _count, "Not enough arbitrators");
        address[] memory jury = new address[](_count);
        for (uint256 i = 0; i < _count; i++) {
            uint256 index = (_seed + i) % registeredArbitrators.length;
            jury[i] = registeredArbitrators[index];
        }
        return jury;
    }

    function selectExpertPanel(uint256 _seed, uint256 _count) external view returns (address[] memory) {
        require(registeredExperts.length >= _count, "Not enough experts");
        address[] memory panel = new address[](_count);
        for (uint256 i = 0; i < _count; i++) {
            uint256 index = (_seed + i) % registeredExperts.length;
            panel[i] = registeredExperts[index];
        }
        return panel;
    }
}
