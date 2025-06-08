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

    struct VoteStatus {
        address partyA;
        address partyB;
        bool votedA;
        bool votedB;
        bool approvedA;
        bool approvedB;
        bool finalized;
    }

    mapping(string => ContractRecord) private contracts; // tradeId → 계약
    mapping(string => VoteStatus) private votes;         // tradeId → 투표상태
    string[] public tradeIds;

    event ContractRegistered(
        string indexed tradeId,
        string contractHash,
        string assetId,
        address indexed registrant,
        uint256 timestamp
    );

    event ContractApproved(string tradeId, address partyA, address partyB);
    event ContractRejected(string tradeId);

    function registerContract(
        string memory _contractHash,
        string memory _assetId,
        string memory _tradeId,
        address _partyA,
        address _partyB
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

        votes[_tradeId] = VoteStatus({
            partyA: _partyA,
            partyB: _partyB,
            votedA: false,
            votedB: false,
            approvedA: false,
            approvedB: false,
            finalized: false
        });

        emit ContractRegistered(_tradeId, _contractHash, _assetId, msg.sender, block.timestamp);
    }

    function voteOnContract(string memory _tradeId, bool approval) public {
        VoteStatus storage vote = votes[_tradeId];
        require(!vote.finalized, "Already finalized");

        if (msg.sender == vote.partyA) {
            require(!vote.votedA, "Already voted by A");
            vote.votedA = true;
            vote.approvedA = approval;
        } else if (msg.sender == vote.partyB) {
            require(!vote.votedB, "Already voted by B");
            vote.votedB = true;
            vote.approvedB = approval;
        } else {
            revert("Not authorized");
        }

        if (vote.votedA && vote.votedB) {
            if (vote.approvedA && vote.approvedB) {
                vote.finalized = true;
                emit ContractApproved(_tradeId, vote.partyA, vote.partyB);
            } else {
                delete contracts[_tradeId];
                delete votes[_tradeId];
                emit ContractRejected(_tradeId);
            }
        }
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

    function getVoters(string memory _tradeId) public view returns (address, address) {
        VoteStatus memory vote = votes[_tradeId];
        return (vote.partyA, vote.partyB);
    }
    function getAllTradeIds() public view returns (string[] memory) {
        return tradeIds;
    }
    function getVoteStatus(string memory _tradeId) public view returns (
    bool, bool, bool, bool, bool
    ) {
        VoteStatus memory v = votes[_tradeId];
        return (v.votedA, v.votedB, v.approvedA, v.approvedB, v.finalized);
    }
}
