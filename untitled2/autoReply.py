# -*- coding: utf-8 -*-
"""
Created on Sat Jul 27 10:26:17 2019

@author: 16427
"""
import threading
import urllib

import requests

lfasr_host = 'http://raasr.xfyun.cn/api'

# 请求的接口名
api_prepare = '/prepare'
api_upload = '/upload'
api_merge = '/merge'
api_get_progress = '/getProgress'
api_get_result = '/getResult'
# 文件分片大小10M
file_piece_sice = 10485760
# 转写类型
lfasr_type = 0
# 是否开启分词
has_participle = 'false'
has_seperate = 'true'
# 多候选词个数
max_alternatives = 0
# 子用户标识
suid = ''

import base64
import hashlib
import hmac
import json
import os
import _thread
import itchat
import datetime
import time
from itchat.content import *
from threading import Timer


class Client:
    clientCount = 0

    def __init__(self, clientname, no, count, flag):
        self.clientname = clientname
        self.no = no
        self.count = count
        self.flag = flag
        Client.clientCount += 1

    def displayClient(self):
        print("total is%d" % Client.clientCount)


class SliceIdGenerator:
    """slice id生成器"""

    def __init__(self):
        self.__ch = 'aaaaaaaaa`'

    def getNextSliceId(self):
        ch = self.__ch
        j = len(ch) - 1
        while j >= 0:
            cj = ch[j]
            if cj != 'z':
                ch = ch[:j] + chr(ord(cj) + 1) + ch[j + 1:]
                break
            else:
                ch = ch[:j] + 'a' + ch[j + 1:]
                j = j - 1
        self.__ch = ch
        return self.__ch


text = " "


class RequestApi(object):
    def __init__(self, appid, secret_key, upload_file_path):
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path

    # 根据不同的apiname生成不同的参数,本示例中未使用全部参数您可在官网(https://doc.xfyun.cn/rest_api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%86%99.html)查看后选择适合业务场景的进行更换
    def gene_params(self, apiname, taskid=None, slice_id=None):
        appid = self.appid
        secret_key = self.secret_key
        upload_file_path = self.upload_file_path
        ts = str(int(time.time()))
        m2 = hashlib.md5()
        m2.update((appid + ts).encode('utf-8'))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding='utf-8')
        # 以secret_key为key, 上面的md5为msg， 使用hashlib.sha1加密结果为signa
        signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)
        param_dict = {}

        if apiname == api_prepare:
            # slice_num是指分片数量，如果您使用的音频都是较短音频也可以不分片，直接将slice_num指定为1即可
            slice_num = int(file_len / file_piece_sice) + (0 if (file_len % file_piece_sice == 0) else 1)
            param_dict['app_id'] = appid
            param_dict['signa'] = signa
            param_dict['ts'] = ts
            param_dict['file_len'] = str(file_len)
            param_dict['file_name'] = file_name
            param_dict['slice_num'] = str(slice_num)
        elif apiname == api_upload:
            param_dict['app_id'] = appid
            param_dict['signa'] = signa
            param_dict['ts'] = ts
            param_dict['task_id'] = taskid
            param_dict['slice_id'] = slice_id
        elif apiname == api_merge:
            param_dict['app_id'] = appid
            param_dict['signa'] = signa
            param_dict['ts'] = ts
            param_dict['task_id'] = taskid
            param_dict['file_name'] = file_name
        elif apiname == api_get_progress or apiname == api_get_result:
            param_dict['app_id'] = appid
            param_dict['signa'] = signa
            param_dict['ts'] = ts
            param_dict['task_id'] = taskid
        return param_dict

    # 请求和结果解析，结果中各个字段的含义可参考：https://doc.xfyun.cn/rest_api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%86%99.html
    def gene_request(self, apiname, data, files=None, headers=None):
        global text
        response = requests.post(lfasr_host + apiname, data=data, files=files, headers=headers)
        result = json.loads(response.text)

        if result["ok"] == 0:
            print("{} success:".format(apiname) + str(result))
            # write_txt(str(result['data']))
            text = str(result['data'])
            return result
        else:
            print("{} error:".format(apiname) + str(result))
            exit(0)
            return result

    # 预处理
    def prepare_request(self):
        return self.gene_request(apiname=api_prepare,
                                 data=self.gene_params(api_prepare))

    # 上传
    def upload_request(self, taskid, upload_file_path):
        file_object = open(upload_file_path, 'rb')
        try:
            index = 1
            sig = SliceIdGenerator()
            while True:
                content = file_object.read(file_piece_sice)
                if not content or len(content) == 0:
                    break
                files = {
                    "filename": self.gene_params(api_upload).get("slice_id"),
                    "content": content
                }
                response = self.gene_request(api_upload,
                                             data=self.gene_params(api_upload, taskid=taskid,
                                                                   slice_id=sig.getNextSliceId()),
                                             files=files)
                if response.get('ok') != 0:
                    # 上传分片失败
                    print('upload slice fail, response: ' + str(response))
                    return False
                print('upload slice ' + str(index) + ' success')
                index += 1
        finally:
            'file index:' + str(file_object.tell())
            file_object.close()
        return True

    # 合并
    def merge_request(self, taskid):
        return self.gene_request(api_merge, data=self.gene_params(api_merge, taskid=taskid))

    # 获取进度
    def get_progress_request(self, taskid):
        return self.gene_request(api_get_progress, data=self.gene_params(api_get_progress, taskid=taskid))

    # 获取结果
    def get_result_request(self, taskid):
        return self.gene_request(api_get_result, data=self.gene_params(api_get_result, taskid=taskid))

    def all_api_request(self):
        # 1. 预处理
        pre_result = self.prepare_request()
        taskid = pre_result["data"]
        # 2 . 分片上传
        self.upload_request(taskid=taskid, upload_file_path=self.upload_file_path)
        # 3 . 文件合并
        self.merge_request(taskid=taskid)
        # 4 . 获取任务进度
        while True:
            # 每隔20秒获取一次任务进度
            progress = self.get_progress_request(taskid)
            progress_dic = progress
            if progress_dic['err_no'] != 0 and progress_dic['err_no'] != 26605:
                print('task error: ' + progress_dic['failed'])
                return
            else:
                data = progress_dic['data']
                task_status = json.loads(data)
                if task_status['status'] == 9:
                    print('task ' + taskid + ' finished')
                    break
                print('The task ' + taskid + ' is in processing, task status: ' + str(data))

            # 每次获取进度间隔20S
            time.sleep(20)
        # 5 . 获取结果
        self.get_result_request(taskid=taskid)


question = ['默默是一个神奇的智能助手，当您在和小孩子相处中需要帮助时都可以告诉他，它将会主动询问您一些问题，请一次性回答完毕哦。当您准备好时，进行请发送“开始”。？',
            '您好，我是默默，以后将是您的贴心小助手，请问最近一次您需要帮助时，孩子在做什么呢？还有其他参与者吗？（回答举例：孩子在起床穿衣服，我在旁边督促他）',
            '孩子在做这件事上持续了大概多久',
            '孩子是在哪里做这件事的呢？',
            '请问身边有相关参与者么？（如果有，请列举，比如爸爸妈妈、老师、朋友等）',
            '孩子用到了什么产品呢？有使用App吗？',
            '孩子在做这件事时，情绪是怎么样呢？（比如不开心，不愿意起床，故意耍赖不穿衣服；很高兴，玩得特别开心等）',
            '如果从消极到积极可以打-5到5分，您觉得孩子在做这件事时的状态可以打几分？',
            '孩子说了什么特别的话，有什么特别的行为？（比如孩子说：妈妈，要是衣服会自动穿到我身上就好了，然后孩子就指着衣服说，“自动，穿衣”）',
            '您希望孩子做这件事的目标是什么？',
            '您希望孩子在做这件事的过程中，培养她/他的什么能力？',
            '孩子在这件事中遇到了什么困难？',
            '相关参与者在这个过程中，遇到了什么困难？',
            '相关参与者在这个过程中的的心情是怎样的？（如果有多个参与者，请在一句话中分别描述每个人的心情，比如爸爸无奈，妈妈生气）',
            '如果从消极到积极可以打-5到5分，参与者在这件事时的状态可以打几分？（请在一句话中，分别描述每个参与者，比如爸爸-1，妈妈-3））',
            '您觉得孩子在刚才的活动中有可以用到语音助手的地方吗？（如果有，请描述，比如语音助手可以告诉孩子穿衣步骤，鼓励孩子，如果没有，请回答“无”）？',
            '孩子在这件事之前在做什么呀？',
            '孩子从做上一件事到现在这一件事的过程中，有遇到什么困难么？',
            '上述困难解决了么，是怎么解决的？',
            '孩子接下来要做什么事？',
            '好滴，之后再见']

ok = True
ok = 1
person = 0


@itchat.msg_register([TEXT, PICTURE, FRIENDS, CARD, MAP, SHARING, RECORDING, ATTACHMENT, VIDEO], isFriendChat=True,
                     isGroupChat=True, isMpChat=True)
def handle_receive_msg(msg):
    global face_bug
    global flag
    global i
    global ok
    global test
    msg_time_rec = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 接受消息的时间
    msg_from = itchat.search_friends(userName=msg['FromUserName'])['RemarkName']  # 在好友列表中查询发送信息的好友昵称
    msg_time = msg['CreateTime']  # 信息发送的时间
    msg_id = msg['MsgId']  # 每条信息的id
    msg_content = None  # 储存信息的内容
    msg_share_url = None  # 储存分享的链接，比如分享的文章和音乐
    if msg['Type'] == 'Text':  # 如果发送的消息是文本
        msg_content = msg['Text']
        print(msg_content)
        write_txt(" " + msg_content + " " + str(msg_time) + "\n", msg_from)


    # 如果发送的消息是附件、视屏、图片、语音。
    elif msg['Type'] == "Attachment" or msg['Type'] == "Video" \
            or msg['Type'] == 'Picture':
        msg_content = msg['FileName']  # 内容就是他们的文件名
        msg['Text'](str(msg_content))  # 下载文件
        msg.download(msg.fileName)
        write_txt(" " + str(msg_content) + " " + str(msg_time) + "\n", msg_from)

    elif msg['Type'] == "Recording":
        msg_content = msg['FileName']  # 内容就是他们的文件名
        msg['Text'](str(msg_content))  # 下载文件
        msg.download(msg.fileName)
        print(msg.fileName)
        api = RequestApi(appid="5da838be", secret_key="7392c0cea8d4e9ef85880e7a20035d68",
                         upload_file_path=msg_content)
        api.all_api_request()
        write_txt(" " + str(msg_content) + " " + str(msg_time) + "\n", msg_from)
        write_txt(text + "\n", msg_from)

    for i in range(1, person + 1):
        if globals()['client_' + str(i)].flag:
            if msg_from == globals()['client_' + str(i)].clientname:
                # print("aaa")
                # send_message(question[3], msg_from)
                globals()['client_' + str(i)].count += 1

                if globals()['client_' + str(i)].count == len(question):
                    globals()['client_' + str(i)].count = 1
                    globals()['client_' + str(i)].flag = False
                else:
                    send_message(question[int(globals()['client_' + str(i)].count)], msg_from)
                    write_txt(question[int(globals()['client_' + str(i)].count)], msg_from)

        # else:
        # print("else")

    """
    if flag:
        # print(msg_from)
        if i >= len(question):
            flag = False
            ok = 2
        elif msg_from == n:
            i = i + 1
            if i < len(question):
                send_message(question[i], msg_from)
                write_txt(question[i], n)

    else:
        i = 0

    print(ok)
    """


def write_txt(str, name):
    with open(name + ".txt", "a") as f:
        f.write(str)
        f.close()


def public_research():
    for e in range(1, person + 1):
        send_message(question[0], globals()['client_' + str(e)].clientname)
        write_txt(question[0], globals()['client_' + str(e)].clientname)
        globals()['client_' + str(e)].count = 0
        globals()['client_' + str(i)].flag = True
    # print('hello timer')
    global timer  # 定义变量
    timer = threading.Timer(600, public_research)
    timer.start()


def send_message(str, Name):
    users = itchat.search_friends(name=Name)  # 修改发送者名字
    # print(users)
    userName = users[0]['UserName']
    itchat.send(str, userName)


"""
def timer():
    now = datetime.datetime.now()
    now_str = now.strftime('%Y/%m/%d %H:%M:%S')[11:]
    if (str(now_str) > str('21:00:00') and str(now_str) < str('21:55:10')):
        public_research()



if __name__ == '__main__':
    itchat.auto_login(hotReload=True)
    print("请输入本次需要调研的人数")
    person = int(input())
    for i in range(1, person + 1):
        name = input("输入本次需要调研的微信名")
        locals()['client_' + str(i)] = Client(name, i, 0)
        #print(locals()['client_' + str(i)].clientname)

        send_message('嗨，感谢您参加我们的语音交互场景调研。首先请填写一个问卷。链接https://www.wjx.cn/jq/43360902.aspx', name)
        public_research(name)
        # print(client_1.clientname)

        # print(client_1.count)
        # time.sleep(10)
    test()
    itchat.run()
"""
itchat.auto_login(hotReload=True)
print("请输入本次需要调研的人数")
person = int(input())
for i in range(1, person + 1):
    name = input("输入本次需要调研的微信名")
    locals()['client_' + str(i)] = Client(name, i, 0, True)
    # print(locals()['client_' + str(i)].clientname)
    send_message('为了对您有初步的了解，请先填写这个问卷（填写完成请告诉我~）：https://www.wjx.cn/jq/48642421.aspx', name)

timer = threading.Timer(600, public_research)
timer.start()
itchat.run()
