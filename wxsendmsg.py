#!/usr/bin/env python
# coding=utf-8

import os
import urllib.request, urllib.parse, urllib.error
import re
import http.cookiejar
import time
import xml.dom.minidom
import json
import sys
import math
import subprocess
import json
import threading

DEBUG = False

QRImagePath = os.getcwd() + '/qrcode.jpg'

tip = 0
uuid = ''

base_uri = ''
redirect_uri = ''

skey = ''
wxsid = ''
wxuin = ''
pass_ticket = ''
deviceId = 'e000000000000000'
SyncKey = {}
BaseRequest = {}

ContactList = []
My = []

def getUUID():
    global uuid

    url = 'https://login.weixin.qq.com/jslogin'
    params = {
        'appid': 'wx782c26e4c19acffb',
        'fun': 'new',
        'lang': 'zh_CN',
        '_': int(time.time()),
    }

    request = urllib.request.Request(url=url, data=urllib.parse.urlencode(params).encode(encoding='UTF8'))
    response = urllib.request.urlopen(request)
    data = response.read()

    # print data
    # window.QRLogin.code = 200; window.QRLogin.uuid = "oZwt_bFfRg==";
    regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
    pm = re.search(regx, str(data))

    code = pm.group(1)
    uuid = pm.group(2)

    if code == '200':
        return True

    return False


def showQRImage():
    global tip

    url = 'https://login.weixin.qq.com/qrcode/' + uuid
    params = {
        't': 'webwx',
        '_': int(time.time()),
    }

    request = urllib.request.Request(url=url, data=urllib.parse.urlencode(params).encode(encoding='UTF-8'))
    response = urllib.request.urlopen(request)

    tip = 1

    f = open(QRImagePath, 'wb')
    f.write(response.read())
    f.close()

    if sys.platform.find('darwin') >= 0:
        subprocess.call(['open', QRImagePath])
    elif sys.platform.find('linux') >= 0:
        subprocess.call(['xdg-open', QRImagePath])
    else:
        os.startfile(QRImagePath)

    print(u'请使用微信扫描二维码以登录')

def waitForLogin():
    global tip, base_uri, redirect_uri

    url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (tip, uuid, int(time.time()))

    request = urllib.request.Request(url=url)
    response = urllib.request.urlopen(request)
    data = response.read()

    # print data

    # window.code=500;
    regx = r'window.code=(\d+);'
    pm = re.search(regx, str(data))

    code = pm.group(1)

    if code == '201':  # 已扫描
        print(u'成功扫描,请在手机上点击确认以登录')
        tip = 0
    elif code == '200':  # 已登录
        print(u'正在登录...')
        regx = r'window.redirect_uri="(\S+?)";'
        pm = re.search(regx, str(data))
        redirect_uri = pm.group(1) + '&fun=new'
        base_uri = redirect_uri[:redirect_uri.rfind('/')]
    elif code == '408':  # 超时
        pass
    # elif code == '400' or code == '500':

    return code


def login():
    global skey, wxsid, wxuin, pass_ticket, BaseRequest

    request = urllib.request.Request(url=redirect_uri)
    response = urllib.request.urlopen(request)
    data = response.read()

    # print data

    '''
		<error>
			<ret>0</ret>
			<message>OK</message>
			<skey>xxx</skey>
			<wxsid>xxx</wxsid>
			<wxuin>xxx</wxuin>
			<pass_ticket>xxx</pass_ticket>
			<isgrayscale>1</isgrayscale>
		</error>
	'''

    doc = xml.dom.minidom.parseString(data)
    root = doc.documentElement

    for node in root.childNodes:
        if node.nodeName == 'skey':
            skey = node.childNodes[0].data
        elif node.nodeName == 'wxsid':
            wxsid = node.childNodes[0].data
        elif node.nodeName == 'wxuin':
            wxuin = node.childNodes[0].data
        elif node.nodeName == 'pass_ticket':
            pass_ticket = node.childNodes[0].data

    # print 'skey: %s, wxsid: %s, wxuin: %s, pass_ticket: %s' % (skey, wxsid, wxuin, pass_ticket)

    if skey == '' or wxsid == '' or wxuin == '' or pass_ticket == '':
        return False

    BaseRequest = {
        'Uin': int(wxuin),
        'Sid': wxsid,
        'Skey': skey,
        'DeviceID': deviceId,
    }

    return True


def webwxinit():
    global SyncKey
    url = base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (pass_ticket, skey, int(time.time()))
    params = {
        'BaseRequest': BaseRequest
    }

    request = urllib.request.Request(url=url, data=json.dumps(params).encode('utf-8'))
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    response = urllib.request.urlopen(request)
    data = response.read()

    if DEBUG:
        f = open(os.getcwd() + '/webwxinit.json', 'wb')
        f.write(data)
        f.close()

    # print data

    global ContactList, My
    dic = json.loads(data.decode())
    ContactList = dic['ContactList']
    My = dic['User']

    ErrMsg = dic['BaseResponse']['ErrMsg']
    # if len(ErrMsg) > 0:
    # 	print ErrMsg

    Ret = dic['BaseResponse']['Ret']
    if Ret != 0:
        return False

    #获得用户与服务器同步的信息
    #SyncKey = dic['SyncKey']

    return True

def webwxgetcontact():
    url = base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (pass_ticket, skey, int(time.time()))

    request = urllib.request.Request(url=url)
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    response = urllib.request.urlopen(request)
    data = response.read()

    if DEBUG:
        f = open(os.getcwd() + '/webwxgetcontact.json', 'wb')
        f.write(data)
        f.close()

    # print data
    data = data.decode('utf-8', 'replace')

    dic = json.loads(data)
    MemberList = dic['MemberList']

    # 倒序遍历,不然删除的时候出问题..
    SpecialUsers = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage', 'tmessage', 'qmessage',
                    'qqsync', 'floatbottle', 'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp', 'blogapp',
                    'facebookapp', 'masssendapp', 'meishiapp', 'feedsapp', 'voip', 'blogappweixin', 'weixin',
                    'brandsessionholder', 'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c',
                    'officialaccounts', 'notification_messages', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil',
                    'userexperience_alarm', 'notification_messages']
    for i in range(len(MemberList) - 1, -1, -1):
        Member = MemberList[i]
        if Member['VerifyFlag'] & 8 != 0:  # 公众号/服务号
            MemberList.remove(Member)
        elif Member['UserName'] in SpecialUsers:  # 特殊账号
            MemberList.remove(Member)
        elif Member['UserName'].find('@@') != -1:  # 群聊
            MemberList.remove(Member)
        elif Member['UserName'] == My['UserName']:  # 自己
            MemberList.remove(Member)

    return MemberList

# 根据指定的Username发消息
def sendMsg(MyUserName, ToUserName, msg, seconds):
    url = base_uri + '/webwxsendmsg?pass_ticket=%s' % (pass_ticket)
    params = {
        "BaseRequest": BaseRequest,
        "Msg": {"Type": 1, "Content": msg, "FromUserName": MyUserName, "ToUserName": ToUserName},
    }

    json_obj = json.dumps(params,ensure_ascii=False).encode('utf-8')#ensure_ascii=False防止中文乱码
    time.sleep(seconds)
    request = urllib.request.Request(url=url, data=json_obj)
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    urllib.request.urlopen(request)
    
    #打印响应信息，调试用
    #response = urllib.request.urlopen(request)
    #data = response.read()
    #print(data)

def sendInterface(MemberList, MemberCount):
    print('-'*20+u'发送界面(虽然我丑，但我就是界面)'+'-'*20)
    print(u'选择你要发送消息的对象，你可以按以下方式输入：')
    print(u'1-昵称；2-备注名；3-all(发送给所有人)')
    input_str = input()
    try:
        input_ = input_str.split('-')
        choice = int(input_[0])
        name = input_[1]
    except:
        print(u'请按格式输入，如2-逗比')
        print()
        return []
    print(u'我要对%s说：'%name),
    msg = input()
    print(u'希望在多少小时后发送？如果你输入0，则退出发送界面后立即发送',)
    delay = float(input())
    sleep = delay*3600
    thread_res = []
    if(choice == 1):
        print(u'查找联系人中...')
        for i in range(MemberCount):
            if MemberList[i]['NickName'] == name:
                to_user_found = MemberList[i]['UserName']
                t = threading.Thread(target = sendMsg, args = (My['UserName'], to_user_found, msg, sleep))
                thread_res.append(t)
                return thread_res
        print(u'找不到发送对象')
        print()

    elif(choice == 2):
        print(u'查找联系人中...')
        for i in range(MemberCount):
            if MemberList[i]['RemarkName'] == name:
                to_user_found = MemberList[i]['UserName']
                t = threading.Thread(target = sendMsg, args = (My['UserName'], to_user_found, msg, sleep))
                thread_res.append(t)
                return thread_res
        print(u'找不到发送对象')
        print()

    elif(choice == 3):
        print(u'按回车将发送给所有人(慎用！)...等等！不想让人知道你是群发的？输入1自动在消息前加对方的备注名')
        flag = input()
        for i in range(MemberCount):
            #根据第几次循环显示群发百分比
            #percent = i / MemberCount * 100
            #print(u'群发进度:%6.5s%s'%(str(percent),'%'), end = '\r')

            to_user_found = MemberList[i]['UserName']
            if(flag == '1'):
                mark_name = MemberList[i]['RemarkName']
                t = threading.Thread(target = sendMsg, args = (My['UserName'], to_user_found, mark_name+' '+msg, sleep))
            else:
                t = threading.Thread(target = sendMsg, args = (My['UserName'], to_user_found, msg, sleep))
            thread_res.append(t)
        #print(u'群发进度:%6.5s%s'%(str(100),'%'))
        print()

    return thread_res

def main():
    print(u'欢迎使用情怀版微信，正在生成登录二维码...')

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    urllib.request.install_opener(opener)

    if not getUUID():
        print(u'获取uuid失败')
        return

    showQRImage()
    time.sleep(1)

    while waitForLogin() != '200':
        pass

    os.remove(QRImagePath)

    if not login():
        print(u'登录失败')
        return

    if not webwxinit():
        print(u'初始化失败')
        return

    MemberList = webwxgetcontact()
    MemberCount = len(MemberList)
    print(u'通讯录共%s位好友' % MemberCount)

    if DEBUG:
        #打印联系人信息，调试用
        for i in range(0, MemberCount):
            print(json.dumps(MemberList[i],encoding = 'utf-8',ensure_ascii = False))

    threads = []
    while(True):
        #进入发送界面

        threads_res = sendInterface(MemberList, MemberCount)
        threads_num = len(threads_res)
        if(threads_num == 0):
            continue
        for i in range(threads_num):
            threads.append(threads_res[i])
        print(u'当前有%d个发送线程'%len(threads))
        print(u'回车继续发送，输入q退出发送界面，并开始执行所有发送线程')
        flag = input()
        if(flag == 'q'):
            break

    for t in threads:
        #t.setDaemon(True)
        t.start()

    t.join()
    print(u'程序将在发送成功后自动退出(换句话说，该干嘛干嘛去吧)...')

if __name__ == '__main__':
    main()
