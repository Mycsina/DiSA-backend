import json
import os

import web3
from cryptography.hazmat.primitives import hashes
from dotenv import load_dotenv


class BlockchainService:
    def __init__(self, abi_location="utils/abi.json"):

        load_dotenv()
        with open(abi_location) as f:
            abi = json.load(f)

        self.w3 = web3.Web3(web3.Web3.HTTPProvider(os.environ.get("NODE_URL")))
        self.contract = self.w3.eth.contract(abi=abi, address=os.environ.get("CONTRACT_ADDRESS"))
        self.account = self.w3.eth.account.from_key(os.environ.get("PRIVATE_KEY"))

    def to_hash(self, manifest: bytes) -> bytes:
        """
        hashes one or more files with sha256
        files: list of bytes arrays (each representing a file)
        """
        digest = hashes.Hash(hashes.SHA256())
        digest.update(manifest)
        return digest.finalize()

    def save_contract(self, originalHash, processedHash, url):
        private_key = os.environ.get("PRIVATE_KEY")
        function_name = "storeCertificate"
        function_args = [originalHash, processedHash, url]

        estimated_gas = self.contract.functions[function_name](*function_args).estimateGas(
            {"from": self.account.address}
        )

        txn = self.contract.functions[function_name](*function_args).buildTransaction(
            {
                "from": self.account.address,
                "gas": estimated_gas,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_transaction(signed_txn)
        return tx_hash

    def get_transaction_receipt(self, tx_hash: str, timeout=120) -> dict:
        """
        waits for the transaction to be included in a block
        see https://web3py.readthedocs.io/en/stable/web3.eth.html#web3.eth.Eth.wait_for_transaction_receipt for receipt contents
        raises:
            web3.exceptions.TimeExhausted: timeout elapsed
        """
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    def get_manifest_hash(self, receipt: dict) -> str:
        """
        returns the stored manifest hash, given the transaction's receipt
        raises:
            keyError: either there were no storeHash event (or it didn't have the originalHash argument)
        """
        event_logs = self.contract.events.hashStored().process_receipt(receipt)

        if event_logs and len(event_logs) >= 1:
            return event_logs[0]["args"]["originalHash"]
        else:
            raise KeyError("no matching event found")

    def get_certificate_args(self, receipt: dict) -> dict:
        """
        returns the originalHash, processedHash and url from the certificate, given the transaction's receipt
        raises:
            keyError: no valid event found
        """
        event_logs = self.contract.events.certificateStored().process_receipt(receipt)

        if event_logs and len(event_logs) >= 1:
            return event_logs[0]["args"]
        else:
            raise KeyError("no matching event found")

    def get_block_timestamp(self, receipt: dict) -> int:
        """
        returns the timestamp in which the transaction was inserted on the block
        raises:
            web3.exceptions.BlockNotFoundError: block on the receipt wasn't found
            keyError: invalid receipt (or invalid block)
        """
        blockNumber = receipt["blockNumber"]
        return self.w3.eth.get_block(blockNumber)["timestamp"]
