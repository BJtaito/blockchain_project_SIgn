// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SecondDAO {
    address public admin;

    struct DAOVote {
        string tradeId;
        uint256 yesVotes;
        uint256 noVotes;
        mapping(address => bool) hasVoted;
        bool processed;
        bool passed;
    }

    mapping(address => bool) public allowedVoters;
    mapping(string => DAOVote) private daoVotes;

    event VoterAdded(address voter);
    event VoterRemoved(address voter);
    event Voted(string tradeId, address voter, bool approved);
    event VoteFinalized(string tradeId, bool passed);

    constructor(address[] memory initialVoters) {
        admin = msg.sender;
        for (uint i = 0; i < initialVoters.length; i++) {
            allowedVoters[initialVoters[i]] = true;
            emit VoterAdded(initialVoters[i]);
        }
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    modifier onlyVoter() {
        require(allowedVoters[msg.sender], "Not authorized voter");
        _;
    }

    function addVoter(address voter) public onlyAdmin {
        require(!allowedVoters[voter], "Already a voter");
        allowedVoters[voter] = true;
        emit VoterAdded(voter);
    }

    function removeVoter(address voter) public onlyAdmin {
        require(allowedVoters[voter], "Not a voter");
        allowedVoters[voter] = false;
        emit VoterRemoved(voter);
    }

    function vote(string calldata tradeId, bool approve) external onlyVoter {
        DAOVote storage v = daoVotes[tradeId];
        require(!v.hasVoted[msg.sender], "Already voted");
        require(!v.processed, "Vote already finalized");

        if (bytes(v.tradeId).length == 0) {
            v.tradeId = tradeId;
        }
        v.hasVoted[msg.sender] = true;

        if (approve) {
            v.yesVotes++;
        } else {
            v.noVotes++;
        }

        emit Voted(tradeId, msg.sender, approve);
    }

    function finalizeVote(string calldata tradeId) external onlyAdmin {
        DAOVote storage v = daoVotes[tradeId];
        require(!v.processed, "Already finalized");
        require(bytes(v.tradeId).length != 0, "No votes cast");

        v.processed = true;
        v.passed = v.yesVotes > v.noVotes;

        emit VoteFinalized(tradeId, v.passed);
    }

    function getVoteResult(string calldata tradeId) external view returns (
        uint256 yesVotes, uint256 noVotes, bool processed, bool passed
    ) {
        DAOVote storage v = daoVotes[tradeId];
        if (bytes(v.tradeId).length == 0) {
            return (0, 0, false, false);
        }
        return (v.yesVotes, v.noVotes, v.processed, v.passed);
    }
}
