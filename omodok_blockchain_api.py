# -*- coding: utf-8 -*-
from omodok_block import Block
from omodok_next_block import next_block
from omodok_wallet import Wallet,addressFn
from omodok_P2PKH import digitalSigFn,bin2hexOneFn,verifyFn
from urllib.parse import urlparse
from collections import OrderedDict as OD
import json
import time
import hashlib
import pickle
import os
from flask import Flask, jsonify,request,render_template
app = Flask(__name__)

#初期設定変数の初期化
fileName = 'blockchain.bin'
#メモリプール（トランザクションプール）用配列の用意
this_transactions=[]
#エラーメッセージ
tuikaError = ""
#ノードのセット配列
nodes= set(["127.0.0.1:5000"])
#invブロードキャスト
invFlag = False
#Txブロードキャスト
TxFlag = False

#IPアドレスとポート番号の取得
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
parser.add_argument('-H', '--host', default="127.0.0.1", type=str, help='host to listen on')
args = parser.parse_args()
host = args.host
port = args.port

#ウォレットの新規作成
walletFile = "port"+str(port)+".json"
loadValue = Wallet(walletFile)
private_key_u = loadValue["private_key"]
public_key_u = loadValue["public_key"]
address_u = loadValue["address"]

#ブロックチェーンの読み込み
if os.path.exists(fileName):
    f = open(fileName,'rb')     
    blockchain = pickle.load(f)
    f.close()
else:
    genesis = Block(0, 0, "", [])
    #genesis = Block(0, round(time.time()), "", [])
    blockchain = []
    
    # 送信者は、採掘者が新しいコインを採掘したことを表すために"0"とする
    add_transaction = OD([("sender", "0"),("recipient", "my address"),("amount", 1),
            ("prev_TxID",""),("public_key",""),("digital_sig",""),("TxID","")]) 
    nonce = genesis.mining(add_transaction) #マイニング処理
    genesis.nonce = nonce #取得したnonceをブロックに挿入
    nonce_joined = genesis.current_hash+str(genesis.nonce)
    calced = hashlib.sha256(nonce_joined.encode("utf-8")).hexdigest()
    genesis.current_hash = calced
    blockchain.append(genesis)

#これよりFlask関数定義文
#####ユーザインターフェース関数
@app.route('/')
def index():
	return render_template('./index.html')

@app.route('/make/transaction')
def make_transaction():
    return render_template('./make_transaction.html',
                           address_u=address_u,
                           UTXO=UTXOPoolFn(address_u),
                           NodeURL="http://"+host+":"+str(port))

@app.route('/view/transactions')
def view_transaction():
    return render_template('./view_transactions.html',
                          address_u=address_u,
                          NodeURL="http://"+host+":"+str(port))

@app.route('/index2')
def index2():
    return render_template('./index2.html')

@app.route('/configure')
def configure():
    return render_template('./configure.html')

#####peer to peer関数
@app.route('/nodes/get', methods=['GET'])
def get_nodes():
    listNodes = list(nodes)
    response = {'nodes': listNodes}
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    oneNode = request.form['oneNode']
    if oneNode=="":
        return '{ "warning": "ノードが見つかりません。" }', 406

    #URL内のIPアドレスを取得
    parsed_url = urlparse(oneNode)
    if parsed_url.netloc:
        #http://が付いていた場合
        nodes.add(parsed_url.netloc)
    elif parsed_url.path:
        #http://が付いていなかった場合
        nodes.add(parsed_url.path)
        
    #nodesの最大値を5にする
    if len(nodes)>5:
        for node in nodes:
            nodes.remove(node)
            break
        
    return '{"message": "新規ノードを追加しました。"}', 201

@app.route('/chain', methods=['GET'])
def chain():
    chain = {"chain":[]}
    for i in range(0,len(blockchain)):
        block = blockDumpFn(blockchain[i])
        chain["chain"].append(block)
    chain["chain"] = chain["chain"][::-1]
    return jsonify(chain),201

def blockDumpFn(oneBlock):
    block = {
        "index":oneBlock.index,
        "timestamp":oneBlock.timestamp,
        "previous_hash":oneBlock.previous_hash,
        "diff":oneBlock.diff,
        "transactions":oneBlock.transactions
        }
    return block
""" 
@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    global this_transactions
    get_transactions = {"transactions":this_transactions}
    return jsonify(get_transactions),201
"""
"""
@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    global this_transactions, TxFlag
    
    new_transaction = OD(request.form)
    new_transaction["amount"] = int(new_transaction["amount"])
    
    if P2PKHFn(new_transaction):
        this_transactions.append(new_transaction)
        #TXのブロードキャスト
        TxFlag = True
        return jsonify(new_transaction),201
    else:
        return '{ "warning": "このトランザクションは無効です。'+tuikaError+'" }', 406
"""

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    global this_transactions
    #データ不備のエラー処理
    if request.form['sender_add'] != address_u :
        return '{ "warning": "送信元が異なります。" }', 406
    if request.form['recipient_add'] == "" or request.form['amt'] == "":
        return '{ "warning": "データが不足です。" }', 406
    if int(request.form['amt']) != UTXOPoolFn(address_u):
        return '{ "warning": "金額が異なります。" }', 406
    for i in range(0,len(this_transactions)):
        if this_transactions[i]["sender"]==request.form['sender_add']:
            return '{ "warning": "この送信元はすでに受付中です。" }', 406

    new_transaction = OD([("sender", request.form['sender_add']),
                       ("recipient", request.form['recipient_add']), 
                       ("amount", int(request.form['amt']))])
    """
    new_transaction = OD([("sender", "1DCtpKZebwxmtJQZBt1rLZ9AqoAL2BXsKs"),
                       ("recipient", "1DCtpKZebwxmtJQZBt1rLZ9AqoAL2BXsKs"), 
                       ("amount",3 )])
    """
    new_transaction = TxMetaDataFn(new_transaction)
    
    return jsonify(new_transaction),201

def P2PKHFn(new_transaction):
    global tuikaError
    #ロック解除したUTXOとロックするUTXOが異なる場合はFalse
    if new_transaction["amount"] != UTXOPoolFn(new_transaction["sender"]):
        tuikaError="入金と出金の金額が合いません。"
        return False
    
    #前回トランザクションから送金先アドレスを取得
    prev_TxID = new_transaction["prev_TxID"]
    prev_recipient_u =""
    for i in range(0,len(blockchain)):
        for i2 in range(0,len(blockchain[i].transactions)):
            if blockchain[i].transactions[i2]["TxID"] == prev_TxID:
                prev_recipient_u = blockchain[i].transactions[i2]["recipient"]

    #取り出したUnicode型送金アドレスを生バイト列に変換
    prev_recipient_b = prev_recipient_u.encode("utf-8")

    #今回の「公開鍵」をUnico型から生バイト列に変換
    check_public_key_u = new_transaction["public_key"]
    check_public_key = bytes.fromhex(check_public_key_u)
    
    #生バイト列「公開鍵」から「公開鍵ハッシュ（アドレス）」を作成
    check_address_b = addressFn(check_public_key)

    if check_address_b != prev_recipient_b:
        tuikaError="入金確認が取れませんでした。"
        return False
    
    #「デジタル署名」16進数数字の取得と生バイト列化
    digital_sig_u = new_transaction["digital_sig"]
    digital_sig = bytes.fromhex(digital_sig_u)
    
    #検証用トランザクションの再作成
    check_Tx = OD([("sender", new_transaction["sender"]),
                   ("recipient", new_transaction["recipient"]),
                   ("amount", new_transaction["amount"]),
                   ("prev_TxID",new_transaction["prev_TxID"]),
                   ("public_key",new_transaction["public_key"]),
                   ("digital_sig",""),
                   ("TxID","")])
    #トランザクション連想配列のUnicode文字列化
    check_Tx_u = json.dumps(check_Tx)
    #Unicode文字列のバイト文字列化
    check_Tx_b = check_Tx_u.encode("utf-8")
    #「デジタル署名」の検証    
    try:
        kekka = verifyFn(digital_sig, check_public_key, check_Tx_b)
        if kekka:
            return True
    except :
        tuikaError="本人確認が取れませんでした。"
        return False

"""    
@app.route('/PoW', methods=['GET'])
def PoWFn():
    global blockchain,this_transactions,invFlag
    new_block = next_block(blockchain[-1],this_transactions)
    # 送信者は、採掘者が新しいコインを採掘したことを表すために"0"とする
    add_transaction = OD([("sender", "0"),("recipient", address_u),("amount", 1)]) 
    
    #トランザクションメタデータの作成
    add_transaction = TxMetaDataFn(add_transaction)
    
    nonce = new_block.mining(add_transaction) #マイニング処理
    #メモリプールの初期化
    this_transactions=[] 
    new_block.nonce = nonce #取得したnonceをブロックに挿入
    nonce_joined = new_block.current_hash+str(new_block.nonce)
    calced = hashlib.sha256(nonce_joined.encode("utf-8")).hexdigest()
    new_block.current_hash = calced
    blockchain.append(new_block) #完成したブロックを追加します。
    #ブロックチェーンの保存
    blockchain_save(blockchain)
    #ブロックのブロードキャスト
    invFlag = True
    print("invFlag-A",invFlag)
    #データのダンプ
    dumpValue = {"index":new_block.index,
         "timestamp":new_block.timestamp,
         "previous_hash":new_block.previous_hash,
         "diff":new_block.diff,
         "nonce":new_block.nonce,
         "transactions":new_block.transactions,
         "current_hash":new_block.current_hash}

    return jsonify(dumpValue),201
"""

def TxMetaDataFn(add_transaction):
    #連想配列に「前回TxID」「公開鍵」と空の「デジタル署名」を追加
    if add_transaction["sender"]!=0:
        add_transaction["prev_TxID"] = prev_TxIDgetFn(address_u)
    else:
        add_transaction["prev_TxID"] = ""        
    add_transaction["public_key"] = public_key_u
    add_transaction["digital_sig"] = ""
    add_transaction["TxID"] = ""
    
    #トランザクション連想配列のUnicode文字列化
    add_transaction_u = json.dumps(add_transaction)
    #Unicode文字列のバイト文字列化
    add_transaction_b = add_transaction_u.encode("utf-8")
    #秘密鍵の生バイト列化
    private_key = bytes.fromhex(private_key_u)
    #秘密鍵で取引文字列をデジタル署名
    A2B_sig = digitalSigFn(add_transaction_b, private_key)
    #生バイト列のデジタル署名を16進数数字化
    A2B_sig_16 = bin2hexOneFn(A2B_sig)
    #デジタル署名のUnicode化
    A2B_sig_u = A2B_sig_16.decode("utf-8")
    #連想配列に「デジタル署名」を追加
    add_transaction["digital_sig"] = A2B_sig_u
    
    #連想配列を直列化
    add_transaction_u = json.dumps(add_transaction)
    #全体をハッシュ化してTxIDとする
    sha = hashlib.sha256()
    sha.update(add_transaction_u.encode("utf-8"))
    #ハッシュを連想配列に追加
    add_transaction["TxID"] = sha.hexdigest()

    return add_transaction

@app.route('/Wallet', methods=['GET'])
def WalletFn():
    loadValue["UTXO"] = UTXOPoolFn(address_u)
    return jsonify(loadValue)

def UTXOPoolFn(address_u):
    UTXO=0
    for i in range(0,len(blockchain)):
        for i2 in range(0,len(blockchain[i].transactions)):
            if blockchain[i].transactions[i2]["recipient"]==address_u:
                UTXO += blockchain[i].transactions[i2]["amount"]
            if blockchain[i].transactions[i2]["sender"]==address_u:
                UTXO -= blockchain[i].transactions[i2]["amount"]
    return UTXO

def prev_TxIDgetFn(address_u):
    prev_TxID = ""
    for i in range(0,len(blockchain)):
        for i2 in range(0,len(blockchain[i].transactions)):
            if blockchain[i].transactions[i2]["recipient"]==address_u:
                prev_TxID = blockchain[i].transactions[i2]["TxID"] 
    return prev_TxID

def blockchain_save(savechain):
    f = open(fileName, 'wb')
    pickle.dump(savechain, f)
    f.close

if __name__ == '__main__':

    """
    app.run(host=host, port=port,debug=True)

    """
    with app.app_context():
        print(PoWFn())
        print("invFlag-A",invFlag)
  
