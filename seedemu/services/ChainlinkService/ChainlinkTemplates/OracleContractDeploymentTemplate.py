from typing import Dict

OracleContractDeploymentTemplate: Dict[str, str] = {}

OracleContractDeploymentTemplate['oracle_contract_deploy']="""\
#!/bin/env python3
import time
import logging
import os
from queue import Queue
from web3 import Web3, HTTPProvider
import re
import requests
import random
import json

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}/getEth"

contract_folder = './contracts/'
retry_delay = random.randint(20, 100)

deployment_queue = Queue()
deployment_queue.put({{}})

url = "http://{init_node_url}"
response = requests.get(url)
html_content = response.text
match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)

if match and match.group(1):
	link_address = Web3.toChecksumAddress(match.group(1))
else:
	logging.error("Failed to extract Link Token contract address from HTML content.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

web3 = Web3(HTTPProvider(rpc_url))
if not web3.isConnected():
    logging.error("Failed to connect to Ethereum node.")
    exit()

new_account = web3.eth.account.create()
owner_address = new_account.address
private_key = new_account.privateKey.hex()

data = {{"new_account": owner_address}}
response = requests.post(faucet_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
if response.status_code != 200:
	logging.error(f"Failed to request funds from faucet: {{response.text}}")
	exit()

check_interval = 10

def is_address_funded(address):
    balance = web3.eth.get_balance(address)
    return balance > 0

while True:
	if is_address_funded(owner_address):
		logging.info(f"Address funded: {{owner_address}}")
		break
	else:
		logging.info(f"Waiting for address to be funded: {{owner_address}}")
		time.sleep(check_interval)

with open(os.path.join(contract_folder, 'oracle_contract.abi'), 'r') as abi_file:
    contract_abi = abi_file.read()
with open(os.path.join(contract_folder, 'oracle_contract.bin'), 'r') as bin_file:
    contract_bytecode = bin_file.read().strip()
account = web3.eth.account.from_key(private_key)

gas_price = web3.eth.gasPrice
while not deployment_queue.empty():
    try:
        deployment_queue.get()
        nonce = web3.eth.getTransactionCount(account.address, 'pending')
        OracleContract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        transaction = OracleContract.constructor(link_address, owner_address).buildTransaction({{
            'from': account.address,
            'nonce': nonce,
            'gas': 4000000,
            'gasPrice': gas_price
        }})
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logging.info(f"Attempting to deploy contract, TX Hash: {{tx_hash.hex()}}")

        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if tx_receipt.status == 1:
            logging.info(f"Contract deployed at: {{tx_receipt.contractAddress}}")
            directory = './deployed_contracts'
            if not os.path.exists(directory): os.makedirs(directory)
            with open('./deployed_contracts/oracle_contract_address.txt', 'w') as address_file:
                address_file.write(f"{{tx_receipt.contractAddress}}")
            contract_address = tx_receipt.contractAddress
        else:
            logging.error("Transaction failed. Retrying...")
            deployment_queue.put({{}})
            time.sleep(retry_delay)

    except Exception as e:
        logging.error(f"An error occurred during contract deployment: {{e}}. Retrying...")
        deployment_queue.put({{}})
        time.sleep(retry_delay)
        
def authorize_address(sender, oracle_contract_address, nonce):
    try:
        oracle_contract = web3.eth.contract(address=oracle_contract_address, abi=contract_abi)
        txn_dict = oracle_contract.functions.setAuthorizedSenders([sender]).buildTransaction({{
            'chainId': {chain_id},
            'gas': 4000000,
            'gasPrice': web3.toWei('50', 'gwei'),
            'nonce': nonce,
        }})
        signed_txn = web3.eth.account.sign_transaction(txn_dict, account.privateKey)
        txn_receipt = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(txn_receipt)
        logging.info(f'Success: {{txn_receipt}}')
        return True
    except Exception as e:
        logging.error(f'Error: {{e}}')
        if "replacement transaction underpriced" in str(e):
            logging.warning('Requeuing due to underpriced transaction')
            return False
        else:
            return True

with open('./deployed_contracts/sender.txt', 'r') as file:
    sender = file.read().strip()
authorization_success = False
while not authorization_success:
    nonce = web3.eth.getTransactionCount(owner_address, 'pending')
    authorization_success = authorize_address(sender, contract_address, nonce)
    if not authorization_success:
        time.sleep(retry_delay)
"""

OracleContractDeploymentTemplate['oracle_contract_abi']="""\
[
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": false,
				"internalType": "address[]",
				"name": "senders",
				"type": "address[]"
			},
			{
				"indexed": false,
				"internalType": "address",
				"name": "changedBy",
				"type": "address"
			}
		],
		"name": "AuthorizedSendersChanged",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			}
		],
		"name": "CancelOracleRequest",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "specId",
				"type": "bytes32"
			},
			{
				"indexed": false,
				"internalType": "address",
				"name": "requester",
				"type": "address"
			},
			{
				"indexed": false,
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"indexed": false,
				"internalType": "address",
				"name": "callbackAddr",
				"type": "address"
			},
			{
				"indexed": false,
				"internalType": "bytes4",
				"name": "callbackFunctionId",
				"type": "bytes4"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "cancelExpiration",
				"type": "uint256"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "dataVersion",
				"type": "uint256"
			},
			{
				"indexed": false,
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "OracleRequest",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			}
		],
		"name": "OracleResponse",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "address",
				"name": "acceptedContract",
				"type": "address"
			}
		],
		"name": "OwnableContractAccepted",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "address",
				"name": "from",
				"type": "address"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "to",
				"type": "address"
			}
		],
		"name": "OwnershipTransferRequested",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "address",
				"name": "from",
				"type": "address"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "to",
				"type": "address"
			}
		],
		"name": "OwnershipTransferred",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": false,
				"internalType": "address[]",
				"name": "targets",
				"type": "address[]"
			},
			{
				"indexed": false,
				"internalType": "address[]",
				"name": "senders",
				"type": "address[]"
			},
			{
				"indexed": false,
				"internalType": "address",
				"name": "changedBy",
				"type": "address"
			}
		],
		"name": "TargetsUpdatedAuthorizedSenders",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "targets",
				"type": "address[]"
			},
			{
				"internalType": "address[]",
				"name": "senders",
				"type": "address[]"
			}
		],
		"name": "acceptAuthorizedReceivers",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "ownable",
				"type": "address[]"
			}
		],
		"name": "acceptOwnableContracts",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "acceptOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunc",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "expiration",
				"type": "uint256"
			}
		],
		"name": "cancelOracleRequest",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "nonce",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunc",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "expiration",
				"type": "uint256"
			}
		],
		"name": "cancelOracleRequestByRequester",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address payable[]",
				"name": "receivers",
				"type": "address[]"
			},
			{
				"internalType": "uint256[]",
				"name": "amounts",
				"type": "uint256[]"
			}
		],
		"name": "distributeFunds",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "callbackAddress",
				"type": "address"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunctionId",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "expiration",
				"type": "uint256"
			},
			{
				"internalType": "bytes32",
				"name": "data",
				"type": "bytes32"
			}
		],
		"name": "fulfillOracleRequest",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "requestId",
				"type": "bytes32"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "callbackAddress",
				"type": "address"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunctionId",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "expiration",
				"type": "uint256"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "fulfillOracleRequest2",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "sender",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "onTokenTransfer",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "sender",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "bytes32",
				"name": "specId",
				"type": "bytes32"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunctionId",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "nonce",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "dataVersion",
				"type": "uint256"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "operatorRequest",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "sender",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "payment",
				"type": "uint256"
			},
			{
				"internalType": "bytes32",
				"name": "specId",
				"type": "bytes32"
			},
			{
				"internalType": "address",
				"name": "callbackAddress",
				"type": "address"
			},
			{
				"internalType": "bytes4",
				"name": "callbackFunctionId",
				"type": "bytes4"
			},
			{
				"internalType": "uint256",
				"name": "nonce",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "dataVersion",
				"type": "uint256"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "oracleRequest",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "to",
				"type": "address"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "ownerForward",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "to",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "value",
				"type": "uint256"
			},
			{
				"internalType": "bytes",
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "ownerTransferAndCall",
		"outputs": [
			{
				"internalType": "bool",
				"name": "success",
				"type": "bool"
			}
		],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "senders",
				"type": "address[]"
			}
		],
		"name": "setAuthorizedSenders",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "targets",
				"type": "address[]"
			},
			{
				"internalType": "address[]",
				"name": "senders",
				"type": "address[]"
			}
		],
		"name": "setAuthorizedSendersOn",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "ownable",
				"type": "address[]"
			},
			{
				"internalType": "address",
				"name": "newOwner",
				"type": "address"
			}
		],
		"name": "transferOwnableContracts",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "to",
				"type": "address"
			}
		],
		"name": "transferOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "recipient",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "withdraw",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "link",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			}
		],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "getAuthorizedSenders",
		"outputs": [
			{
				"internalType": "address[]",
				"name": "",
				"type": "address[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getChainlinkToken",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getExpiryTime",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "sender",
				"type": "address"
			}
		],
		"name": "isAuthorizedSender",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "typeAndVersion",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "pure",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "withdrawable",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]
"""

OracleContractDeploymentTemplate['oracle_contract_bin']="""\
60a060405260016006553480156200001657600080fd5b506040516200469738038062004697833981810160405260408110156200003c57600080fd5b810190808051906020019092919080519060200190929190505050808060008073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff161415620000fe576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260188152602001807f43616e6e6f7420736574206f776e657220746f207a65726f000000000000000081525060200191505060405180910390fd5b81600260006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff161462000186576200018581620001c860201b60201c565b5b5050508173ffffffffffffffffffffffffffffffffffffffff1660808173ffffffffffffffffffffffffffffffffffffffff1660601b8152505050506200032b565b3373ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614156200026b576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260178152602001807f43616e6e6f74207472616e7366657220746f2073656c6600000000000000000081525060200191505060405180910390fd5b80600360006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508073ffffffffffffffffffffffffffffffffffffffff16600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff167fed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae127860405160405180910390a350565b60805160601c61432b6200036c600039806111cf5280611414528061256c528061289f5280612d9e52806132b752806137255280613c2d525061432b6000f3fe6080604052600436106101665760003560e01c80636ae0bc76116100d1578063a4c0ed361161008a578063f2fde38b11610064578063f2fde38b14610dc9578063f3fef3a314610e1a578063fa00763a14610e75578063fc4a03ed14610edc57610166565b8063a4c0ed3614610bd9578063eb007d9914610ccb578063ee56997b14610d4357610166565b80636ae0bc76146108725780636bd59ec0146109755780636ee4d55314610a4357806379ba509714610abb5780638da5cb5b14610ad2578063902fc37014610b1357610166565b80633c6d41b9116101235780633c6d41b9146103ff5780633ec5bc14146104f6578063404299461461059c5780634ab0d190146106b4578063501883011461076c5780635ffa62881461079757610166565b806301994b991461016b578063033f49f7146101f1578063165d35e114610297578063181f5a77146102d85780632408afaa1461036857806325cb5bc0146103d4575b600080fd5b34801561017757600080fd5b506101ef6004803603602081101561018e57600080fd5b81019080803590602001906401000000008111156101ab57600080fd5b8201836020820111156101bd57600080fd5b803590602001918460208302840111640100000000831117156101df57600080fd5b9091929391929390505050610fb7565b005b3480156101fd57600080fd5b506102956004803603604081101561021457600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019064010000000081111561025157600080fd5b82018360208201111561026357600080fd5b8035906020019184600183028401116401000000008311171561028557600080fd5b90919293919293905050506111c4565b005b3480156102a357600080fd5b506102ac611410565b604051808273ffffffffffffffffffffffffffffffffffffffff16815260200191505060405180910390f35b3480156102e457600080fd5b506102ed611438565b6040518080602001828103825283818151815260200191508051906020019080838360005b8381101561032d578082015181840152602081019050610312565b50505050905090810190601f16801561035a5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b34801561037457600080fd5b5061037d611475565b6040518080602001828103825283818151815260200191508051906020019060200280838360005b838110156103c05780820151818401526020810190506103a5565b505050509050019250505060405180910390f35b3480156103e057600080fd5b506103e9611503565b6040518082815260200191505060405180910390f35b34801561040b57600080fd5b506104f4600480360360e081101561042257600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803590602001909291908035906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff191690602001909291908035906020019092919080359060200190929190803590602001906401000000008111156104b057600080fd5b8201836020820111156104c257600080fd5b803590602001918460018302840111640100000000831117156104e457600080fd5b9091929391929390505050611509565b005b34801561050257600080fd5b5061059a6004803603604081101561051957600080fd5b810190808035906020019064010000000081111561053657600080fd5b82018360208201111561054857600080fd5b8035906020019184602083028401116401000000008311171561056a57600080fd5b9091929391929390803573ffffffffffffffffffffffffffffffffffffffff1690602001909291905050506116b9565b005b3480156105a857600080fd5b506106b260048036036101008110156105c057600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019092919080359060200190929190803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916906020019092919080359060200190929190803590602001909291908035906020019064010000000081111561066e57600080fd5b82018360208201111561068057600080fd5b803590602001918460018302840111640100000000831117156106a257600080fd5b909192939192939050505061180b565b005b3480156106c057600080fd5b50610754600480360360c08110156106d757600080fd5b810190808035906020019092919080359060200190929190803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916906020019092919080359060200190929190803590602001909291905050506119bc565b60405180821515815260200191505060405180910390f35b34801561077857600080fd5b50610781611d1c565b6040518082815260200191505060405180910390f35b3480156107a357600080fd5b50610870600480360360408110156107ba57600080fd5b81019080803590602001906401000000008111156107d757600080fd5b8201836020820111156107e957600080fd5b8035906020019184602083028401116401000000008311171561080b57600080fd5b90919293919293908035906020019064010000000081111561082c57600080fd5b82018360208201111561083e57600080fd5b8035906020019184602083028401116401000000008311171561086057600080fd5b9091929391929390505050611d2b565b005b34801561087e57600080fd5b5061095d600480360360c081101561089557600080fd5b810190808035906020019092919080359060200190929190803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19169060200190929190803590602001909291908035906020019064010000000081111561091957600080fd5b82018360208201111561092b57600080fd5b8035906020019184600183028401116401000000008311171561094d57600080fd5b9091929391929390505050611dc1565b60405180821515815260200191505060405180910390f35b610a416004803603604081101561098b57600080fd5b81019080803590602001906401000000008111156109a857600080fd5b8201836020820111156109ba57600080fd5b803590602001918460208302840111640100000000831117156109dc57600080fd5b9091929391929390803590602001906401000000008111156109fd57600080fd5b820183602082011115610a0f57600080fd5b80359060200191846020830284011164010000000083111715610a3157600080fd5b90919293919293905050506121f7565b005b348015610a4f57600080fd5b50610ab960048036036080811015610a6657600080fd5b81019080803590602001909291908035906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19169060200190929190803590602001909291905050506123bb565b005b348015610ac757600080fd5b50610ad061263e565b005b348015610ade57600080fd5b50610ae7612808565b604051808273ffffffffffffffffffffffffffffffffffffffff16815260200191505060405180910390f35b348015610b1f57600080fd5b50610bc160048036036060811015610b3657600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019092919080359060200190640100000000811115610b7d57600080fd5b820183602082011115610b8f57600080fd5b80359060200191846001830284011164010000000083111715610bb157600080fd5b9091929391929390505050612832565b60405180821515815260200191505060405180910390f35b348015610be557600080fd5b50610cc960048036036060811015610bfc57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019092919080359060200190640100000000811115610c4357600080fd5b820183602082011115610c5557600080fd5b80359060200191846001830284011164010000000083111715610c7757600080fd5b91908080601f016020809104026020016040519081016040528093929190818152602001838380828437600081840152601f19601f8201169050808301925050505050505091929192905050506129a8565b005b348015610cd757600080fd5b50610d4160048036036080811015610cee57600080fd5b81019080803590602001909291908035906020019092919080357bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916906020019092919080359060200190929190505050612ba1565b005b348015610d4f57600080fd5b50610dc760048036036020811015610d6657600080fd5b8101908080359060200190640100000000811115610d8357600080fd5b820183602082011115610d9557600080fd5b80359060200191846020830284011164010000000083111715610db757600080fd5b9091929391929390505050612e71565b005b348015610dd557600080fd5b50610e1860048036036020811015610dec57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050613238565b005b348015610e2657600080fd5b50610e7360048036036040811015610e3d57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019092919050505061324c565b005b348015610e8157600080fd5b50610ec460048036036020811015610e9857600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919050505061338c565b60405180821515815260200191505060405180910390f35b348015610ee857600080fd5b50610fb560048036036040811015610eff57600080fd5b8101908080359060200190640100000000811115610f1c57600080fd5b820183602082011115610f2e57600080fd5b80359060200191846020830284011164010000000083111715610f5057600080fd5b909192939192939080359060200190640100000000811115610f7157600080fd5b820183602082011115610f8357600080fd5b80359060200191846020830284011164010000000083111715610fa557600080fd5b90919293919293905050506133e1565b005b610fbf6135fa565b611031576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601d8152602001807f43616e6e6f742073657420617574686f72697a65642073656e6465727300000081525060200191505060405180910390fd5b60005b828290508110156111bf5760016005600085858581811061105157fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff0219169083151502179055508282828181106110cb57fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff167f615a0c1cb00a60d4acd77ec67acf2f17f223ef0932d591052fabc33643fe7e8260405160405180910390a282828281811061113657fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166379ba50976040518163ffffffff1660e01b8152600401600060405180830381600087803b15801561119a57600080fd5b505af11580156111ae573d6000803e3d6000fd5b505050508080600101915050611034565b505050565b6111cc613647565b827f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff16141561128f576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260138152602001807f43616e6e6f742063616c6c20746f204c494e4b0000000000000000000000000081525060200191505060405180910390fd5b6112ae8473ffffffffffffffffffffffffffffffffffffffff1661370c565b611320576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601a8152602001807f4d75737420666f727761726420746f206120636f6e747261637400000000000081525060200191505060405180910390fd5b60008473ffffffffffffffffffffffffffffffffffffffff1684846040518083838082843780830192505050925050506000604051808303816000865af19150503d806000811461138d576040519150601f19603f3d011682016040523d82523d6000602084013e611392565b606091505b5050905080611409576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260158152602001807f466f727761726465642063616c6c206661696c6564000000000000000000000081525060200191505060405180910390fd5b5050505050565b60007f0000000000000000000000000000000000000000000000000000000000000000905090565b60606040518060400160405280600e81526020017f4f70657261746f7220312e302e30000000000000000000000000000000000000815250905090565b606060018054806020026020016040519081016040528092919081815260200182805480156114f957602002820191906000526020600020905b8160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190600101908083116114af575b5050505050905090565b61012c81565b611511611410565b73ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146115b1576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260138152602001807f4d75737420757365204c494e4b20746f6b656e0000000000000000000000000081525060200191505060405180910390fd5b6000806115c28a8a8c8a8a8a61371f565b91509150877fd8d7ecc4800d25fa53ce0372f13a416d98907a7ef3d8d3bdd79cf4fe75529c658b848c8e8c878c8c8c604051808a73ffffffffffffffffffffffffffffffffffffffff1681526020018981526020018881526020018773ffffffffffffffffffffffffffffffffffffffff168152602001867bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19168152602001858152602001848152602001806020018281038252848482818152602001925080828437600081840152601f19601f8201169050808301925050509a505050505050505050505060405180910390a250505050505050505050565b6116c1613647565b60005b83839050811015611805576000600560008686858181106116e157fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff02191690831515021790555083838281811061175b57fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1663f2fde38b836040518263ffffffff1660e01b8152600401808273ffffffffffffffffffffffffffffffffffffffff168152602001915050600060405180830381600087803b1580156117e057600080fd5b505af11580156117f4573d6000803e3d6000fd5b5050505080806001019150506116c4565b50505050565b611813611410565b73ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146118b3576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260138152602001807f4d75737420757365204c494e4b20746f6b656e0000000000000000000000000081525060200191505060405180910390fd5b6000806118c48b8b8a8a8a8a61371f565b91509150887fd8d7ecc4800d25fa53ce0372f13a416d98907a7ef3d8d3bdd79cf4fe75529c658c848d8f8c878c8c8c604051808a73ffffffffffffffffffffffffffffffffffffffff1681526020018981526020018881526020018773ffffffffffffffffffffffffffffffffffffffff168152602001867bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19168152602001858152602001848152602001806020018281038252848482818152602001925080828437600081840152601f19601f8201169050808301925050509a505050505050505050505060405180910390a25050505050505050505050565b60006119c66139b8565b86600060081b6004600083815260200190815260200160002060000160009054906101000a900460081b60ff19161415611a68576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f4d757374206861766520612076616c696420726571756573744964000000000081525060200191505060405180910390fd5b85600560008273ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff1615611b29576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601a8152602001807f43616e6e6f742063616c6c206f776e656420636f6e747261637400000000000081525060200191505060405180910390fd5b611b3889898989896001613a35565b887f9e9bc7616d42c2835d05ae617e508454e63b30b934be8aa932ebc125e0e58a6460405160405180910390a262061a805a1015611bde576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260208152602001807f4d7573742070726f7669646520636f6e73756d657220656e6f7567682067617381525060200191505060405180910390fd5b60008773ffffffffffffffffffffffffffffffffffffffff16878b876040516024018083815260200182815260200192505050604051602081830303815290604052907bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19166020820180517bffffffffffffffffffffffffffffffffffffffffffffffffffffffff83818316178352505050506040518082805190602001908083835b60208310611ca15780518252602082019150602081019050602083039250611c7e565b6001836020036101000a0380198251168184511680821785525050505050509050019150506000604051808303816000865af19150503d8060008114611d03576040519150601f19603f3d011682016040523d82523d6000602084013e611d08565b606091505b505090508093505050509695505050505050565b6000611d26613c0c565b905090565b611d336135fa565b611da5576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601d8152602001807f43616e6e6f742073657420617574686f72697a65642073656e6465727300000081525060200191505060405180910390fd5b611daf8484610fb7565b611dbb848484846133e1565b50505050565b6000611dcb6139b8565b87600060081b6004600083815260200190815260200160002060000160009054906101000a900460081b60ff19161415611e6d576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f4d757374206861766520612076616c696420726571756573744964000000000081525060200191505060405180910390fd5b86600560008273ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff1615611f2e576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601a8152602001807f43616e6e6f742063616c6c206f776e656420636f6e747261637400000000000081525060200191505060405180910390fd5b8985856020828290501015611fab576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f526573706f6e7365206d757374206265203e203332206279746573000000000081525060200191505060405180910390fd5b600082359050808414612026576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601c8152602001807f466972737420776f7264206d757374206265207265717565737449640000000081525060200191505060405180910390fd5b6120358e8e8e8e8e6002613a35565b8d7f9e9bc7616d42c2835d05ae617e508454e63b30b934be8aa932ebc125e0e58a6460405160405180910390a262061a805a10156120db576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260208152602001807f4d7573742070726f7669646520636f6e73756d657220656e6f7567682067617381525060200191505060405180910390fd5b60008c73ffffffffffffffffffffffffffffffffffffffff168c8b8b60405160200180847bffffffffffffffffffffffffffffffffffffffffffffffffffffffff191681526004018383808284378083019250505093505050506040516020818303038152906040526040518082805190602001908083835b602083106121775780518252602082019150602081019050602083039250612154565b6001836020036101000a0380198251168184511680821785525050505050509050019150506000604051808303816000865af19150503d80600081146121d9576040519150601f19603f3d011682016040523d82523d6000602084013e6121de565b606091505b5050905080975050505050505050979650505050505050565b60008484905011801561220f57508181905084849050145b612281576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260178152602001807f496e76616c6964206172726179206c656e67746828732900000000000000000081525060200191505060405180910390fd5b600034905060005b8585905081101561233d5760008484838181106122a257fe5b9050602002013590506122be8184613d0190919063ffffffff16565b92508686838181106122cc57fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166108fc829081150290604051600060405180830381858888f1935050505015801561232e573d6000803e3d6000fd5b50508080600101915050612289565b50600081146123b4576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260118152602001807f546f6f206d756368204554482073656e7400000000000000000000000000000081525060200191505060405180910390fd5b5050505050565b60006123c984338585613d8a565b90508060ff19166004600087815260200190815260200160002060000160009054906101000a900460081b60ff19161461246b576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601e8152602001807f506172616d7320646f206e6f74206d617463682072657175657374204944000081525060200191505060405180910390fd5b428211156124e1576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f52657175657374206973206e6f7420657870697265640000000000000000000081525060200191505060405180910390fd5b60046000868152602001908152602001600020600080820160006101000a8154907effffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff021916905560008201601f6101000a81549060ff02191690555050847fa7842b9ec549398102c0d91b1b9919b2f20558aefdadf57528a95c6cd3292e9360405160405180910390a27f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff1663a9059cbb33866040518363ffffffff1660e01b8152600401808373ffffffffffffffffffffffffffffffffffffffff16815260200182815260200192505050602060405180830381600087803b1580156125fb57600080fd5b505af115801561260f573d6000803e3d6000fd5b505050506040513d602081101561262557600080fd5b8101908080519060200190929190505050505050505050565b600360009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614612701576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f4d7573742062652070726f706f736564206f776e65720000000000000000000081525060200191505060405180910390fd5b6000600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905033600260006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506000600360006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055503373ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff167f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e060405160405180910390a350565b6000600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905090565b600061283c613647565b8380612846613c0c565b101561289d576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260358152602001806142c16035913960400191505060405180910390fd5b7f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff16634000aea0878787876040518563ffffffff1660e01b8152600401808573ffffffffffffffffffffffffffffffffffffffff168152602001848152602001806020018281038252848482818152602001925080828437600081840152601f19601f82011690508083019250505095505050505050602060405180830381600087803b15801561296257600080fd5b505af1158015612976573d6000803e3d6000fd5b505050506040513d602081101561298c57600080fd5b8101908080519060200190929190505050915050949350505050565b6129b0611410565b73ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614612a50576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260138152602001807f4d75737420757365204c494e4b20746f6b656e0000000000000000000000000081525060200191505060405180910390fd5b80600060208201519050612a648183613e0d565b84602484015283604484015260003073ffffffffffffffffffffffffffffffffffffffff16846040518082805190602001908083835b60208310612abd5780518252602082019150602081019050602083039250612a9a565b6001836020036101000a038019825116818451168082178552505050505050905001915050600060405180830381855af49150503d8060008114612b1d576040519150601f19603f3d011682016040523d82523d6000602084013e612b22565b606091505b5050905080612b99576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260188152602001807f556e61626c6520746f206372656174652072657175657374000000000000000081525060200191505060405180910390fd5b505050505050565b60003385604051602001808373ffffffffffffffffffffffffffffffffffffffff1660601b8152601401828152602001925050506040516020818303038152906040528051906020012090506000612bfb85338686613d8a565b90508060ff19166004600084815260200190815260200160002060000160009054906101000a900460081b60ff191614612c9d576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601e8152602001807f506172616d7320646f206e6f74206d617463682072657175657374204944000081525060200191505060405180910390fd5b42831115612d13576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f52657175657374206973206e6f7420657870697265640000000000000000000081525060200191505060405180910390fd5b60046000838152602001908152602001600020600080820160006101000a8154907effffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff021916905560008201601f6101000a81549060ff02191690555050817fa7842b9ec549398102c0d91b1b9919b2f20558aefdadf57528a95c6cd3292e9360405160405180910390a27f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff1663a9059cbb33876040518363ffffffff1660e01b8152600401808373ffffffffffffffffffffffffffffffffffffffff16815260200182815260200192505050602060405180830381600087803b158015612e2d57600080fd5b505af1158015612e41573d6000803e3d6000fd5b505050506040513d6020811015612e5757600080fd5b810190808051906020019092919050505050505050505050565b612e796135fa565b612eeb576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601d8152602001807f43616e6e6f742073657420617574686f72697a65642073656e6465727300000081525060200191505060405180910390fd5b60008282905011612f64576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f4d7573742068617665206174206c6561737420312073656e646572000000000081525060200191505060405180910390fd5b6000600180549050905060005b8181101561301457600080600060018481548110612f8b57fe5b9060005260206000200160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff0219169083151502179055508080600101915050612f71565b5060005b8383905081101561319c576000151560008086868581811061303657fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff16151514613110576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601f8152602001807f4d757374206e6f742068617665206475706c69636174652073656e646572730081525060200191505060405180910390fd5b600160008086868581811061312157fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff0219169083151502179055508080600101915050613018565b508282600191906131ae929190614203565b507ff263cfb3e4298332e776194610cf9fdc09ccb3ada8b9aa39764d882e11fbf0a083833360405180806020018373ffffffffffffffffffffffffffffffffffffffff1681526020018281038252858582818152602001925060200280828437600081840152601f19601f82011690508083019250505094505050505060405180910390a1505050565b613240613647565b61324981613f98565b50565b613254613647565b808061325e613c0c565b10156132b5576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260358152602001806142c16035913960400191505060405180910390fd5b7f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff1663a9059cbb84846040518363ffffffff1660e01b8152600401808373ffffffffffffffffffffffffffffffffffffffff16815260200182815260200192505050602060405180830381600087803b15801561334657600080fd5b505af115801561335a573d6000803e3d6000fd5b505050506040513d602081101561337057600080fd5b810190808051906020019092919050505061338757fe5b505050565b60008060008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff169050919050565b6133e96135fa565b61345b576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601d8152602001807f43616e6e6f742073657420617574686f72697a65642073656e6465727300000081525060200191505060405180910390fd5b7f1bb185903e2cb2f1b303523128b60e314dea81df4f8d9b7351cadd344f6e772784848484336040518080602001806020018473ffffffffffffffffffffffffffffffffffffffff1681526020018381038352888882818152602001925060200280828437600081840152601f19601f8201169050808301925050508381038252868682818152602001925060200280828437600081840152601f19601f82011690508083019250505097505050505050505060405180910390a160005b848490508110156135f35784848281811061353057fe5b9050602002013573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1663ee56997b84846040518363ffffffff1660e01b815260040180806020018281038252848482818152602001925060200280828437600081840152601f19601f8201169050808301925050509350505050600060405180830381600087803b1580156135ce57600080fd5b505af11580156135e2573d6000803e3d6000fd5b505050508080600101915050613519565b5050505050565b60006136053361338c565b8061364257503373ffffffffffffffffffffffffffffffffffffffff1661362a612808565b73ffffffffffffffffffffffffffffffffffffffff16145b905090565b600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff161461370a576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f4f6e6c792063616c6c61626c65206279206f776e65720000000000000000000081525060200191505060405180910390fd5b565b600080823b905060008111915050919050565b600080857f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614156137e5576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260138152602001807f43616e6e6f742063616c6c20746f204c494e4b0000000000000000000000000081525060200191505060405180910390fd5b8885604051602001808373ffffffffffffffffffffffffffffffffffffffff1660601b815260140182815260200192505050604051602081830303815290604052805190602001209250600060081b6004600085815260200190815260200160002060000160009054906101000a900460081b60ff1916146138cf576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260148152602001807f4d75737420757365206120756e6971756520494400000000000000000000000081525060200191505060405180910390fd5b6138e461012c426140fa90919063ffffffff16565b915060006138f489898986613d8a565b905060405180604001604052808260ff1916815260200161391487614182565b60ff168152506004600086815260200190815260200160002060008201518160000160006101000a8154817effffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff021916908360081c0217905550602082015181600001601f6101000a81548160ff021916908360ff1602179055509050506139a5896006546140fa90919063ffffffff16565b6006819055505050965096945050505050565b6139c13361338c565b613a33576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260158152602001807f4e6f7420617574686f72697a65642073656e646572000000000000000000000081525060200191505060405180910390fd5b565b6000613a4386868686613d8a565b90508060ff19166004600089815260200190815260200160002060000160009054906101000a900460081b60ff191614613ae5576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601e8152602001807f506172616d7320646f206e6f74206d617463682072657175657374204944000081525060200191505060405180910390fd5b613aee82614182565b60ff1660046000898152602001908152602001600020600001601f9054906101000a900460ff1660ff161115613b8c576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260188152602001807f446174612076657273696f6e73206d757374206d61746368000000000000000081525060200191505060405180910390fd5b613ba186600654613d0190919063ffffffff16565b60068190555060046000888152602001908152602001600020600080820160006101000a8154907effffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff021916905560008201601f6101000a81549060ff0219169055505050505050505050565b600080613c256001600654613d0190919063ffffffff16565b9050613cfb817f000000000000000000000000000000000000000000000000000000000000000073ffffffffffffffffffffffffffffffffffffffff166370a08231306040518263ffffffff1660e01b8152600401808273ffffffffffffffffffffffffffffffffffffffff16815260200191505060206040518083038186803b158015613cb257600080fd5b505afa158015613cc6573d6000803e3d6000fd5b505050506040513d6020811015613cdc57600080fd5b8101908080519060200190929190505050613d0190919063ffffffff16565b91505090565b600082821115613d79576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601e8152602001807f536166654d6174683a207375627472616374696f6e206f766572666c6f77000081525060200191505060405180910390fd5b600082840390508091505092915050565b600084848484604051602001808581526020018473ffffffffffffffffffffffffffffffffffffffff1660601b8152601401837bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19168152600401828152602001945050505050604051602081830303815290604052805190602001209050949350505050565b600260200260040181511015613e8b576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f496e76616c69642072657175657374206c656e6774680000000000000000000081525060200191505060405180910390fd5b633c6d41b960e01b7bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916827bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19161480613f225750634042994660e01b7bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916827bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916145b613f94576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601e8152602001807f4d757374207573652077686974656c69737465642066756e6374696f6e73000081525060200191505060405180910390fd5b5050565b3373ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff16141561403a576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260178152602001807f43616e6e6f74207472616e7366657220746f2073656c6600000000000000000081525060200191505060405180910390fd5b80600360006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508073ffffffffffffffffffffffffffffffffffffffff16600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff167fed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae127860405160405180910390a350565b600080828401905083811015614178576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f536166654d6174683a206164646974696f6e206f766572666c6f77000000000081525060200191505060405180910390fd5b8091505092915050565b600061010082106141fb576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825260168152602001807f6e756d62657220746f6f2062696720746f20636173740000000000000000000081525060200191505060405180910390fd5b819050919050565b828054828255906000526020600020908101928215614292579160200282015b8281111561429157823573ffffffffffffffffffffffffffffffffffffffff168260006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555091602001919060010190614223565b5b50905061429f91906142a3565b5090565b5b808211156142bc5760008160009055506001016142a4565b509056fe416d6f756e74207265717565737465642069732067726561746572207468616e20776974686472617761626c652062616c616e6365a26469706673582212204307508538a95775881674e5234c7fc6a641aabfbf7f606605ae466b565ea5de64736f6c63430007060033
"""

