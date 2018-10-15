# -*- coding: utf-8 -*-
import hashlib

class Block:
    def __init__(self, index, timestamp, previous_hash, transactions):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.diff = 4
        self.nonce = None
        self.transactions = transactions
        self.current_hash = self.hash_blockMe()

    def hash_blockMe(self):
        """
        ブロックのインデックス、タイムスタンプ、トランザクション、および前のブロックのハッシュのハッシュの暗号化ハッシュを生成します。
        """
        sha = hashlib.sha256()
        sha.update((str(self.index) +
                   str(self.timestamp) +
                   str(self.previous_hash) +
                   str(self.diff) +
                   str(self.transactions)).encode('utf-8'))
        return sha.hexdigest()
    
    def mining(self, add_transaction):
        nonce = 0
        self.transactions.append(add_transaction)
        self.current_hash = self.hash_blockMe()
        while True:
            nonce_joined = self.current_hash+str(nonce)
            calced = hashlib.sha256(nonce_joined.encode('utf-8')).hexdigest()
            if calced[:self.diff:].count('0') == self.diff:
                break
            nonce += 1
        return nonce