# -*- coding: utf-8 -*-
import time
from omodok_block import Block

def next_block(last_block,this_transactions):
    this_index = last_block.index + 1
    this_timestamp = round(time.time())
    last_hash = last_block.current_hash
    return Block(this_index, this_timestamp, last_hash, this_transactions)
