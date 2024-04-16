import json
import os

from dotenv import load_dotenv
import web3
from cryptography.hazmat.primitives import hashes

load_dotenv()

private_key = os.environ.get("PRIVATE_KEY")


class BlockchainService:
    def __init__(self, abi_location="resources/abi.json"):
        with open(abi_location) as f:
            abi = json.load(f)

        self.contract = web3.eth.contract(abi=abi, address="0x9e5c6b3d16411736c068026fc212e0b413dce243")
        self.w3 = web3.Web3(web3.Web3.HTTPProvider("https://rpc-mumbai.maticvigil.com"))
        self.account = self.w3.eth.account.from_key(private_key)

    def to_hash(self, files):
        """
        hashes one or more files with sha256
        files: list of bytes arrays (each representing a file)
        """
        digest = hashes.Hash(hashes.SHA256())
        for file in files:
            digest.update(file)
        return digest.finalize()

    def save_contract(self, originalHash, processedHash, url):
        private_key = os.environ.get("PRIVATE_KEY")
        function_name = "storeCertificate"
        function_args = [originalHash, processedHash, url]

        estimated_gas = self.contract.functions[function_name](*function_args).estimateGas(
            {"from": self.account.address}
        )

        txn = self.contract.functions[function_name](*function_args).buildTransaction(
            {"from": self.account.address, "gas": estimated_gas, "gasPrice": self.w3.eth.gas_price}
        )

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_transaction(signed_txn)
        return tx_hash

    def get_args_from_transaction(self, tx_hash, event_name="hashStored"):
        receipt = self.w3.eth.getTransactionReceipt(tx_hash)
        event_logs = self.contract.events[event_name].processReceipt(receipt)

        if event_logs:
            return event_logs[0].args
        else:
            return []
