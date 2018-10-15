# -*- coding: utf-8 -*-
from omodok_blockchain_api import *
from flask_sockets import Sockets
from gevent import pywsgi,sleep
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError
from websocket import create_connection
import asyncio
from threading import Thread

sockets = Sockets(app)

#WSのセット配列
ws_list = set() 
ip_dict = {}

#WSCのセット配列
wsc_list = set() 
ipc_dict = {}
#ブロードキャスト送信管理
bcSoushin = set()

#これより関数定義文
def ws_add_txFn(newTx):
    global this_transactions
    
    for i in range(0,len(this_transactions)):
        if this_transactions[i]["sender"]==newTx['sender']:
            print("warning: この送信元はすでに受付中です。")
            return

    new_transaction = OD(newTx)
    new_transaction["amount"] = int(new_transaction["amount"])
        
    if P2PKHFn(new_transaction):
        this_transactions.append(new_transaction)
        print("ここまでOK-TX",new_transaction["sender"])
@app.route('/shutdown', methods=['GET'])
def shutdownFn():
    for s in ws_list:
        s.close()
    for s in wsc_list:
        s.close()
    dumpValue = {"message":"Websocket Shutdown"}

    return jsonify(dumpValue),201

@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    global this_transactions
    get_transactions = {"transactions":this_transactions}
    return jsonify(get_transactions),201

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
    #データのダンプ
    dumpValue = {"index":new_block.index,
         "timestamp":new_block.timestamp,
         "previous_hash":new_block.previous_hash,
         "diff":new_block.diff,
         "nonce":new_block.nonce,
         "transactions":new_block.transactions,
         "current_hash":new_block.current_hash}

    return jsonify(dumpValue),201

def appendedBlockFn(msg):
    global blockcahin,this_transactions
    if msg == "Ping":
        return
    recvJson = json.loads(msg)
    print("サーバ受信3",recvJson["block"]["index"])
    index = recvJson["block"]["index"]
    timestamp = recvJson["block"]["timestamp"]
    previous_hash = recvJson["block"]["previous_hash"]
    transactions = recvJson["block"]["transactions"]
    newBlock = Block(index,timestamp,previous_hash,transactions)#インスタンス作成
    newBlock.diff =  recvJson["block"]["diff"]
    newBlock.nonce =  recvJson["block"]["nonce"]
    newBlock.current_hash =  recvJson["block"]["current_hash"]
    blockchain.append(newBlock)    #新規ブロックインスタンスの追加
    this_transactions=[]           #未承認トランザクションプールの初期化
    blockchain_save(blockchain)    #ブロックチェーンの保存
    print("新規ブロック高：",blockchain[-1].index)
    
def newNodeFn(newNode):
    global nodes
    for node in nodes:
        if node == newNode:
            print("False")
            return False
        
    nodes.add(newNode)
    t = Thread(target=threadLoop, args=(wsClientFn(newNode),))
    t.setDaemon(True)
    t.start()
    return True

@sockets.route('/ws')
def wsServerFn(ws):
    global nodes, ws_list, ip_dict,blockcahin, this_transactions
    def invServerFn():        
        #1個上の場合
        print("フォークポイント添え字-1：",len(blockchain))
        not_appended = False
        if blockchain[-1].index+1 == newIndex:
            if blockchain[-1].current_hash == recvJson["inv"][-1]["previous_hash"]:
                print("結合可能")
                ws.send(json.dumps({"getData":newIndex}))
                msg = ws.receive()
                appendedBlockFn(msg)
            else:
                not_appended = True
                       
        #2個以上の場合
        forkPoint = len(blockchain)
        if (blockchain[-1].index+1 < newIndex) or not_appended:
            for i in range(0,len(blockchain)):
                if blockchain[i].current_hash == recvJson["inv"][i]["current_hash"]:
                    continue
                else:
                    forkPoint=i
                    break

            if forkPoint < len(blockchain):
                for i in reversed(range(forkPoint,len(blockchain))):
                    blockchain.pop(i)
                
            for i in range(forkPoint,len(recvJson["inv"])):
                if blockchain[i-1].current_hash == recvJson["inv"][i]["previous_hash"]:
                    ws.send(json.dumps({"getData":recvJson["inv"][i]["index"]}))
                    msg = ws.receive()
                    appendedBlockFn(msg)
                    
        #メモリプールの初期化
        this_transactions=[] 
        print("ここまでOK-Pong")
        ws.send("Pong")    

    def broadcastServer(jsonKey, jsonValue):
        remove = set()
        ws_list2 = list(ws_list)
        for s in ws_list2:                
            sleep(1)
            if s == ws:
                #確認表示
                print ('continue!', 1)
                continue                
            try:
                print("サーバ送信",json.dumps({jsonKey:jsonValue}))
                s.send(json.dumps({jsonKey:jsonValue}))
            except Exception:
                remove.add(s)
        for s in remove:
            wsSakujoFn(s)
            
    def wsSakujoFn(s):            
        global nodes, ws_list, ip_dict
        ws_list.remove(s)
        nodes.remove(ip_dict[s])
        print("pop_ip_list:",ip_dict[s])
        ip_dict.pop(s)
        s.close()
            
    #これよりメイン定義文
    #今回WSの追加
    ws_list.add(ws)
    #確認表示
    print ('enter!', len(ws_list))
    
    #初期ハンドシェイク受信
    msg = ws.receive()
    try:
        recvJson = json.loads(msg)
    except:
        pass
    
    if recvJson.get("version")  != None:
        ws.send("verack")
        newNode = recvJson["version"]["addrme"]
        ip_dict[ws] = newNode
        if newNodeFn(newNode):
            print("add_ip_dict:",newNode)
            broadcastServer("addr",newNode)

        #サーバ側ブロック高調整
        newIndex = recvJson["version"]["BestHeight"]
        if blockchain[-1].index < newIndex:
            print("サーバ送信2",json.dumps({"getBlocks":newIndex}))        
            ws.send(json.dumps({"getBlocks":newIndex}))
            msg = ws.receive()
            recvJson = json.loads(msg)
            print("サーバ受信2",recvJson["inv"][-1]["index"])

            invServerFn()
        else:
            ws.send("Pong")
    recvJson = None
    try:
        while True:
            msg = ws.receive()
                
            try:
                recvJson = json.loads(msg)
            except:
                pass
    
            remove = set()
    
            #新規マイニングブロックの受信
            if recvJson != None and recvJson.get("tx")  != None:
                newTx = recvJson["tx"]
                ws_add_txFn(newTx)
                ws.send("Pong")
                recvJson = None               
    
            elif recvJson != None and recvJson.get("inv")  != None:
                if blockchain[-1].index < recvJson["inv"][-1]["index"]:
                    newIndex = recvJson["inv"][-1]["index"]
                    print("inv受信:",newNode)
                    invServerFn()
                    recvJson = None
    
            elif msg == "Ping":
                #print("SA>>>"+msg)
                sleep(1)
                #print("vars",vars(ws))
                print("SB>>>Pong",len(ip_dict))
                try:
                    ws.send("Pong")
                except:
                    wsSakujoFn(ws)
                    
            elif ws.close:
                wsSakujoFn(ws)
            else:
                ws.send("")
    except WebSocketError:
        wsSakujoFn(ws)
        print ("connection closed")

#WebSocketクライアント関数
async def wsClientFn(wsURL):
    global newNode, wsc_list, ipc_dict, invFlag, TxFlag, bcSoushin, nodes
        
    def broadcastClient(jsonKey, jsonValue):
        global bcSoushin,TxFlag, invFlag
        wsc.send(json.dumps({jsonKey:jsonValue}))
        bcSoushin.add(wsURL)
        if len(bcSoushin)==len(wsc_list):
            if jsonKey == "tx":
                TxFlag = False
            elif jsonKey == "inv":
                invFlag = False

            bcSoushin=set()

    def invClientFn(bh):
        inv = []
        for i in range(0,bh+1):
            inv.append({"index":blockchain[i].index,
                        "previous_hash":blockchain[i].previous_hash,
                        "current_hash":blockchain[i].current_hash})
        return inv
    
    #これよりメイン定義文
    try:
        wsc = create_connection("ws://"+wsURL+"/ws")
        #今回WSの追加
        wsc_list.add(wsc)
        ipc_dict[wsc] = wsURL
    except Exception as e:
        nodes.remove(wsURL)
        print(e)
        return

    #初回ハンドシェイク送信
    sendJson = json.dumps({"version":{"addrme":host+":"+str(port),
                           "BestHeight":blockchain[-1].index
                           }})
    wsc.send(sendJson)
    print("send version! to:", wsURL, sendJson)
    
    #初回ハンドシェイク拒否
    mes = wsc.recv()
    if mes != "verack":
        print("no handshake",mes)
        return
    else:
        print("receive verack from:",wsURL)
        
    try:
        while True:
            mes = wsc.recv()
            try:
                recvJson = json.loads(mes)
                print("クライアント受信",recvJson,wsURL)
                if recvJson.get("addr") != None:
                    newNodeFn(recvJson["addr"])
                
                #クライアント側ブロック高調整
                if recvJson.get("getBlocks") !=  None:
                    bh = recvJson["getBlocks"]
                    inv = invClientFn(bh)
                    sendJson = json.dumps({"inv":inv})
                    #print("クライアント送信",sendJson)
                    wsc.send(sendJson)
        
                if recvJson.get("getData") !=  None:
                    ch = recvJson["getData"]
                    sendJson = json.dumps({"block":{"index":blockchain[ch].index,
                    "timestamp":blockchain[ch].timestamp,
                    "previous_hash":blockchain[ch].previous_hash,
                    "diff":blockchain[ch].diff,
                    "nonce":blockchain[ch].nonce,
                    "transactions":blockchain[ch].transactions,
                    "current_hash":blockchain[ch].current_hash}})
                    #print("クライアント送信2",sendJson)
                    wsc.send(sendJson)
            except:
                pass
            
            if TxFlag and wsURL not in bcSoushin:
                tx = this_transactions[-1]
                print("TxFlag-C",TxFlag,tx["sender"])
                broadcastClient("tx",tx) 

            elif invFlag and wsURL not in bcSoushin:
                bh = blockchain[-1].index
                print("invFlag-C",invFlag,bh,wsURL)
                inv = invClientFn(bh)
                broadcastClient("inv",inv) 

            elif mes == "Pong":
                #print ("CB>>>"+mes)
                await asyncio.sleep(1)
                print("CA>>>Ping",wsURL)
                wsc.send("Ping")
            elif mes is None:
                break
            
        wsc.close()
    except (KeyboardInterrupt,Exception):
        pass
        

def threadLoop(wsFn):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(wsFn)
    
if __name__ == '__main__':
    #WebSockeクライアントのスタート
    for node in nodes:
        if node != host+":"+str(port):
            t = Thread(target=threadLoop, args=(wsClientFn(node),))
            t.setDaemon(True)
            t.start()
    #WebSockeサーバのスタート
    app.debug = True
    server = pywsgi.WSGIServer((host, port), app, handler_class=WebSocketHandler)
    server.serve_forever()

    """
    with app.app_context():
        print(PoWFn())
    """
  
