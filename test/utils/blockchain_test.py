from utils.BlockchainService import BlockchainService


def test_get_manifest_hash():
    bcs=BlockchainService()
    receipt=bcs.get_transaction_receipt("0xa3fccda86d68f186f02746f7b89e83ebdeb7406eb6a24e2609221de0e8ac0059")
    realHash=bcs.get_manifest_hash(receipt)
    expectedHash="testing"
    assert realHash==expectedHash

