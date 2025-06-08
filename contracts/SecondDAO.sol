// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SecondDAO {
    address public admin;

    struct DAOVote {
        string tradeId;
        uint256 yesVotes;
        uint256 noVotes;
        mapping(address => bool) hasVoted;
        mapping(address => bool) approvedVotes;
        bool processed;
        bool passed;
    }

    mapping(address => bool) public allowedVoters;
    address[] public votersList;
    mapping(string => DAOVote) private daoVotes;

    event VoterAdded(address voter);
    event VoterRemoved(address voter);
    event Voted(string tradeId, address voter, bool approved);
    event VoteFinalized(string tradeId, bool passed);

    constructor(address[] memory initialVoters) {
        admin = msg.sender;
        for (uint i = 0; i < initialVoters.length; i++) {
            allowedVoters[initialVoters[i]] = true;
            votersList.push(initialVoters[i]);
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
        votersList.push(voter);
        emit VoterAdded(voter);
    }

    function removeVoter(address voter) public onlyAdmin {
        require(allowedVoters[voter], "Not a voter");
        allowedVoters[voter] = false;
        emit VoterRemoved(voter);
    }

    function getVotersList() external view returns (address[] memory) {
        return votersList;
    }

    function vote(string calldata tradeId, bool approve) external onlyVoter {
        DAOVote storage v = daoVotes[tradeId];
        require(!v.hasVoted[msg.sender], "Already voted");
        require(!v.processed, "Vote already finalized");

        if (bytes(v.tradeId).length == 0) {
            v.tradeId = tradeId;
        }

        v.hasVoted[msg.sender] = true;
        v.approvedVotes[msg.sender] = approve;

        if (approve) {
            v.yesVotes++;
        } else {
            v.noVotes++;
        }

        emit Voted(tradeId, msg.sender, approve);

        // ✅ 자동 finalize 조건
        uint totalVoters = 0;
        for (uint i = 0; i < votersList.length; i++) {
            if (allowedVoters[votersList[i]]) {
                totalVoters++;
            }
        }

        uint totalVotes = v.yesVotes + v.noVotes;

        // 자동 처리 조건 충족 시
        if (!v.processed) {
            if (totalVoters == 2 && v.yesVotes == 2) {
                v.processed = true;
                v.passed = true;
                emit VoteFinalized(tradeId, true);
            } else if (totalVoters > 2 && totalVotes == totalVoters && v.yesVotes > v.noVotes) {
                v.processed = true;
                v.passed = true;
                emit VoteFinalized(tradeId, true);
            }
        }
    }

    function finalizeVote(string calldata tradeId) external onlyAdmin {
        DAOVote storage v = daoVotes[tradeId];
        require(!v.processed, "Already finalized");
        require(bytes(v.tradeId).length != 0, "No votes cast");

        v.processed = true;

        uint totalVoters = 0;
        for (uint i = 0; i < votersList.length; i++) {
            if (allowedVoters[votersList[i]]) {
                totalVoters++;
            }
        }

        if (totalVoters == 2) {
            v.passed = (v.yesVotes == 2);
        } else {
            v.passed = (v.yesVotes > v.noVotes);
        }

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

    function getVoterVote(string calldata tradeId, address voter) external view returns (bool voted, bool approved) {
        DAOVote storage v = daoVotes[tradeId];
        voted = v.hasVoted[voter];
        approved = v.approvedVotes[voter];
    }
}
