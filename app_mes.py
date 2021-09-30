#!/usr/bin/python
# -*- coding: utf-8 -*-
from crypt import methods
from flask import Flask, render_template, request, redirect, url_for, make_response, Response, jsonify
import json
import random as rand
import datetime
import win32com.client
import os
import pythoncom
import random as rand
from test_send_message import *
from function import *
from lxml import etree
import pandas as pd
import time
app = Flask(__name__)
app.debug = True
timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
commandid = timeNow.strftime("%Y%m%d%H%M%S")+"" + \
    '{:0>4}'.format(rand.randint(
        1, 9999))  # 將時間戳加1到9999隨機數組成commandid隨機數的格式的是四個0，例如0001、0011、0111、1111
queue_info = win32com.client.Dispatch(
    "MSMQ.MSMQQueueInfo")  # 用win32com套件和msmq傳連
user_id = ""+'{:0>4}'.format(rand.randint(1, 9999))  # 使用1到9999隨機數做爲user_id
f = open('config.json', 'r')  # 讀取config json 文件
data = json.load(f)
# ACS的Queue的名字，沒有就用挂號第二個參數代替
SendQueueName = data.get('SendQueueName', 'ACSBridgeQueue')
# MES的Queue的名字，沒有就用挂號第二個參數代替
RecvQueueName = data.get('RecvQueueName', 'MESQueue')
# MES的Queue的名字，沒有就用挂號第二個參數代替
ErrQueueName = data.get('ErrQueueName', 'MESQueue')
# ACS的Queue的IP，沒有就用挂號第二個參數代替
SendQueueIP = data.get('SendQueueIP', "tcp:192.168.0.85")
# MES的Queue的IP，沒有就用挂號第二個參數代替
RecvQueueIP = data.get('RecvQueueIP', "tcp:192.168.0.93")
# MES的Queue的IP，沒有就用挂號第二個參數代替
ErrQueueIP = data.get('ErrQueueIP', "tcp:192.168.0.93")
SendQueue = "direct=" + SendQueueIP + "\\PRIVATE$\\" + \
    SendQueueName  # ACS的Queue的路徑，沒有就用挂號第二個參數代替
RecvQueue = "direct=" + RecvQueueIP + "\\PRIVATE$\\" + \
    RecvQueueName  # MES的Queue的路徑，沒有就用挂號第二個參數代替
ErrQueue = "direct=" + ErrQueueIP + "\\PRIVATE$\\" + \
    ErrQueueName  # MES的Queue的路徑，沒有就用挂號第二個參數代替
HostName = os.getenv('COMPUTERNAME')  # MES主機的名字
Version = '1.6'  # 版本號碼
PID = '00000000'  # 隨便設定的PROCESS_ID
shelf_name_list = data.get('shelf_name_list')#讀取貨架list
shelf_port_list = data.get('shelf_port_list')#讀取貨架list_port
machine_name_list = data.get('machine_name_list')#讀取機台的name
machine_port_list = data.get('machine_port_list')#讀取機台的port
f.close()  # 關閉json讀取



def Response_headers(content):
    resp = Response(content)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


def send_msmaq(label, message):  # 發送msmq的函數第一個參數是要傳送的label，第二個參數是要傳送的message body
    queue_info.FormatName = SendQueue  # 設定要傳去mes的msmq路徑
    queue_send = None
    try:
        queue_send = queue_info.Open(2, 0)  # 發送queue參數是(2,0)

        msg = win32com.client.Dispatch("MSMQ.MSMQMessage")
        msg.Label = label  # 將label的值賦予msg.Label
        msg.Body = message  # 將message的值賦予msg.Body

        msg.Send(queue_send)  # 使用Send函數將label和body傳到acs 的 msmq
        return "msmq has  send"  # 成功傳送會回傳msmq has send
    except Exception as e:
        return "connect wrong"  # 如果acs的msmq連線有問題改爲回傳connect wrong
    finally:
        queue_send.Close()  # 關閉msmq的連線


def recv_msmq():  # 接收acs傳到mes 的 msmq的資料
    queue_info.FormatName = RecvQueue  # 設定mes的msqm資料
    queue_receive = None
    try:
        queue_receive = queue_info.Open(1, 0)  # 接收資料的參數是(1,0)
        print("i am here recv2")
        timeout_sec = 1.0  # 這個是設定要用多少秒去等待acs轉資料到mes的msmq如果超過這個時間mes的msmq還是空就回傳else的資料
        return_message = {}
        # 所設定的等待時間内恰好用資料就進入這個if
        if queue_receive.Peek(pythoncom.Empty, pythoncom.Empty, timeout_sec * 1000):
            # log.logger.debug("server has send message to client")
            msg = queue_receive.Receive()  # 使用這個函數去消費掉mes裡面第一個的msmq
            return_message["message_label"] = (msg.Label).encode(
                "utf-8")  # 將msmq分解成label,並儲存到對應的字典
            return_message["message_body"] = (msg.Body).encode(
                "utf-8")  # 將msmq分解成body，並儲存到對應的字典
            queue_receive.Close()  # 關閉讀取mes的msmq
            return return_message  # 回傳對於字典
        else:  # 如果超過特定時間mes的msmq還是空就回傳else裡面的東西
            Time2 = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")  # 可以不用理會
            # 儅mes的 msmq為空的時候設定空label給對應的字典
            return_message["message_label"] = "msmq no label"
            # 儅mes的 msmq為空的時候設定空body給對應的字典
            return_message["message_body"] = "msmq no message"
            queue_receive.Close()  # 關閉讀取mes的msmq
            return return_message  # 回傳對應的字典
    except Exception as e:  # 儅mes的msmq連線錯誤時回傳這個else裡面的東西
        print("connect error")
        # 儅mes的 msmq連線錯誤的時候設定空label給對應的字典
        return_message["message_label"] = "connect wrong"
        # 儅mes的 msmq連線錯誤的時候設定空label給對應的字典
        return_message["message_Sbody"] = "connect wrong"
        return return_message  # 回傳對應的字典
    finally:
        queue_receive.Close()  # 關閉讀取mes的msmq


@app.route('/index', methods=['GET', 'POST'])  # index的路由
def index():
    # 如果點擊STKMOVE按鈕就跳轉到stkmove_new頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'STKMOVE':
        return redirect(url_for('stkmove_new', strFunction=request.form.get('go_to')))
    # 如果點擊EQMOVE按鈕就跳轉到eqmove頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'EQMOVE':
        return redirect(url_for('eqmove', strFunction=request.form.get('go_to')))
    # 如果點擊emptycarrmove按鈕就跳轉到emptycarrmove頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'EMPTYCARRMOVE':
        return redirect(url_for('emptycarrmove', strFunction=request.form.get('go_to')))
    # 如果點擊CHANGECMD按鈕就跳轉到changecmd頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'CHANGECMD':
        return redirect(url_for('changecmd', strFunction=request.form.get('go_to')))
    # 如果點擊MOVEREQUEST按鈕就跳轉到moverequest頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'MOVEREQUEST':
        return redirect(url_for('moverequest', strFunction=request.form.get('go_to')))
    # 如果點擊INVDATA按鈕就跳轉到invdata頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'INVDATA':
        return redirect(url_for('invdata', strFunction=request.form.get('go_to')))
    # 如果點擊MOVEREQUEST按鈕就跳轉到movestatusrequest頁面和路由
    if request.method == 'POST' and request.values['go_to'] == 'MOVESTATUSREQUEST':
        return redirect(url_for('movestatusrequest', strFunction=request.form.get('go_to')))

    return render_template('index.html')


need_change_to_input_list = ["OUTSTK", "LEAVE", "ARRIVE",
                             "VALIDINPUT", "OUTEQP", "INEQP", "CARR_ALARM", "INSTK", "FOUPINFO"]  # ACS會傳到MES的function,如果是傳這些function，MES需要回應相關的function給ACS
check_need_to_send_function_list = [
    "STKMOVE", "EQMOVE", "EMPTYCARRMOVE", "CHANGECMD", "MOVEREQUEST", "INVDATA", "MOVESTATUSREQUEST"]  # MES會傳到ACS的function
need_change_to_send_function_replay_list = [
    "OUTSTK_R", "LEAVE_R", "ARRIVE_R", "VALIDINPUT_R", "OUTEQP_R", "INEQP_R", "CARR_ALARM_R", "INSTK_R", "FOUPINFO_R"]  # 儅ACS傳特定的function時mes需要回傳的function基本就是加底線_R


# stkmove_new路由
@app.route('/stkmove_new/<strFunction>', methods=['GET', 'POST'])
def stkmove_new(strFunction):
    strFROMDEVICE_list=[] #存貨架的list
    strFROMPORT_list=[] #存貨架的port
    strTODEVICE_list = []  # 存機台的list
    strTOPORT_list = machine_port_list[0].encode('utf-8') #存機台的port


    for strFROMDEVICE_list_index in range(len(shelf_name_list)):
        strFROMDEVICE_list.append((shelf_name_list[strFROMDEVICE_list_index]).encode('utf-8'))

    for strFROMPORT_list_index in range(len(shelf_port_list)):
         strFROMPORT_list.append((shelf_port_list[strFROMPORT_list_index]).encode('utf-8'))
    
    for strTODEVICE_list_index in range(len(machine_name_list)):
        strTODEVICE_list.append((machine_name_list[strTODEVICE_list_index]).encode('utf-8'))

    
    
    stk_dict = {
        "strFROMDEVICE":strFROMDEVICE_list,#貨架name_list
        "strFROMPORT":strFROMPORT_list,#貨架port
        "strFunction": strFunction,  # function
        "strCOMAND": commandid,  # 流水號
        "strFORNAME": "ACS",  # 不知道是什麽，文件就這樣設定
        "strUSERID": user_id,  # 使用者id
        "strTODEVICE": strTODEVICE_list,  # 將機台存放在stk_dict的字典,key值是strTODEVICE
        "strTOPORT":strTOPORT_list
    }
    # 以字典的形式傳給html的jinja
    return render_template('stkmove_new.html', stk_dict=stk_dict)


@app.route('/eqmove/<strFunction>', methods=['GET', 'POST'])  # eqmove路由
def eqmove(strFunction):
    strFROMDEVICE_list=[] #存機台的list 
    strFROMPORT_list=machine_port_list[0].encode('utf-8')#存機台的port
    strTODEVICE_list = [] #存貨架的list
    strTOPORT_list = [] #存貨架的port

    for strFROMDEVICE_list_index in range(len(machine_name_list)):
        strFROMDEVICE_list.append((machine_name_list[strFROMDEVICE_list_index]).encode('utf-8'))

    for strTODEVICE_list_index in range(len(shelf_name_list)):
        strTODEVICE_list.append((shelf_name_list[strTODEVICE_list_index]).encode('utf-8'))

    for strTOPORT_list_index in range(len(shelf_port_list)):
        strTOPORT_list.append((shelf_port_list[strTOPORT_list_index]).encode('utf-8'))
    stk_dict = {
        "strFunction": strFunction,  # function
        "strCOMAND": commandid,  # 流水號
        "strFORNAME": "ACS",  # 不知道是什麽，文件就是這樣設定
        "strUSERID": user_id,  # 使用者id
        "strFROMDEVICE": strFROMDEVICE_list,  # 將機台存放在stk_dict的字典,key值是strFROMDEVICE
        "strFROMPORT":strFROMPORT_list,
        "strTODEVICE":strTODEVICE_list,
        "strTOPORT":strTOPORT_list,

    }
    # 以字典的形式傳給html的jinja
    return render_template('eqmove.html', stk_dict=stk_dict)


# emptycarrmove路由
@app.route('/emptycarrmove/<strFunction>', methods=['GET', 'POST'])
def emptycarrmove(strFunction):
    strCARRIERRID_list = ["ER-A01_stock1", "ER-B01_stock1"]  # 物品名稱

    stk_dict = {
        "strFunction": strFunction,  # function
        "strCOMAND": commandid,  # 流水號
        "strFORNAME": "ACS",  # 不知道是什麽，文件就這樣設定
        "strUSERID": user_id,  # 使用者id
        "strCARRIERRID": strCARRIERRID_list,  # 將物品號存放在stk_dict的字典,key值是 strCARRIERID
    }

    # 以字典的形式傳給html的jinjia
    return render_template('emptycarrmove.html', stk_dict=stk_dict)


@app.route('/changecmd/<strFunction>', methods=['GET', 'POST'])  # changecmd路由
def changecmd(strFunction):
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    commandid = timeNow.strftime("%Y%m%d%H%M%S")+"" + \
        '{:0>4}'.format(rand.randint(
            1, 9999))  # 將時間戳加1到9999隨機數組成commandid隨機數的格式的是四個0，例如0001、0011、0111、1111
    strCARRIERRID_list = ["ER-A01_stock1", "ER-B01_stock1"]  # 物品名稱
    strFROMDEVICE_list = ["LSD002", "LSD003", "LSD004", "LSD005", "LSD022", "LSD023",
                          "LSD024", "LSD025", "LSD029", "LSD030", "LSD033",
                          "OCR01", "OCR02", "OCR03", "OCR04", "OCR05",
                          "WSD119", "WSD137", "WSD156", "WSD157", "WSD158", "WSD162", "WSD163", "WSD645"]  # 貨架名稱
    stk_dict = {
        "strFunction": strFunction,  # function
        "strCOMAND": commandid,  # 流水號
        "strFORNAME": "ACS",  # 不知道是什麽，文件就這樣設定
        "strUSERID": user_id,  # 使用者id
        "strCARRIERRID": strCARRIERRID_list,  # 將物品號存放在stk_dict的字典key值是strCARRIERID
        "strFROMDEVICE": strFROMDEVICE_list,  # 將機台存放在stk_dict的字典,key值是strFROMDEVICE
    }

    # 以字典的形式傳給html的jinjia
    return render_template('changecmd.html', stk_dict=stk_dict)


# moverequest路由
@app.route('/moverequest/<strFunction>', methods=['GET', 'POST'])
def moverequest(strFunction):
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    commandid = timeNow.strftime("%Y%m%d%H%M%S")+"" + \
        '{:0>4}'.format(rand.randint(
            1, 9999))  # 將時間戳加1到9999隨機數組成commandid隨機數的格式的是四個0，例如0001、0011、0111、1111

    strCARRIERRID_list = ["ER-A01_stock1", "ER-B01_stock1"]  # 物品名稱
    strFROMDEVICE_list = ["LSD002", "LSD003", "LSD004", "LSD005", "LSD022", "LSD023",
                          "LSD024", "LSD025", "LSD029", "LSD030", "LSD033",
                          "OCR01", "OCR02", "OCR03", "OCR04", "OCR05",
                          "WSD119", "WSD137", "WSD156", "WSD157", "WSD158", "WSD162", "WSD163", "WSD645"]  # 貨架名稱
    stk_dict = {
        "strFunction": strFunction,
        "strCOMAND": commandid,
        "strFORNAME": "ACS",
        "strUSERID": user_id,
        "strCARRIERRID": strCARRIERRID_list,
        "strFROMDEVICE": strFROMDEVICE_list,
    }

    return render_template('moverequest.html', stk_dict=stk_dict)


@app.route('/invdata/<strFunction>', methods=['GET', 'POST'])
def invdata(strFunction):
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    commandid = timeNow.strftime("%Y%m%d%H%M%S")+"" + \
        '{:0>4}'.format(rand.randint(
            1, 9999))  # 將時間戳加1到9999隨機數組成commandid隨機數的格式的是四個0，例如0001、0011、0111、1111

    stk_dict = {
        "strFunction": strFunction,
        "strCOMAND": commandid,
        "strFORNAME": "ACS",
        "strUSERID": user_id,
    }
    return render_template('invdata.html', stk_dict=stk_dict)


@app.route('/movestatusrequest/<strFunction>', methods=['GET', 'POST'])
def movestatusrequest(strFunction):
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    commandid = timeNow.strftime("%Y%m%d%H%M%S")+"" + \
        '{:0>4}'.format(rand.randint(
            1, 9999))  # 將時間戳加1到9999隨機數組成commandid隨機數的格式的是四個0，例如0001、0011、0111、1111

    strCARRIERRID_list = ["ER-A01_stock1", "ER-B01_stock1"]
    stk_dict = {
        "strFunction": strFunction,
        "strCOMAND": commandid,
        "strFORNAME": "ACS",
        "strUSERID": user_id,
        "strCARRIERRID": strCARRIERRID_list
    }
    return render_template('movestatusrequest.html', stk_dict=stk_dict)


@app.route('/send_function', methods=["GET", "POST"])
def send_function():
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式

    print("i am here send")
    send_dict = {}
    hope_dict = {
        "lunch": "burger",
    }
    send_method = (request.form.get('strMETHODNAME')).encode('utf-8')
    print(send_method)
    if(send_method == "STKMOVE"):
        print('stkmove function is send')
        STKMOVE_xml_data = STKMOVE.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERRID')).encode('utf-8')),
            FROMDEVICE=((request.form.get('strFROMDEVICE')).encode('utf-8')),
            FROMPORT=((request.form.get('strFROMPORT')).encode('utf-8')),
            TODEVICE=((request.form.get('strTODEVICE')).encode('utf-8')),
            TOPORT=((request.form.get('strTOPORT')).encode('utf-8')),
            EMPTYCARRIER=(
                (request.form.get('strEMPTYCARRIER')).encode('utf-8')),
            PRIORITY=((request.form.get('strPRIORITY')).encode('utf-8')))
        print(STKMOVE_xml_data)
        status_of_send = send_msmaq(send_method, STKMOVE_xml_data)  # here
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "STKMOVE"
        send_dict["send_message_body"] = STKMOVE_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send[1]) > 1):
                if(len(root_send[1][-1]) >= 1):
                    if(root_send[1][-1][0].text in check_need_to_send_function_list):
                        if(str(root_send[1][-1][0].text) == "STKMOVE"):
                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                            send_dict["send_FUNCTION"] = root_send[0][1].text
                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                            send_dict["send_IP"] = root_send[0][3].text
                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                            send_dict["send_PROCESS_ID"] = root_send[0][7].text
                            send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                            send_dict["send_LANG"] = root_send[0][9].text
                            send_dict["send_TIMESTAMP"] = root_send[0][10].text
                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                            send_dict["send_strUSERID"] = root_send[1][1].text
                            send_dict["send_strCARRIERID"] = root_send[1][2].text
                            send_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                            send_dict["send_strFROMDEVICE"] = root_send[1][4].text
                            send_dict["send_strFROMPORT"] = root_send[1][5].text
                            send_dict["send_strTODEVICE"] = root_send[1][6].text
                            send_dict["send_strTOPORT"] = root_send[1][7].text
                            send_dict["send_strEMPTYCARRIER"] = root_send[1][8].text
                            send_dict["send_strPRIORITY"] = root_send[1][9].text
                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                            print(result_send_data_frame)
                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_stkmove.xlsx")
                            return jsonify(send_dict)
    elif(send_method == "EQMOVE"):
        print("eqmove function is send")
        EQMOVE_xml_data = EQMOVE.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERRID')).encode('utf-8')),
            FROMDEVICE=((request.form.get('strFROMDEVICE')).encode('utf-8')),
            FROMPORT=((request.form.get('strFROMPORT')).encode('utf-8')),
            TODEVICE=((request.form.get('strTODEVICE')).encode('utf-8')),
            TOPORT=((request.form.get('strTOPORT')).encode('utf-8')),
            EMPTYCARRIER=(
                (request.form.get('strEMPTYCARRIER')).encode('utf-8')),
            PRIORITY=((request.form.get('strPRIORITY')).encode('utf-8')))
        print(EQMOVE_xml_data)
        status_of_send = send_msmaq(send_method, EQMOVE_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "EQMOVE"
        send_dict["send_message_body"] = EQMOVE_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            root_send = etree.fromstring(send_dict["send_message_body"])
            print("i am here11111111")
            if(len(root_send[1]) > 1):
                print("i am here2222222222222")
                if(len(root_send[1][-1]) >= 1):
                    print("i am here3333333333")
                    if(root_send[1][-1][0].text in check_need_to_send_function_list):
                        print("i am here44444444")
                        if(str(root_send[1][-1][0].text) == "EQMOVE"):
                            print("i am here")
                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                            send_dict["send_FUNCTION"] = root_send[0][1].text
                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                            send_dict["send_IP"] = root_send[0][3].text
                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                            send_dict["send_PROCESS_ID"] = root_send[0][7].text
                            send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                            send_dict["send_LANG"] = root_send[0][9].text
                            send_dict["send_TIMESTAMP"] = root_send[0][10].text
                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                            send_dict["send_strUSERID"] = root_send[1][1].text
                            send_dict["send_strCARRIERID"] = root_send[1][2].text
                            send_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                            send_dict["send_strFROMDEVICE"] = root_send[1][4].text
                            send_dict["send_strFROMPORT"] = root_send[1][5].text
                            send_dict["send_strTODEVICE"] = root_send[1][6].text
                            send_dict["send_strTOPORT"] = root_send[1][7].text
                            send_dict["send_strEMPTYCARRIER"] = root_send[1][8].text
                            send_dict["send_strPRIORITY"] = root_send[1][9].text
                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                            print(result_send_data_frame)
                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_eqmove.xlsx")
                            return jsonify(send_dict)
    elif(send_method == "EMPTYCARRMOVE"):
        print("emptycarrmove function is send")
        EMPTYCARRMOVE_xml_data = EMPTYCARRMOVE.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERTYPE')).encode('utf-8')),
            TODEVICE=((request.form.get('strTODEVICE')).encode('utf-8')),
            TOPORT=((request.form.get('strTOPORT')).encode('utf-8')),
            PRIORITY=((request.form.get('strPRIORITY')).encode('utf-8')),
        )
        print(EMPTYCARRMOVE_xml_data)
        status_of_send = send_msmaq(send_method, EMPTYCARRMOVE_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "EMPTYCARRMOVE"
        send_dict["send_message_body"] = EMPTYCARRMOVE_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            # print(send_dict["send_message_body"])
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send) > 1):
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text in check_need_to_send_function_list):
                            if(str(root_send[1][-1][0].text) == "EMPTYCARRMOVE"):
                                send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_dict["send_FUNCTION"] = root_send[0][1].text
                                send_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_dict["send_IP"] = root_send[0][3].text
                                send_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_dict["send_LANG"] = root_send[0][9].text
                                send_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_dict["send_strUSERID"] = root_send[1][1].text
                                send_dict["send_strCARRIERIDTYPE"] = root_send[1][2].text
                                send_dict["send_strTODEVICE"] = root_send[1][3].text
                                send_dict["send_strTOPORT"] = root_send[1][4].text
                                send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_dict["send_strCMD"] = root_send[1][-1][2].text
                                result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                print(result_send_data_frame)
                                #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_emptycarrmove.xlsx")
                                return jsonify(send_dict)
    elif(send_method == "CHANGECMD"):
        print("changecmd function is send")
        print((request.form.get('strCOMMANDID')).encode('utf-8'))
        CHANGECMD_xml_data = CHANGECMD.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERRID')).encode('utf-8')),
            FROMDEVICE=((request.form.get('strFROMDEVICE')).encode('utf-8')),
            FROMPORT=((request.form.get('strFROMPORT')).encode('utf-8')),
            TODEVICE=((request.form.get('strTODEVICE')).encode('utf-8')),
            TOPORT=((request.form.get('strTOPORT')).encode('utf-8')),
            PRIORITY=((request.form.get('strPRIORITY')).encode('utf-8')),
        )
        print(CHANGECMD_xml_data)
        status_of_send = send_msmaq(send_method, CHANGECMD_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "CHANGECMD"
        send_dict["send_message_body"] = CHANGECMD_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            # print(send_dict["msmq_message"])
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send) > 1):
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text in check_need_to_send_function_list):
                            if(str(root_send[1][-1][0].text) == "CHANGECMD"):
                                send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_dict["send_FUNCTION"] = root_send[0][1].text
                                send_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_dict["send_IP"] = root_send[0][3].text
                                send_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_dict["send_LANG"] = root_send[0][9].text
                                send_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_dict["send_strUSERID"] = root_send[1][1].text
                                send_dict["send_strCARRIERID"] = root_send[1][2].text
                                send_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                                send_dict["send_strFROMDEVICE"] = root_send[1][4].text
                                send_dict["send_strFROMPORT"] = root_send[1][5].text
                                send_dict["send_strTODEVICE"] = root_send[1][6].text
                                send_dict["send_strTOPORT"] = root_send[1][7].text
                                send_dict["send_strPRIORITY"] = root_send[1][8].text
                                send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_dict["send_strCMD"] = root_send[1][-1][2].text
                                result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                print(result_send_data_frame)
                                #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_changecmd.xlsx")
                                return jsonify(send_dict)
    elif(send_method == "MOVEREQUEST"):
        print("moverequest function is send")
        MOVEREQUEST_xml_data = MOVEREQUEST.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERRID')).encode('utf-8')),
            FROMDEVICE=((request.form.get('strFROMDEVICE')).encode('utf-8')),
            FROMPORT=((request.form.get('strFROMPORT')).encode('utf-8')),
            TODEVICE=((request.form.get('strTODEVICE')).encode('utf-8')),
            TOPORT=((request.form.get('strTOPORT')).encode('utf-8')),
            PRIORITY=((request.form.get('strPRIORITY')).encode('utf-8')),
        )
        print(MOVEREQUEST_xml_data)
        status_of_send = send_msmaq(send_method, MOVEREQUEST_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "MOVEREQUEST"
        send_dict["send_message_body"] = MOVEREQUEST_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            # print(send_dict["msmq_message"])
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send) > 1):
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text in check_need_to_send_function_list):
                            if(str(root_send[1][-1][0].text) == "MOVEREQUEST"):
                                send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_dict["send_FUNCTION"] = root_send[0][1].text
                                send_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_dict["send_IP"] = root_send[0][3].text
                                send_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_dict["send_LANG"] = root_send[0][9].text
                                send_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_dict["send_strUSERID"] = root_send[1][1].text
                                send_dict["send_strCARRIERID"] = root_send[1][2].text
                                send_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                                send_dict["send_strFROMDEVICE"] = root_send[1][4].text
                                send_dict["send_strFROMPORT"] = root_send[1][5].text
                                send_dict["send_strTODEVICE"] = root_send[1][6].text
                                send_dict["send_strTOPORT"] = root_send[1][7].text
                                send_dict["send_strPRIORITY"] = root_send[1][8].text
                                send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_dict["send_strCMD"] = root_send[1][-1][2].text
                                result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                print(result_send_data_frame)
                                #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_moverequest.xlsx")
                                return jsonify(send_dict)
    elif(send_method == "INVDATA"):
        print('INVDATA function is send')
        INVDATA_xml_data = INVDATA.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            STKID=((request.form.get('strSTKID')).encode('utf-8')),
        )
        print(INVDATA_xml_data)
        status_of_send = send_msmaq(send_method, INVDATA_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "INVDATA"
        send_dict["send_message_body"] = INVDATA_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            # print(send_dict["msmq_message"])
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send) > 1):
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text in check_need_to_send_function_list):
                            if(str(root_send[1][-1][0].text) == "INVDATA"):
                                send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_dict["send_FUNCTION"] = root_send[0][1].text
                                send_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_dict["send_IP"] = root_send[0][3].text
                                send_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_dict["send_LANG"] = root_send[0][9].text
                                send_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_dict["send_strUSERID"] = root_send[1][1].text
                                send_dict["send_strSTKID"] = root_send[1][2].text
                                send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_dict["send_strCMD"] = root_send[1][-1][2].text
                                result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                print(result_send_data_frame)
                                #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_invdata.xlsx")
                                return jsonify(send_dict)
    elif(send_method == "MOVESTATUSREQUEST"):
        print("movestatusrequest function is send")
        MOVESTATUSREQUEST_xml_data = MOVESTATUSREQUEST.format(
            IP=SendQueueIP,
            QUEUE_NAME=SendQueueName,
            CLIENT_HOSTNAME=HostName,
            FUNCTION_VERSION=Version,
            PROCESS_ID=PID,
            TIMESTAMP=Time,
            COMMANDID=((request.form.get('strCOMMANDID')).encode('utf-8')),
            USERID=((request.form.get('strUSERID')).encode('utf-8')),
            CARRIERID=((request.form.get('strCARRIERRID')).encode('utf-8')),
        )
        print(MOVESTATUSREQUEST_xml_data)
        status_of_send = send_msmaq(send_method, MOVESTATUSREQUEST_xml_data)
        send_dict["status_of_send"] = status_of_send
        send_dict["send_message_label"] = "MOVESTATUSREQUEST"
        send_dict["send_message_body"] = MOVESTATUSREQUEST_xml_data
        if(send_dict["send_message_body"][0] == "<"):
            # print(send_dict["send_message_body"])
            root_send = etree.fromstring(send_dict["send_message_body"])
            if(len(root_send) > 1):
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text in check_need_to_send_function_list):
                            if(str(root_send[1][-1][0].text) == "MOVESTATUSREQUEST"):
                                send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_dict["send_FUNCTION"] = root_send[0][1].text
                                send_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_dict["send_IP"] = root_send[0][3].text
                                send_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_dict["send_LANG"] = root_send[0][9].text
                                send_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_dict["send_strUSERID"] = root_send[1][1].text
                                send_dict["send_strCARRIERID"] = root_send[1][2].text
                                send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_dict["send_strCMD"] = root_send[1][-1][2].text
                                result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                print(result_send_data_frame)
                                #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_movestatusrequest.xlsx")
                                return jsonify(send_dict)
    else:
        send_dict["send_message_body"] = "no this function"
        return jsonify(send_dict)
    # return jsonify(send_dict)
@app.route('/send_stkmove_batch_function', methods=["GET", "POST"])
def send_stkmove_batch_function():
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    print("i am in send_stkmove_batch_function")
    send_batch_stkmove_all_dict={}
    batch_stkmove_data_frame = pd.read_excel('./batch_excel/stkmove.xlsx')#讀取excel文件
    print(batch_stkmove_data_frame)
    batch_stkmove_data_frame['strFROMPORT'] = batch_stkmove_data_frame['strFROMPORT'].apply(lambda x : '{:0>2d}'.format(x))
    #print(batch_stkmove_data_frame['strFROMPORT'])
    
    for batch_stkmove_data_frame_index in range(len(batch_stkmove_data_frame)):
        send_batch_stkmove_dict={}
        send_batch_stkmove_dict_key="stkmove_batch_"+str(batch_stkmove_data_frame_index)
        print("strCARRIERTYPE:"+str(batch_stkmove_data_frame['strCARRIERTYPE'][batch_stkmove_data_frame_index]))
        print("strCOMMANDID:"+str(batch_stkmove_data_frame['strCOMMANDID'][batch_stkmove_data_frame_index]))
        print("strUSERID:"+str(batch_stkmove_data_frame['strUSERID'][batch_stkmove_data_frame_index]))
        print("strCARRIERID:"+str(batch_stkmove_data_frame['strCARRIERID'][batch_stkmove_data_frame_index]))
        print("strFROMDEVICE:"+str(batch_stkmove_data_frame['strFROMDEVICE'][batch_stkmove_data_frame_index]))
        print("strFROMPORT:"+'{:0>2}'.format(str(batch_stkmove_data_frame['strFROMPORT'][batch_stkmove_data_frame_index])))
        print("strTODEVICE:"+str(batch_stkmove_data_frame['strTODEVICE'][batch_stkmove_data_frame_index]))
        print("strTOPORT:"+str(batch_stkmove_data_frame['strTOPORT'][batch_stkmove_data_frame_index]))
        print("strEMPTYCARRIER:"+str(batch_stkmove_data_frame['strEMPTYCARRIER'][batch_stkmove_data_frame_index]))
        print("strPRIORITY:"+str(batch_stkmove_data_frame['strPRIORITY'][batch_stkmove_data_frame_index]))
        print("strCMD:"+str(batch_stkmove_data_frame['strCMD'][batch_stkmove_data_frame_index]))
        print("strMETHODNAME:"+str(batch_stkmove_data_frame['strMETHODNAME'][batch_stkmove_data_frame_index]))
        print("strFORMNAME:"+str(batch_stkmove_data_frame['strFORMNAME'][batch_stkmove_data_frame_index]))
        print("function is send")
        if((str(batch_stkmove_data_frame['strMETHODNAME'][batch_stkmove_data_frame_index]))=="STKMOVE"):
            print("function is stkmove")
            STKMOVE_xml_data = STKMOVE.format(
                IP=SendQueueIP,
                QUEUE_NAME=SendQueueName,
                CLIENT_HOSTNAME=HostName,
                FUNCTION_VERSION=Version,
                PROCESS_ID=PID,
                TIMESTAMP=Time,
                COMMANDID=str(batch_stkmove_data_frame['strCOMMANDID'][batch_stkmove_data_frame_index]),
                USERID=str(batch_stkmove_data_frame['strUSERID'][batch_stkmove_data_frame_index]),
                CARRIERID=str(batch_stkmove_data_frame['strCARRIERID'][batch_stkmove_data_frame_index]),
                FROMDEVICE=str(batch_stkmove_data_frame['strFROMDEVICE'][batch_stkmove_data_frame_index]),
                FROMPORT=str(batch_stkmove_data_frame['strFROMPORT'][batch_stkmove_data_frame_index]),
                TODEVICE=str(batch_stkmove_data_frame['strTODEVICE'][batch_stkmove_data_frame_index]),
                TOPORT=str(batch_stkmove_data_frame['strTOPORT'][batch_stkmove_data_frame_index]),
                EMPTYCARRIER=str(batch_stkmove_data_frame['strEMPTYCARRIER'][batch_stkmove_data_frame_index]),
                PRIORITY=str(batch_stkmove_data_frame['strPRIORITY'][batch_stkmove_data_frame_index]))
            print(STKMOVE_xml_data)
            status_of_send = send_msmaq("STKMOVE", STKMOVE_xml_data)  # here
            send_batch_stkmove_dict["status_of_send"] = status_of_send
            send_batch_stkmove_dict["send_message_label"] = "STKMOVE"
            send_batch_stkmove_dict["send_message_body"] = STKMOVE_xml_data
            if(send_batch_stkmove_dict["send_message_body"][0] == "<"):
                root_send = etree.fromstring(send_batch_stkmove_dict["send_message_body"])
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text =="STKMOVE"):
                            if(str(root_send[1][-1][0].text) == "STKMOVE"):
                                send_batch_stkmove_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_batch_stkmove_dict["send_FUNCTION"] = root_send[0][1].text
                                send_batch_stkmove_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_batch_stkmove_dict["send_IP"] = root_send[0][3].text
                                send_batch_stkmove_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_batch_stkmove_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_batch_stkmove_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_batch_stkmove_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_batch_stkmove_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_batch_stkmove_dict["send_LANG"] = root_send[0][9].text
                                send_batch_stkmove_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_batch_stkmove_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_batch_stkmove_dict["send_strUSERID"] = root_send[1][1].text
                                send_batch_stkmove_dict["send_strCARRIERID"] = root_send[1][2].text
                                send_batch_stkmove_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                                send_batch_stkmove_dict["send_strFROMDEVICE"] = root_send[1][4].text
                                send_batch_stkmove_dict["send_strFROMPORT"] = root_send[1][5].text
                                send_batch_stkmove_dict["send_strTODEVICE"] = root_send[1][6].text
                                send_batch_stkmove_dict["send_strTOPORT"] = root_send[1][7].text
                                send_batch_stkmove_dict["send_strEMPTYCARRIER"] = root_send[1][8].text
                                send_batch_stkmove_dict["send_strPRIORITY"] = root_send[1][9].text
                                send_batch_stkmove_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_batch_stkmove_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_batch_stkmove_dict["send_strCMD"] = root_send[1][-1][2].text
        send_batch_stkmove_all_dict[send_batch_stkmove_dict_key]=send_batch_stkmove_dict
        print("delay:"+str(batch_stkmove_data_frame['delay'][batch_stkmove_data_frame_index])+"second")
        time.sleep(batch_stkmove_data_frame['delay'][batch_stkmove_data_frame_index])
    print(send_batch_stkmove_all_dict)
    return jsonify(send_batch_stkmove_all_dict)

@app.route('/send_eqmove_batch_function',methods=["GET","PSOT"])
def send_eqmove_batch_functionn():
    timeNow = datetime.datetime.now()
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")
    print("i am in send_eqmove_batch_function")
    
    batch_eqmove_data_frame = pd.read_excel('./batch_excel/eqmove.xlsx')
    send_batch_eqmove_all_dict={}
    print(batch_eqmove_data_frame)
    batch_eqmove_data_frame['strTOPORT'] = batch_eqmove_data_frame['strTOPORT'].apply(lambda x : '{:0>2d}'.format(x))
    for batch_eqmove_data_frame_index in range(len(batch_eqmove_data_frame)):
        send_batch_eqmove_dict={}
        send_batch_eqmove_dict_key="eqmove_batch_"+str(batch_eqmove_data_frame_index)
        print("strCARRIERTYPE:"+str(batch_eqmove_data_frame['strCARRIERTYPE'][batch_eqmove_data_frame_index]))
        print("strCOMMANDID:"+str(batch_eqmove_data_frame['strCOMMANDID'][batch_eqmove_data_frame_index]))
        print("strUSERID:"+str(batch_eqmove_data_frame['strUSERID'][batch_eqmove_data_frame_index]))
        print("strCARRIERID:"+str(batch_eqmove_data_frame['strCARRIERID'][batch_eqmove_data_frame_index]))
        print("strFROMDEVICE:"+str(batch_eqmove_data_frame['strFROMDEVICE'][batch_eqmove_data_frame_index]))
        print("strFROMPORT:"+'{:0>2}'.format(str(batch_eqmove_data_frame['strFROMPORT'][batch_eqmove_data_frame_index])))
        print("strTODEVICE:"+str(batch_eqmove_data_frame['strTODEVICE'][batch_eqmove_data_frame_index]))
        print("strTOPORT:"+str(batch_eqmove_data_frame['strTOPORT'][batch_eqmove_data_frame_index]))
        print("strEMPTYCARRIER:"+str(batch_eqmove_data_frame['strEMPTYCARRIER'][batch_eqmove_data_frame_index]))
        print("strPRIORITY:"+str(batch_eqmove_data_frame['strPRIORITY'][batch_eqmove_data_frame_index]))
        print("strCMD:"+str(batch_eqmove_data_frame['strCMD'][batch_eqmove_data_frame_index]))
        print("strMETHODNAME:"+str(batch_eqmove_data_frame['strMETHODNAME'][batch_eqmove_data_frame_index]))
        print("strFORMNAME:"+str(batch_eqmove_data_frame['strFORMNAME'][batch_eqmove_data_frame_index]))
        print("function is send")
        if((str(batch_eqmove_data_frame['strMETHODNAME'][batch_eqmove_data_frame_index]))=="EQMOVE"):
            print("function is eqmove")
            EQMOVE_xml_data = EQMOVE.format(
                IP=SendQueueIP,
                QUEUE_NAME=SendQueueName,
                CLIENT_HOSTNAME=HostName,
                FUNCTION_VERSION=Version,
                PROCESS_ID=PID,
                TIMESTAMP=Time,
                COMMANDID=str(batch_eqmove_data_frame['strCOMMANDID'][batch_eqmove_data_frame_index]),
                USERID=str(batch_eqmove_data_frame['strUSERID'][batch_eqmove_data_frame_index]),
                CARRIERID=str(batch_eqmove_data_frame['strCARRIERID'][batch_eqmove_data_frame_index]),
                FROMDEVICE=str(batch_eqmove_data_frame['strFROMDEVICE'][batch_eqmove_data_frame_index]),
                FROMPORT=str(batch_eqmove_data_frame['strFROMPORT'][batch_eqmove_data_frame_index]),
                TODEVICE=str(batch_eqmove_data_frame['strTODEVICE'][batch_eqmove_data_frame_index]),
                TOPORT=str(batch_eqmove_data_frame['strTOPORT'][batch_eqmove_data_frame_index]),
                EMPTYCARRIER=str(batch_eqmove_data_frame['strEMPTYCARRIER'][batch_eqmove_data_frame_index]),
                PRIORITY=str(batch_eqmove_data_frame['strPRIORITY'][batch_eqmove_data_frame_index]))
            print(EQMOVE_xml_data)
            status_of_send = send_msmaq("EQMOVE",EQMOVE_xml_data)
            send_batch_eqmove_dict["status_of_send"] = status_of_send
            send_batch_eqmove_dict["send_message_label"] = "EQMOVE"
            send_batch_eqmove_dict["send_message_body"] = EQMOVE_xml_data
            if(send_batch_eqmove_dict["send_message_body"][0] == "<"):
                root_send = etree.fromstring(send_batch_eqmove_dict["send_message_body"])
                if(len(root_send[1]) > 1):
                    if(len(root_send[1][-1]) >= 1):
                        if(root_send[1][-1][0].text =="EQMOVE"):
                            if(str(root_send[1][-1][0].text) == "EQMOVE"):
                                send_batch_eqmove_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                send_batch_eqmove_dict["send_FUNCTION"] = root_send[0][1].text
                                send_batch_eqmove_dict["send_SERVERNAME"] = root_send[0][2].text
                                send_batch_eqmove_dict["send_IP"] = root_send[0][3].text
                                send_batch_eqmove_dict["send_DLL_NAME"] = root_send[0][4].text
                                send_batch_eqmove_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                send_batch_eqmove_dict["send_CLASSNAME"] = root_send[0][6].text
                                send_batch_eqmove_dict["send_PROCESS_ID"] = root_send[0][7].text
                                send_batch_eqmove_dict["send_QUEUE_NAME"] = root_send[0][8].text
                                send_batch_eqmove_dict["send_LANG"] = root_send[0][9].text
                                send_batch_eqmove_dict["send_TIMESTAMP"] = root_send[0][10].text
                                send_batch_eqmove_dict["send_strCOMMANDID"] = root_send[1][0].text
                                send_batch_eqmove_dict["send_strUSERID"] = root_send[1][1].text
                                send_batch_eqmove_dict["send_strCARRIERID"] = root_send[1][2].text
                                send_batch_eqmove_dict["send_strCARRIERIDTYPE"] = root_send[1][3].text
                                send_batch_eqmove_dict["send_strFROMDEVICE"] = root_send[1][4].text
                                send_batch_eqmove_dict["send_strFROMPORT"] = root_send[1][5].text
                                send_batch_eqmove_dict["send_strTODEVICE"] = root_send[1][6].text
                                send_batch_eqmove_dict["send_strTOPORT"] = root_send[1][7].text
                                send_batch_eqmove_dict["send_strEMPTYCARRIER"] = root_send[1][8].text
                                send_batch_eqmove_dict["send_strPRIORITY"] = root_send[1][9].text
                                send_batch_eqmove_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                send_batch_eqmove_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                send_batch_eqmove_dict["send_strCMD"] = root_send[1][-1][2].text
        send_batch_eqmove_all_dict[send_batch_eqmove_dict_key]=send_batch_eqmove_dict
        print("delay:"+str(batch_eqmove_data_frame['delay'][batch_eqmove_data_frame_index])+"second")
        time.sleep(batch_eqmove_data_frame['delay'][batch_eqmove_data_frame_index])
    print(send_batch_eqmove_all_dict)
    return jsonify(send_batch_eqmove_all_dict)





@app.route('/receive_function', methods=["GET", "POST"])
def receive_function_and_process_function():
    timeNow = datetime.datetime.now()  # 讀取系統現在的時間戳
    Time = timeNow.strftime("%Y/%m/%d %H:%M:%S")  # 將時間戳轉爲YYYY/MM/DD HH:mm:SS格式
    hope_dict = {
        "lunch": "burger",
    }
    need_change_to_input_list = ["OUTSTK", "LEAVE", "ARRIVE",
                                 "VALIDINPUT", "OUTEQP", "INEQP", "CARR_ALARM", "INSTK", "FOUPINFO"]
    check_need_to_send_function_list = [
        "STKMOVE", "EQMOVE", "EMPTYCARRMOVE", "CHANGECMD", "MOVEREQUEST", "INVDATA", "MOVESTATUSREQUEST"]
    need_change_to_send_function_replay_list = [
        "OUTSTK_R", "LEAVE_R", "ARRIVE_R", "VALIDINPUT_R", "OUTEQP_R", "INEQP_R", "CARR_ALARM_R", "INSTK_R", "FOUPINFO_R"]
    print("i am here recv1")
    recv_dict = {}
    recv_dict_2 = {}
    send_dict = {}

    recv_msmq_dict = recv_msmq()

    recv_dict["recv_message_label"] = recv_msmq_dict["message_label"]
    recv_dict["recv_message_body"] = recv_msmq_dict["message_body"]
    if(recv_dict["recv_message_body"][0] == "<"):
        root_recv = etree.fromstring(recv_dict["recv_message_body"])
        print(root_recv[1][1].tag)
        if(len(root_recv) > 1):
            if(len(root_recv[1][-1]) >= 1):
                if(root_recv[1][-1][0].text not in need_change_to_input_list):
                    if(str(root_recv[1][-1][0].text) == "STKMOVE_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strRESULT"] = root_recv[1][1].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_stkmove_r.xlsx")
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "EQMOVE_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strRESULT"] = root_recv[1][1].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_eqmove_r.xlsx")
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "EMPTYCARRMOVE_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strRESULT"] = root_recv[1][1].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][2].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][3].text
                        recv_dict["recv_strCARRIERTYPE"] = root_recv[1][4].text
                        recv_dict["recv_strFROMDEVICE"] = root_recv[1][5].text
                        recv_dict["recv_strFROMPORT"] = root_recv[1][6].text
                        recv_dict["recv_strTODEVICE"] = root_recv[1][7].text
                        recv_dict["recv_strTOPORT"] = root_recv[1][8].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_emptycarrmove_r.xlsx")
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "CHANGECMD_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strRESULT"] = root_recv[1][1].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_changecmd_r.xlsx")
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "MOVEREQUEST_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strRESULT"] = root_recv[1][1].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_moverequest_r.xlsx")
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "INVDATA_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strSTKID"] = root_recv[1][1].text
                        recv_dict["recv_strCOUNT"] = root_recv[1][2].text
                        recv_dict["recv_strCARRIERIDList"] = root_recv[1][3].text
                        recv_dict["recv_strSTKSTATUS"] = root_recv[1][4].text
                        recv_dict["recv_strRESULT"] = root_recv[1][5].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][6].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_invdata_r.xlsx")
                        return jsonify(recv_dict)
                    if(str(root_recv[1][-1][0].text) == "MOVESTATUSREQUEST_R"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PID"] = root_recv[0][7].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][8].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][9].text
                        recv_dict["recv_LANG"] = root_recv[0][10].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][11].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strMOVESTATUS"] = root_recv[1][2].text
                        recv_dict["recv_strTODEVICE"] = root_recv[1][3].text
                        recv_dict["recv_strTOPORT"] = root_recv[1][4].text
                        recv_dict["recv_strPRIORITY"] = root_recv[1][5].text
                        recv_dict["recv_strRESULT"] = root_recv[1][6].text
                        recv_dict["recv_strERRORMESSAGE"] = root_recv[1][7].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_movestatusrequest_r.xlsx")
                        return jsonify(recv_dict)
                if(root_recv[1][-1][0].text in need_change_to_input_list):
                    if(str(root_recv[1][-1][0].text) == "OUTSTK"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strSTKID"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_outstk.xlsx")
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        OUTSTK_R_xml_data = OUTSTK_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="")
                        print(OUTSTK_R_xml_data)
                        send_dict["send_message_body"] = OUTSTK_R_xml_data
                        send_dict["send_message_label"] = "OUTSTK_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "OUTSTK_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                        return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "LEAVE"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strFROMDEVICE"] = root_recv[1][3].text
                        recv_dict["recv_strFROMPORT"] = root_recv[1][4].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_leave.xlsx")
                        # print(recv_dict_whit_xml)
                        LEAVE_R_xml_data = LEAVE_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(LEAVE_R_xml_data)
                        send_dict["send_message_body"] = LEAVE_R_xml_data
                        send_dict["send_message_label"] = "LEAVE_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            print("check523")
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                print("check529")
                                if(len(root_send[1][-1]) >= 1):
                                    print("check531")
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        print("check533")
                                        if(str(root_send[1][-1][0].text) == "LEAVE_R"):
                                            print("check535")
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_leave_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "ARRIVE"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strTODEVICE"] = root_recv[1][3].text
                        recv_dict["recv_strTOPORT"] = root_recv[1][4].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_arrive.xlsx")
                        # print(recv_dict_whit_xml)
                        ARRIVE_R_xml_data = ARRIVE_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(ARRIVE_R_xml_data)
                        send_dict["send_message_body"] = ARRIVE_R_xml_data
                        send_dict["send_message_label"] = "ARRIVE_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "ARRIVE_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_arriver_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "VALIDINPUT"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strACTIONTYPE"] = root_recv[1][3].text
                        recv_dict["recv_strFROMDEVICE"] = root_recv[1][4].text
                        recv_dict["recv_strFROMPORT"] = root_recv[1][5].text
                        recv_dict["recv_strTODEVICE"] = root_recv[1][6].text
                        recv_dict["recv_strTOPORT"] = root_recv[1][7].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_validinput.xlsx")
                        # print(recv_dict_whit_xml)
                        VALIDINPUT_R_xml_data = VALIDINPUT_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(VALIDINPUT_R_xml_data)
                        send_dict["send_message_body"] = VALIDINPUT_R_xml_data
                        send_dict["send_message_label"] = "VALIDINPUT_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "VALIDINPUT_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_validinput_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "OUTEQP"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strFROMDEVICE"] = root_recv[1][3].text
                        recv_dict["recv_strFROMPORT"] = root_recv[1][4].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_outeqp.xlsx")
                        # print(recv_dict_whit_xml)
                        OUTEQP_R_xml_data = OUTEQP_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(OUTEQP_R_xml_data)
                        send_dict["send_message_body"] = OUTEQP_R_xml_data
                        send_dict["send_message_label"] = "OUTEQP_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "OUTEQP_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_outeqp_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "INEQP"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strTODEVICE"] = root_recv[1][3].text
                        recv_dict["recv_strTOPORT"] = root_recv[1][4].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_ineqp_r.xlsx")
                        # print(recv_dict_whit_xml)
                        INEQP_R_xml_data = INEQP_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(INEQP_R_xml_data)
                        send_dict["send_message_body"] = INEQP_R_xml_data
                        send_dict["send_message_label"] = "INEQP_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            print("check794")
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                print("check798")
                                if(len(root_send[1][-1]) >= 1):
                                    print("check800")
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        print("check802")
                                        if(str(root_send[1][-1][0].text) == "INEQP_R"):
                                            print("check804")
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            print("check823")
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_ineqp_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "CARR_ALARM"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strVEHICLEID"] = root_recv[1][2].text
                        recv_dict["recv_strALARMCODE"] = root_recv[1][3].text
                        recv_dict["recv_strALARMDESC"] = root_recv[1][4].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_carr_alarm.xlsx")
                        # print(recv_dict_whit_xml)
                        CARR_ALARM_R_xml_data = CARR_ALARM_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(CARR_ALARM_R_xml_data)
                        send_dict["send_message_body"] = CARR_ALARM_R_xml_data
                        send_dict["send_message_label"] = "CARR_ALARM_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "CARR_ALARM_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_ carr_alarm_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "INSTK"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strSTKID"] = root_recv[1][2].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_instk.xlsx")
                        # print(recv_dict_whit_xml)
                        INSTK_R_xml_data = INSTK_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        print(INSTK_R_xml_data)
                        send_dict["send_message_body"] = INSTK_R_xml_data
                        send_dict["send_message_label"] = "INSTK_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "INSTK_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strRESULT"] = root_send[1][1].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][2].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_instk_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
                    if(str(root_recv[1][-1][0].text) == "FOUPINFO"):
                        recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                        recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                        recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                        recv_dict["recv_IP"] = root_recv[0][3].text
                        recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                        recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                        recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                        recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                        recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                        recv_dict["recv_LANG"] = root_recv[0][9].text
                        recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                        recv_dict["recv_strCOMMANDID"] = root_recv[1][0].text
                        recv_dict["recv_strCARRIERID"] = root_recv[1][1].text
                        recv_dict["recv_strMETHODNAME"] = root_recv[1][-1][0].text
                        recv_dict["recv_strFORNAME"] = root_recv[1][-1][1].text
                        recv_dict["recv_strCMD"] = root_recv[1][-1][2].text
                        result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                        print(result_recv_data_frame)
                        #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strCOMMANDID"]+"_foupinfo.xlsx")
                        # print(recv_dict_whit_xml)
                        f = open('config.json', 'r')  
                        data = json.load(f)
                        FOUPINFO_R_xml_data = FOUPINFO_R.format(
                            IP=recv_dict["recv_IP"],
                            QUEUE_NAME=recv_dict["recv_QUEUE_NAME"],
                            CLIENT_HOSTNAME=recv_dict["recv_CLIENT_HOSTNAME"],
                            FUNCTION_VERSION=recv_dict["recv_FUNCTION_VERSION"],
                            PROCESS_ID=recv_dict["recv_PROCESS_ID"],
                            TIMESTAMP=recv_dict["recv_TIMESTAMP"],
                            COMMANDID=recv_dict["recv_strCOMMANDID"],
                            CARRIERID=recv_dict["recv_strCARRIERID"],
                            TODEVICE=data.get(recv_dict["recv_strCARRIERID"]),
                            TOPORT="1234",
                            RESULT="OK",
                            ERRORMESSAGE="",

                        )
                        f.close()
                        print(FOUPINFO_R_xml_data)
                        send_dict["send_message_body"] = FOUPINFO_R_xml_data
                        send_dict["send_message_label"] = "FOUPINFO_R"
                        send_msmaq(send_dict["send_message_label"],
                                   send_dict["send_message_body"])
                        if(send_dict["send_message_body"][0] == "<"):
                            root_send = etree.fromstring(
                                send_dict["send_message_body"])
                            if(len(root_send) > 1):
                                if(len(root_send[1][-1]) >= 1):
                                    if(root_send[1][-1][0].text in need_change_to_send_function_replay_list):
                                        if(str(root_send[1][-1][0].text) == "FOUPINFO_R"):
                                            send_dict["send_CLIENT_HOSTNAME"] = root_send[0][0].text
                                            send_dict["send_FUNCTION"] = root_send[0][1].text
                                            send_dict["send_SERVERNAME"] = root_send[0][2].text
                                            send_dict["send_IP"] = root_send[0][3].text
                                            send_dict["send_DLL_NAME"] = root_send[0][4].text
                                            send_dict["send_FUNCTION_VERSION"] = root_send[0][5].text
                                            send_dict["send_CLASSNAME"] = root_send[0][6].text
                                            send_dict["send_PID"] = root_send[0][7].text
                                            send_dict["send_PROCESS_ID"] = root_send[0][8].text
                                            send_dict["send_QUEUE_NAME"] = root_send[0][9].text
                                            send_dict["send_LANG"] = root_send[0][10].text
                                            send_dict["send_TIMESTAMP"] = root_send[0][11].text
                                            send_dict["send_strCOMMANDID"] = root_send[1][0].text
                                            send_dict["send_strCARRIERID"] = root_send[1][1].text
                                            send_dict["send_strTODEVICE"] = root_send[1][2].text
                                            send_dict["send_strTOPORT"] = root_send[1][3].text
                                            send_dict["send_strRESULT"] = root_send[1][4].text
                                            send_dict["send_strERRORMESSAGE"] = root_send[1][5].text
                                            send_dict["send_strMETHODNAME"] = root_send[1][-1][0].text
                                            send_dict["send_strFORNAME"] = root_send[1][-1][1].text
                                            send_dict["send_strCMD"] = root_send[1][-1][2].text
                                            result_send_data_frame=pd.DataFrame.from_dict(send_dict, orient='index')
                                            print(result_send_data_frame)
                                            #result_send_data_frame.to_excel("./mes_excel/"+send_dict["send_strCOMMANDID"]+"_foupinfo_r.xlsx")
                                            return jsonify(send_dict, recv_dict)
            if(str(root_recv[1][1].tag) == "strALARMID"):
                print(root_recv[1][1].tag)
                recv_dict["recv_CLIENT_HOSTNAME"] = root_recv[0][0].text
                recv_dict["recv_FUNCTION"] = root_recv[0][1].text
                recv_dict["recv_SERVERNAME"] = root_recv[0][2].text
                recv_dict["recv_IP"] = root_recv[0][3].text
                recv_dict["recv_DLL_NAME"] = root_recv[0][4].text
                recv_dict["recv_FUNCTION_VERSION"] = root_recv[0][5].text
                recv_dict["recv_CLASSNAME"] = root_recv[0][6].text
                recv_dict["recv_PROCESS_ID"] = root_recv[0][7].text
                recv_dict["recv_QUEUE_NAME"] = root_recv[0][8].text
                recv_dict["recv_LANG"] = root_recv[0][9].text
                recv_dict["recv_TIMESTAMP"] = root_recv[0][10].text
                recv_dict["recv_strEQCHAR"] = root_recv[1][0].text
                recv_dict["recv_strALARMID"] = root_recv[1][1].text
                recv_dict["recv_strEQPID"] = root_recv[1][2].text
                recv_dict["recv_strALARMLEVEL"] = root_recv[1][3].text
                recv_dict["recv_strALARMTYPE"] = root_recv[1][4].text
                recv_dict["recv_strALARMCODE"] = root_recv[1][5].text
                recv_dict["recv_strALARMMSG"] = root_recv[1][6].text
                recv_dict["recv_strALARMSYS"] = root_recv[1][7].text
                recv_dict["recv_strALARMSYS"] = root_recv[1][7].text
                recv_dict["recv_strALARMTIME"] = root_recv[1][8].text
                recv_dict["recv_strDEPT"] = root_recv[1][9].text
                recv_dict["recv_strSTAGE"] = root_recv[1][10].text
                result_recv_data_frame=pd.DataFrame.from_dict(recv_dict, orient='index')
                print(result_recv_data_frame)
                #result_recv_data_frame.to_excel("./mes_excel/"+recv_dict["recv_strALARMID"]+"_ALARM.xlsx")
                return jsonify(send_dict, recv_dict)
    else:
        return jsonify(recv_dict)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8887, debug=True)
