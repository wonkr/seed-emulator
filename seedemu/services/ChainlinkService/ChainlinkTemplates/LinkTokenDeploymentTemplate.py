from typing import Dict

LinkTokenDeploymentTemplate: Dict[str, str] = {}

LinkTokenDeploymentTemplate['link_token_contract'] = '''\
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}/getEth"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)
    
logging.info("Successfully connected to the Ethereum node.")

new_account = web3.eth.account.create()
account_address = new_account.address
private_key = new_account.privateKey.hex()

data = {{"new_account": account_address}}
response = requests.post(faucet_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
if response.status_code != 200:
	logging.error(f"Failed to request funds from faucet: {{response.text}}")
	exit()

check_interval = 10

def is_address_funded(address):
    balance = web3.eth.get_balance(address)
    return balance > 0

while True:
	if is_address_funded(account_address):
		logging.info(f"Address funded: {{account_address}}")
		break
	else:
		logging.info(f"Waiting for address to be funded: {{account_address}}")
		time.sleep(check_interval)

with open('./contracts/link_token.abi', 'r') as abi_file:
	contract_abi = abi_file.read()
with open('./contracts/link_token.bin', 'r') as bin_file:
	contract_bytecode = bin_file.read().strip()

link_token_contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

account = web3.eth.account.from_key(private_key)
nonce = web3.eth.get_transaction_count(account.address)

transaction = link_token_contract.constructor().buildTransaction({{
	'from': account.address,
	'nonce': nonce,
	'gas': 2000000,
	'gasPrice': web3.eth.gas_price,
	'chainId': {chain_id}
}})

signed_txn = web3.eth.account.sign_transaction(transaction, private_key)

tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

print(f"Link Token Contract deployed at address: {{tx_receipt.contractAddress}}")

directory = './deployed_contracts'

if not os.path.exists(directory):
    os.makedirs(directory)

with open('./deployed_contracts/link_token_address.txt', 'w') as address_file:
	address_file.write(tx_receipt.contractAddress)

with open('./deployed_contracts/sender_account.txt', 'w') as account_file:
	account_file.write(f"Address: {{account_address}}\\nPrivate Key: {{private_key}}")
'''
    
LinkTokenDeploymentTemplate['link_token_abi'] = """\
[
	{
		"constant": false,
		"inputs": [
			{
				"name": "_spender",
				"type": "address"
			},
			{
				"name": "_value",
				"type": "uint256"
			}
		],
		"name": "approve",
		"outputs": [
			{
				"name": "",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_amount",
				"type": "uint256"
			}
		],
		"name": "claimTokens",
		"outputs": [],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_spender",
				"type": "address"
			},
			{
				"name": "_subtractedValue",
				"type": "uint256"
			}
		],
		"name": "decreaseApproval",
		"outputs": [
			{
				"name": "success",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_spender",
				"type": "address"
			},
			{
				"name": "_addedValue",
				"type": "uint256"
			}
		],
		"name": "increaseApproval",
		"outputs": [
			{
				"name": "success",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_to",
				"type": "address"
			},
			{
				"name": "_value",
				"type": "uint256"
			}
		],
		"name": "transfer",
		"outputs": [
			{
				"name": "success",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"name": "from",
				"type": "address"
			},
			{
				"indexed": true,
				"name": "to",
				"type": "address"
			},
			{
				"indexed": false,
				"name": "value",
				"type": "uint256"
			},
			{
				"indexed": false,
				"name": "data",
				"type": "bytes"
			}
		],
		"name": "Transfer",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"name": "owner",
				"type": "address"
			},
			{
				"indexed": true,
				"name": "spender",
				"type": "address"
			},
			{
				"indexed": false,
				"name": "value",
				"type": "uint256"
			}
		],
		"name": "Approval",
		"type": "event"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_to",
				"type": "address"
			},
			{
				"name": "_value",
				"type": "uint256"
			},
			{
				"name": "_data",
				"type": "bytes"
			}
		],
		"name": "transferAndCall",
		"outputs": [
			{
				"name": "success",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"constant": false,
		"inputs": [
			{
				"name": "_from",
				"type": "address"
			},
			{
				"name": "_to",
				"type": "address"
			},
			{
				"name": "_value",
				"type": "uint256"
			}
		],
		"name": "transferFrom",
		"outputs": [
			{
				"name": "",
				"type": "bool"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "nonpayable"
	},
	{
		"payable": true,
		"type": "fallback",
		"stateMutability": "payable"
	},
	{
		"inputs": [],
		"payable": false,
		"type": "constructor",
		"stateMutability": "nonpayable"
	},
	{
		"constant": true,
		"inputs": [
			{
				"name": "_owner",
				"type": "address"
			},
			{
				"name": "_spender",
				"type": "address"
			}
		],
		"name": "allowance",
		"outputs": [
			{
				"name": "remaining",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [
			{
				"name": "_owner",
				"type": "address"
			}
		],
		"name": "balanceOf",
		"outputs": [
			{
				"name": "balance",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "creatorInitialBalance",
		"outputs": [
			{
				"name": "",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "decimals",
		"outputs": [
			{
				"name": "",
				"type": "uint8"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "name",
		"outputs": [
			{
				"name": "",
				"type": "string"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "poolBalance",
		"outputs": [
			{
				"name": "",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "symbol",
		"outputs": [
			{
				"name": "",
				"type": "string"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "tokenDistributionAmount",
		"outputs": [
			{
				"name": "",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	},
	{
		"constant": true,
		"inputs": [],
		"name": "totalSupply",
		"outputs": [
			{
				"name": "",
				"type": "uint256"
			}
		],
		"payable": false,
		"type": "function",
		"stateMutability": "view"
	}
]
"""

LinkTokenDeploymentTemplate['link_token_bin'] = """\
6060604052341561000c57fe5b5b6000601260ff16600a0a6103e802600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002081905550601260ff16600a0a6103e8026b033b2e3c9fd0803ce800000003905080600160003073ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002081905550806003819055505b505b611800806100d76000396000f300606060405236156100e4576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806306fdde03146101b3578063095ea7b31461024c57806318160ddd146102a357806323b872dd146102c9578063313ce5671461033f5780634000aea01461036b57806346e04a2f1461040557806366188463146104255780636a98cc7b1461047c57806370a08231146104a257806395d89b41146104ec57806396365d4414610585578063a9059cbb146105ab578063d73dd62314610602578063dd62ed3e14610659578063ef334d0c146106c2575b6101b15b6000601260ff16600a0a6101f40290508060036000828254039250508190555080600160003073ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055506101ac33826106e8565b505b50565b005b34156101bb57fe5b6101c3610775565b6040518080602001828103825283818151815260200191508051906020019080838360008314610212575b805182526020831115610212576020820191506020810190506020830392506101ee565b505050905090810190601f16801561023e5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561025457fe5b610289600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919080359060200190919050506107af565b604051808215151515815260200191505060405180910390f35b34156102ab57fe5b6102b361083c565b6040518082815260200191505060405180910390f35b34156102d157fe5b610325600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190505061084c565b604051808215151515815260200191505060405180910390f35b341561034757fe5b61034f6108db565b604051808260ff1660ff16815260200191505060405180910390f35b341561037357fe5b6103eb600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190803590602001908201803590602001908080601f016020809104026020016040519081016040528093929190818152602001838380828437820191505050505050919050506108e0565b604051808215151515815260200191505060405180910390f35b341561040d57fe5b610423600480803590602001909190505061096f565b005b341561042d57fe5b610462600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091908035906020019091905050610a3a565b604051808215151515815260200191505060405180910390f35b341561048457fe5b61048c610ccd565b6040518082815260200191505060405180910390f35b34156104aa57fe5b6104d6600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610cdc565b6040518082815260200191505060405180910390f35b34156104f457fe5b6104fc610d26565b604051808060200182810382528381815181526020019150805190602001908083836000831461054b575b80518252602083111561054b57602082019150602081019050602083039250610527565b505050905090810190601f1680156105775780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561058d57fe5b610595610d60565b6040518082815260200191505060405180910390f35b34156105b357fe5b6105e8600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919080359060200190919050506106e8565b604051808215151515815260200191505060405180910390f35b341561060a57fe5b61063f600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091908035906020019091905050610d66565b604051808215151515815260200191505060405180910390f35b341561066157fe5b6106ac600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610f63565b6040518082815260200191505060405180910390f35b34156106ca57fe5b6106d2610feb565b6040518082815260200191505060405180910390f35b600082600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff161415801561075457503073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614155b15156107605760006000fd5b61076a8484610ffa565b91505b5b5092915050565b604060405190810160405280600f81526020017f436861696e4c696e6b20546f6b656e000000000000000000000000000000000081525081565b600082600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff161415801561081b57503073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614155b15156108275760006000fd5b6108318484611196565b91505b5b5092915050565b6b033b2e3c9fd0803ce800000081565b600082600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff16141580156108b857503073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614155b15156108c45760006000fd5b6108cf858585611289565b91505b5b509392505050565b601281565b600083600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff161415801561094c57503073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1614155b15156109585760006000fd5b61096385858561153b565b91505b5b509392505050565b80600354101515156109815760006000fd5b8060036000828254039250508190555080600160003073ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282540192505081905550610a3533826106e8565b505b50565b60006000600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054905080831115610b4c576000600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002081905550610be0565b610b5f838261164e90919063ffffffff16565b600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055505b8373ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008873ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020546040518082815260200191505060405180910390a3600191505b5092915050565b601260ff16600a0a6101f40281565b6000600160008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205490505b919050565b604060405190810160405280600481526020017f4c494e4b0000000000000000000000000000000000000000000000000000000081525081565b60035481565b6000610df782600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461166890919063ffffffff16565b600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020546040518082815260200191505060405180910390a3600190505b92915050565b6000600260008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205490505b92915050565b601260ff16600a0a6103e80281565b600061104e82600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461164e90919063ffffffff16565b600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055506110e382600160008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461166890919063ffffffff16565b600160008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef846040518082815260200191505060405180910390a3600190505b92915050565b600081600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925846040518082815260200191505060405180910390a3600190505b92915050565b60006000600260008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054905061135e83600160008873ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461164e90919063ffffffff16565b600160008773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055506113f383600160008773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461166890919063ffffffff16565b600160008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002081905550611449838261164e90919063ffffffff16565b600260008773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508373ffffffffffffffffffffffffffffffffffffffff168573ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef856040518082815260200191505060405180910390a3600191505b509392505050565b60006115478484610ffa565b508373ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16858560405180838152602001806020018281038252838181518152602001915080519060200190808383600083146115ee575b8051825260208311156115ee576020820191506020810190506020830392506115ca565b505050905090810190601f16801561161a5780820380516001836020036101000a031916815260200191505b50935050505060405180910390a361163184611688565b156116425761164184848461169d565b5b600190505b9392505050565b600082821115151561165c57fe5b81830390505b92915050565b60006000828401905083811015151561167d57fe5b8091505b5092915050565b60006000823b90506000811191505b50919050565b60008390508073ffffffffffffffffffffffffffffffffffffffff1663a4c0ed363385856040518463ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200183815260200180602001828103825283818151815260200191508051906020019080838360008314611773575b8051825260208311156117735760208201915060208101905060208303925061174f565b505050905090810190601f16801561179f5780820380516001836020036101000a031916815260200191505b50945050505050600060405180830381600087803b15156117bc57fe5b6102c65a03f115156117ca57fe5b5050505b505050505600a165627a7a72305820fb16383a93430b1799f1da5608f6486e8bfe369cd14c034a20a0d00234c223320029
"""

