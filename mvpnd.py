import requests
import json
import re
import time
import base64

from bs4 import BeautifulSoup
from random import randrange
#vpn object
class MVPN (object):
    def __init__(self,host='',username='',password=''):
        self.host = host
        self.username = username
        self.password = password
        self.onmessage = None
        self.runing = False
        self.proxy = None
        self.session = requests.Session()
        self.sesskey = ''
        self.convid = ''
        self.baseheaders = headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0'}

    def create_rnd_id(self,size=12):
        map = "abcdefghijklmnopqrstuvwxyz0123456789"
        id = ''
        i = 0
        while i<size:
            rnd = randrange(len(map))
            id+=map[rnd]
            i+=1
        return id

    def get_sessionkey(self):
        fileurl = self.host + 'my/#'
        resp = self.session.get(fileurl,proxies=self.proxy,headers=self.baseheaders)
        soup = BeautifulSoup(resp.text,'html.parser')
        sesskey  =  soup.find('input',attrs={'name':'sesskey'})['value']
        return sesskey

    def login(self):
        try:
            login = self.host+'login/index.php'
            resp = self.session.get(login,proxies=self.proxy,headers=self.baseheaders)
            soup = BeautifulSoup(resp.text,'html.parser')
            anchor = ''
            try:
              anchor = soup.find('input',attrs={'name':'anchor'})['value']
            except:pass
            logintoken = ''
            try:
                logintoken = soup.find('input',attrs={'name':'logintoken'})['value']
            except:pass
            username = self.username
            password = self.password
            payload = {'anchor': '', 'logintoken': logintoken,'username': username, 'password': password, 'rememberusername': 1}
            loginurl = self.host+'login/index.php'
            resp2 = self.session.post(loginurl, data=payload,proxies=self.proxy,headers=self.baseheaders)
            soup = BeautifulSoup(resp2.text,'html.parser')
            counter = 0
            for i in resp2.text.splitlines():
                if "loginerrors" in i or (0 < counter <= 3):
                    counter += 1
                    print(i)
            if counter>0:
                print('No pude iniciar sesion')
                return False
            else:
                try:
                    self.userid = soup.find('div',{'id':'nav-notification-popover-container'})['data-userid']
                except:
                    try:
                        self.userid = soup.find('a',{'title':'Enviar un mensaje'})['data-userid']
                    except:pass
                print('E iniciado sesion con exito')
                try:
                    self.sesskey  =  self.get_sessionkey()
                except:pass
                try:
                    self.convid  =  self.get_conversation_id()
                except:pass
                return True
        except Exception as ex:
            pass
        return False

    def get_conversation_id(self):
        id = ''
        conversationidurl = self.host+'lib/ajax/service.php?sesskey='+self.sesskey+'&info=core_message_get_conversations'
        jsonreq = '[{"index":0,"methodname":"core_message_get_conversations","args":{"userid":"'+self.userid+'","type":null,"limitnum":51,"limitfrom":0,"favourites":true,"mergeself":true}}]'
        jsondata = json.loads(jsonreq)
        resp = self.session.post(conversationidurl,json=jsondata,headers=self.baseheaders)
        data = json.loads(resp.text)
        id = data[0]['data']['conversations'][0]['id']
        return id

    def get_messsages(self):
        messages = []
        try:
            messagesurl = self.host+'lib/ajax/service.php?sesskey='+self.sesskey+'&info=core_message_get_conversation_messages'
            usermessagesindex = self.host+'message/index.php'
            convid = self.convid
            timeform = int(time.time())
            jsonreq = '[{"index":0,"methodname":"core_message_get_conversation_messages","args":{"currentuserid":'+self.userid+',"convid":'+str(convid)+',"newest":true,"limitnum":101,"limitfrom":1, "newest":true}}]'
            jsondata = json.loads(jsonreq)
            resp = self.session.post(messagesurl,json=jsondata,headers=self.baseheaders)
            data = json.loads(resp.text)
            messages = data[0]['data']['messages']
        except:pass
        return messages

    def delete_message(self,message):
        if message:
            delmessageurl = self.host+'lib/ajax/service.php?sesskey='+self.sesskey+'&info=core_message_delete_message'
            jsonreq = '[{"index":0,"methodname":"core_message_delete_message","args":{"messageid":"'+str(message['id'])+'","userid":'+self.userid+'}}]'
            jsondata = json.loads(jsonreq)
            resp = self.session.post(delmessageurl,json=jsondata,headers=self.baseheaders)
            data = json.loads(resp.text)
            return data
        return None

    def delete_all_messages(self):
        list = self.get_messsages()
        for m in list:
            self.delete_message(m)

    def send_message(self,text):
        sendmessageurl = self.host+'lib/ajax/service.php?sesskey='+self.sesskey+'&info=core_message_send_messages_to_conversation'
        jsonreq = '[{"index":0,"methodname":"core_message_send_messages_to_conversation","args":{"conversationid":'+str(self.convid)+',"messages":[{"text":"'+text+'"}]}}]'
        jsondata = json.loads(jsonreq)
        resp = self.session.post(sendmessageurl,json=jsondata,headers=self.baseheaders)
        data = None
        try:
            data = json.loads(resp.text)
        except:pass
        return data

    def on(self,func):self.onmessage = func

    def run(self):
        self.runing = self.login()
        if self.runing:
            self.delete_all_messages()
        while self.runing:
            try:
                list = self.get_messsages()
                for message in list:
                    if self.onmessage:
                        self.onmessage(self,message)
            except Exception as ex:
                print(str(ex))
                self.runing = self.login()

    def download_url(self,url,progressfunc=None,args=None):
        req_id = self.create_rnd_id(8)
        reqsms = 'REQ-' + req_id + '|'

        reqsms += 'Get ' + url

        self.send_message(reqsms)
        self.send_message('END REQ')
        
        #response zone
        filename = ''
        filezise = 0
        fopen = None
        lastresplist = []

        chunk_por = 0
        time_start = time.time()
        time_total = 0
        size_per_second = 0
        clock_start = time_start

        wait = True
        while wait:
            try:
                list = self.get_messsages()
                i = len(list)
                for resp in list:
                    if 'END RESP LIST' in list[0]['text']:break
                    i-=1
                    resp = list[i]
                    if resp:
                            if 'END FILE RESP' in resp['text']:
                                text = resp['text'].replace('<p>','').replace('</p>','')
                                endid = text.split('-')[1]
                                if endid == req_id:
                                    wait = False
                                    break
                            if 'RESP-'+req_id in resp['text'] and resp not in lastresplist:
                                if len(lastresplist)>=10:
                                    lastresplist.clear()
                                text = str(resp['text']).replace('<p>','').replace('</p>','')
                                tokens = str(text).split('|')
                                if len(tokens)>1:
                                    method = tokens[0]
                                    filename = tokens[1]
                                    filesize = 0
                                    try:
                                        filesize = int(tokens[2])
                                    except:pass
                                    chunkb64 = tokens[3]
                                    if fopen is None:
                                        if filename!='':
                                            fopen = open(filename,'wb')
                                    if fopen:
                                        chunk = base64.b64decode(chunkb64)
                                        chunk_por += len(chunk)
                                        size_per_second+=len(chunk)
                                        tcurrent = time.time() - time_start
                                        time_total += tcurrent
                                        time_start = time.time()
                                        if time_total>=1:
                                            clock_time = (filesize - chunk_por) / (size_per_second)
                                            if progressfunc:
                                                progressfunc(self,filename,chunk_por,filesize,size_per_second,clock_time,args)
                                            time_total = 0
                                            size_per_second = 0
                                        fopen.write(chunk)
                                        pass
                                    lastresplist.append(resp)
                                pass
                            if len(lastresplist)>=10:
                                     self.send_message('END RESP LIST')
            except Exception as ex:
                print(str(ex))
        if fopen:
            fopen.close()
        return filename
#end vpn object
# utils
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
def nice_time(delta):
    weeks = 0
    days = 0
    hours = 0
    minutes = 0
    seconds = 0
    seconds_in_minute = 60
    seconds_in_hour = 60 * seconds_in_minute
    seconds_in_day = 24 * seconds_in_hour
    seconds_in_week = 7 * seconds_in_day
    weeks = delta / seconds_in_week
    if weeks != 0:
        delta -= weeks * seconds_in_week
    days = delta / seconds_in_day
    if days != 0:
        delta -= days * seconds_in_day
    hours = delta / seconds_in_hour
    if hours != 0:
        delta -= hours * seconds_in_hour
    minutes = delta / seconds_in_minute
    if minutes != 0:
        delta -= minutes * seconds_in_minute
    seconds = delta
    out = ""
    if seconds:
        out = "%ss" % seconds + out
    if minutes:
        out = "%sm" % minutes + out
    if hours:
        out = "%sh" % hours + out
    if days:
        out = "%sd" % days + out
    if weeks:
        out = "%sw" % weeks + out
    if out == "":
        return "just now"
    return out
#end utils
#download vpn
def progress(vpn,filename,read_bytes,total_bytes,speed,time,args):
    read_bytes = sizeof_fmt(read_bytes)
    total_bytes = sizeof_fmt(total_bytes)
    speed = sizeof_fmt(speed)
    print(f'{filename} - {read_bytes}/{total_bytes} - {speed}/s')
vpn = MVPN('https://aulacened.uci.cu/','obiiii','Obysoft2001@')
loged = vpn.login()
if loged:
    print('ENVIE UN ENLACE:')
    #url = input()
    url = 'https://www.7-zip.org/a/7z2107.exe'
    filepath = vpn.download_url(url,progressfunc=progress)
    print(filepath + ' Downloaded!')
#end download vpn