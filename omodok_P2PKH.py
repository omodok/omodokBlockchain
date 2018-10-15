# -*- coding: utf-8 -*-

from ecdsa import SigningKey,SECP256k1
import codecs
import json
from ecdsa import VerifyingKey

#####デジタル署名関数
def digitalSigFn(msg, private_key,):
	signing_key = SigningKey.from_string(private_key, curve=SECP256k1)
	return signing_key.sign(msg)

#####新規トランザクションの作成関数
def newTransactionFn(s_add, r_add,amt):
    return b'{"sender": '+s_add+b', "recipient": '+r_add+b', "amount": '+amt+b'}'

#####ブロードキャストの準備
def bin2hexOneFn(nama_bin):
    return codecs.encode(nama_bin,"hex_codec")


#「マイナー」による「検証」
#####生のバイト列化関数
def hex2binOneFn(hex_bin):
    return bytes.fromhex(hex_bin.decode("utf-8"))

#####検証関数
def verifyFn(sig, public_key, msg):
    vk = VerifyingKey.from_string(public_key, curve=SECP256k1)
    return vk.verify(sig, msg) # True

if __name__ == '__main__':
    #「秘密鍵・公開鍵・アドレス」の保存
    fileName = "Asan.json"    
    f = open(fileName)
    loadValue = json.load(f)
    f.close()   
    #読み込んだファイル内の連想配列内の2つを生バイト列、1つをbytes型
    Asan_private_key = bytes.fromhex(loadValue["private_key"])
    Asan_public_key = bytes.fromhex(loadValue["public_key"])
    Asan_address = loadValue["address"].encode("utf-8")
    
    fileName = "Bsan.json"    
    f = open(fileName)
    loadValue = json.load(f)
    f.close()    
    #読み込んだファイル内の連想配列内の2つを生バイト列、1つをbytes型
    Bsan_private_key = bytes.fromhex(loadValue["private_key"])
    Bsan_public_key = bytes.fromhex(loadValue["public_key"])
    Bsan_address = loadValue["address"].encode("utf-8")
    
    A2B_msg = newTransactionFn(Asan_address,Bsan_address, b"5")
    print("平文のメッセージ")
    print(A2B_msg)
    print()
    #デジタル署名
    A2B_sig = digitalSigFn(A2B_msg, Asan_private_key)    
    #生バイト列の16進数数字化
    A2B_sig_16 = bin2hexOneFn(A2B_sig)
    Asan_public_key_16 = bin2hexOneFn(Asan_public_key)
    #「ブロードキャスト送信」
    #16進数数字の生バイト列化
    A2B_sig = hex2binOneFn(A2B_sig_16)
    Asan_public_key = hex2binOneFn(Asan_public_key_16)
    
    kekka = verifyFn(A2B_sig, Asan_public_key, A2B_msg)
    print("検証結果")
    print(kekka)
    print()


