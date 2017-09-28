from django.shortcuts import render,HttpResponse
import requests
import time,re,json
# Create your views here.
CURRENT_TIME =None
QCODE = None

LOGIN_COOKIE_DICT = {} #用来将每一次的cookie给保存起来
TICKET_COOKIE_DICT = {} # 票据cookie的字典
TICKET_DICT = {} #票据的字典
TIPS = 1

USRE_INIT_DATA = {}
BASE_URL = "http://wx.qq.com"
BASE_SYNC_URL = 'https://webpush.weixin.qq.com'

def login(request):
    base_qcode_url = 'https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_={0}'
    global CURRENT_TIME
    CURRENT_TIME = str(time.time())
    q_code_url =base_qcode_url.format(CURRENT_TIME)
    response = requests.get(q_code_url) #得到随机字符串
    #print(response.text)
    code = re.findall('uuid = "(.*)";',response.text)[0]
    global QCODE
    QCODE = code
    return  render(request,'login.html',{'code':QCODE})

def long_polling(request):
    ret = {'status':408,'data':None}
    # 要发送这个请求
    #https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=gYfeF_hjRg==&tip=1&r=2062685809&_=1505470834005

    global TIPS
    base_login_url = 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip={1}&r=2060816902&_={2}'
    login_url = base_login_url.format(QCODE,TIPS,CURRENT_TIME)
    response_login = requests.get(login_url)
    #print(response_login.text)
    # 获取到是201 之后就 获取到这个路径
    if "window.code=201" in response_login.text:
        TIPS = 0
        avatar = re.findall("userAvatar = '(.*)';",response_login.text)[0] # 将这个值赋值给data
        ret['data'] = avatar
        ret['status'] = 201
    elif "window.code=200" in response_login.text:
        # 注意这个地方，涉及到登录，会有这个，也可会有cookie,每一次的cookie都让保存起来
        # 当登录成功之后把cookie给拿出来
        LOGIN_COOKIE_DICT.update(response_login.cookies.get_dict())
        # 拿到了cookie，现在拿结果
        redirect_uri = re.findall('redirect_uri="(.*)";',response_login.text)[0]

        global BASE_URL
        global BASE_SYNC_URL
        if redirect_uri.startswith('https://wx2.qq.com'):
            BASE_URL = 'https://wx2.qq.com'
            BASE_SYNC_URL = 'https://webpush.wx2.qq.com'
        elif redirect_uri.startswith('https://wx1.qq.com'):
            BASE_URL = 'https://wx1.qq.com'
            BASE_SYNC_URL = 'https://webpush.wx2.qq.com'
        else:
            BASE_URL = 'https://wx.qq.com'
            BASE_SYNC_URL = 'https://webpush.wx.qq.com'


        redirect_uri += '&fun=new&version=v2&lang=zh_CN'
        # 但是这个url是干嘛的呢？，获取票据cookie，返回值
        response_ticket = requests.get(redirect_uri,cookies=LOGIN_COOKIE_DICT)
        TICKET_COOKIE_DICT.update(response_ticket.cookies.get_dict()) # 得到票据cookie里面的字典
        #print(response_ticket.text) # 返回了一大堆的html
        # 拿到这些值，把这些值放在ticket中
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response_ticket.text,'html.parser')
        for tag in soup.find():
            TICKET_DICT[tag.name] = tag.string  # tag.name 标签名字，tag.string 标签中的内容
        ret['status'] = 200


        #https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=A1fPZEuwjJHnuoyL4_605KPu@qrticket_0&uuid=QYt_S09Ilg==&lang=zh_CN&scan=1505476340&fun=new&version=v2
        # 这个url里面有ticket , 这里面的ticket 在上面就会返回的有，
    return HttpResponse(json.dumps(ret))


def index(request):
    '''获取用户的基本信息'''
    # 要获取基本信息就要拿到这个url
    #https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=2054581598&pass_ticket=99p6qNzg1NpP%252FpOkBNGDdN1DJ%252BxFjkLsOX3ErtEoY0DEOjuplBcuzfwiY90c8aYO
    #user_init_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=zh_CN&pass_ticket=%s' %(int(time.time()),TICKET_DICT['pass_ticket'])
    user_init_url = '%s/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=zh_CN&pass_ticket=%s' %(BASE_URL,int(time.time()),TICKET_DICT['pass_ticket'])

    form_data = {
        'BaseRequest':{
            "DeviceID":"e488880140765296",
            "Sid":TICKET_DICT['wxsid'],
            "Skey":TICKET_DICT['skey'],
            "Uin":TICKET_DICT['wxuin']
        }
    }

    # 将所有的cookie 放在一起
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)

    #post(url, data=None, json=None, **kwargs):
    # 发送请求
    response_init = requests.post(user_init_url,json=form_data,cookies=all_cookie_dict)
    response_init.encoding = 'utf-8'
    user_init_data = json.loads(response_init.text)
    #print(response_init.text)
    USRE_INIT_DATA.update(user_init_data)
    return render(request,'index.html',{'data':user_init_data})



def contact_list(request):
    """联系人列表"""
    #https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket=S0%252B7W97hh%252Bs9BiKNsWV%252FI%252B0Pv2ltfEx80h1%252BHOccMDz9fenXwJLxoYTW7z9%252F7Ura&r=1505531816738&seq=0&skey=@crypt_51c630c9_38c23d3f69434d5b230e4e26b48ff83b

    base_url ="https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={0}&r={1}&seq=0&skey={2}"
    url = base_url.format(TICKET_DICT['pass_ticket'],str(time.time()),TICKET_DICT['skey'])
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)

    response = requests.get(url,cookies=all_cookie_dict)
    response.encoding = 'utf-8'

    print(response.text)
    contact_list_dict = json.loads(response.text)
    return render(request,'contact_list.html',{'obj':contact_list_dict})


def send_msg(request):
    from_user_id = USRE_INIT_DATA['User']['UserName']
    to_user_id = request.POST.get('user_id')
    msg = request.POST.get('user_msg')

    send_url =  BASE_URL + "/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=" + TICKET_DICT['pass_ticket']
    form_data = {
        'BaseRequest': {
            'DeviceID': 'e531777446530354',
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        },
        'Msg': {
            "ClientMsgId": str(time.time()),
            "Content": '%(content)s',
            "FromUserName": from_user_id,
            "LocalID": str(time.time()),
            "ToUserName": to_user_id,
            "Type": 1
        },
        'Scene': 0
    }

    form_data_str = json.dumps(form_data)
    #进行格式化
    form_data_str = form_data_str %{'content':msg}
    # 转化为字节
    form_data_bytes = bytes(form_data_str,encoding='utf-8') # 为什么要这样转化呢
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)
    response = requests.post(send_url,data=form_data_bytes,cookies=all_cookie_dict,headers = {
        'Content-Type': 'application/json'
    })
    return HttpResponse('ok')

def get_msg(request):
    # 同步url
    sync_url = BASE_SYNC_URL + "/cgi-bin/mmwebwx-bin/synccheck"
    sync_data_list = []
    for item in USRE_INIT_DATA['SyncKey']['List']:
        temp = "%s_%s" % (item['Key'],item['Val'])
        sync_data_list.append(temp)
    sync_data_str = "|".join(sync_data_list)
    nid = int(time.time())
    sync_dict = {
        "r": nid,
        "skey": TICKET_DICT['skey'],
        "sid": TICKET_DICT['wxsid'],
        "uin": TICKET_DICT['wxuin'],
        "deviceid": "e531777446530354",
        "synckey": sync_data_str
    }
    all_cookie = {}
    all_cookie.update(LOGIN_COOKIE_DICT)
    all_cookie.update(TICKET_COOKIE_DICT)
    response_sync = requests.get(sync_url,params=sync_dict,cookies=all_cookie)
    if 'selector:"2"' in response_sync.text:
        fetch_msg_url = "%s/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=zh_CN&pass_ticket=%s" % (
        BASE_URL, TICKET_DICT['wxsid'], TICKET_DICT['skey'], TICKET_DICT['pass_ticket'])

        form_data = {
            'BaseRequest': {
                'DeviceID': 'e531777446530354',
                'Sid': TICKET_DICT['wxsid'],
                'Skey': TICKET_DICT['skey'],
                'Uin': TICKET_DICT['wxuin']
            },
            'SyncKey': USRE_INIT_DATA['SyncKey'],
            'rr': str(time.time())
        }
        response_fetch_msg = requests.post(fetch_msg_url, json=form_data)
        response_fetch_msg.encoding = 'utf-8'
        res_fetch_msg_dict = json.loads(response_fetch_msg.text)
        USRE_INIT_DATA['SyncKey'] = res_fetch_msg_dict['SyncKey']
        for item in res_fetch_msg_dict['AddMsgList']:
            print(item['Content'], ":::::", item['FromUserName'], "---->", item['ToUserName'], )
    return HttpResponse('ok')
