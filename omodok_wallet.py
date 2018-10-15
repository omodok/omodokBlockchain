# -*- coding: utf-8 -*-

from ecdsa import SigningKey,SECP256k1
import codecs
import hashlib
import base58
import json
import os

#####秘密鍵の生成関数
def private_keyFn():
    #ECDSAから署名鍵オブジェクトを作成
    signing_key = SigningKey.generate(curve = SECP256k1) # uses SECP256k1    
    #署名鍵オブジェクトから秘密鍵を作成して戻り値へ
    return  signing_key.to_string()  # 256ビット = 32バイト  x 8ビット（1バイト）

####ECDSA公開鍵の生成関数
def public_keyFn(private_key):
    #楕円曲線パラメータにSECP256k1を指定
    signing_key = SigningKey.from_string(private_key, curve=SECP256k1)
    verifying_key = signing_key.verifying_key
    return verifying_key.to_string()

#####公開鍵からbitcoinアドレスを作成
#チェックサム作成関数定義
def checksumFn(data):
    code = hashlib.sha256(hashlib.sha256(data).digest()).digest()
    return code[:4]

def addressFn(public_key):
    pk_with_prefix = b"\x04" + public_key
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(hashlib.sha256(pk_with_prefix).digest())
    hash160 = ripemd160.digest()
    vhash160 = b"\x00" + hash160  # bitcoin:\x00,TestNet:\x6F
    checksum = checksumFn(vhash160)
    raw_address = vhash160 + checksum
    return base58.b58encode(raw_address)

#####保存用連想配列の作成関数
def bin2hexFn(private_key, public_key):
    private_key_16 = codecs.encode(private_key,"hex_codec").decode("utf-8")
    public_key_16 = codecs.encode(public_key,"hex_codec").decode("utf-8")
    address_58 = addressFn(public_key).decode("utf-8")
    
    dumpValue = {"private_key":private_key_16,
                 "public_key":public_key_16,
                 "address":address_58}
    return dumpValue

#####「秘密鍵・公開鍵・アドレス」の保存
def wallet_save(dumpValue,walletFile):    
    f = open(walletFile, 'w')
    json.dump(dumpValue,f)
    f.close()

#####新規ウォレット作成   
def new_wallet(walletFile):
    private_key = private_keyFn()
    public_key = public_keyFn(private_key)
    dumpValue = bin2hexFn(private_key, public_key)
    wallet_save(dumpValue,walletFile)
    return dumpValue
    
#####ウォレットの取得
def Wallet(walletFile):
    if os.path.exists(walletFile):
        f = open(walletFile)
        loadValue = json.load(f)
        f.close()
    else:
        loadValue = new_wallet(walletFile)
    return loadValue

if __name__ == '__main__':    
    walletFile = "Asan.json"
    loadValue = Wallet(walletFile)
    print("読み込んだファイル内の3データ")
    print (loadValue["private_key"].encode("utf-8"))
    print()
    print (loadValue["public_key"].encode("utf-8"))
    print()
    print (loadValue["address"].encode("utf-8"))
    print()