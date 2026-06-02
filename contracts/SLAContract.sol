// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract SLAContract {
    struct SLA {
        uint256 deliveryDeadline;
        uint256 paymentDeadline;
        uint256 requiredQuantity;
        uint256 latePenalty;
        uint256 shortagePenalty;
        uint256 damagePenalty;
        uint256 paymentDelayPenalty;
        bool active;
    }

    uint256 public slaCounter;
    mapping(uint256 => SLA) public slas;

    event SLACreated(uint256 indexed slaId);

    function createSLA(
        uint256 _deliveryDeadline,
        uint256 _paymentDeadline,
        uint256 _requiredQuantity,
        uint256 _latePenalty,
        uint256 _shortagePenalty,
        uint256 _damagePenalty,
        uint256 _paymentDelayPenalty
    ) external returns (uint256) {
        slaCounter++;

        slas[slaCounter] = SLA({
            deliveryDeadline: _deliveryDeadline,
            paymentDeadline: _paymentDeadline,
            requiredQuantity: _requiredQuantity,
            latePenalty: _latePenalty,
            shortagePenalty: _shortagePenalty,
            damagePenalty: _damagePenalty,
            paymentDelayPenalty: _paymentDelayPenalty,
            active: true
        });

        emit SLACreated(slaCounter);
        return slaCounter;
    }

    function checkLateDelivery(uint256 _slaId, uint256 _deliveryTime) external view returns (bool) {
        return _deliveryTime > slas[_slaId].deliveryDeadline;
    }

    function checkShortage(uint256 _slaId, uint256 _deliveredQuantity) external view returns (bool) {
        return _deliveredQuantity < slas[_slaId].requiredQuantity;
    }

    function checkPaymentDelay(uint256 _slaId, uint256 _paymentTime) external view returns (bool) {
        return _paymentTime > slas[_slaId].paymentDeadline;
    }
}