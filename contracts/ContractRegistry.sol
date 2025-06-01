// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContractRegistry {
    struct ContractRecord {
        string contractHash;
        string assetId;
        string tradeId;
        address registrant;
        uint256 timestamp;
    }

    mapping(string => ContractRecord) private contracts; // tradeId → 계약
    string[] public tradeIds;

    event ContractRegistered(
        string indexed tradeId,
        string contractHash,
        string assetId,
        address indexed registrant,
        uint256 timestamp
    );

    function registerContract(
        string memory _contractHash,
        string memory _assetId,
        string memory _tradeId
    ) public {
        require(bytes(contracts[_tradeId].tradeId).length == 0, "Trade ID already exists");

        ContractRecord memory newRecord = ContractRecord({
            contractHash: _contractHash,
            assetId: _assetId,
            tradeId: _tradeId,
            registrant: msg.sender,
            timestamp: block.timestamp
        });

        contracts[_tradeId] = newRecord;
        tradeIds.push(_tradeId);

        emit ContractRegistered(_tradeId, _contractHash, _assetId, msg.sender, block.timestamp);
    }

    function getContract(string memory _tradeId) public view returns (
        string memory contractHash,
        string memory assetId,
        address registrant,
        uint256 timestamp
    ) {
        ContractRecord memory record = contracts[_tradeId];
        require(bytes(record.tradeId).length != 0, "Trade ID not found");
        return (
            record.contractHash,
            record.assetId,
            record.registrant,
            record.timestamp
        );
    }
}