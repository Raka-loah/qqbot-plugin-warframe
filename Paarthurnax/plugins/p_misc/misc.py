import hashlib
import json
import os
import random
import re
import sqlite3
import time
import urllib.parse
import uuid

import requests
import requests_cache


def food(meal):
    dishlist = {
        'general': ['炒饭','炒面','泡面','煮面','匹萨','烧麦','拉肠','炒牛河','海带','炸鸡','关东煮','米线','面包','狗粮','盖浇饭','节食不吃','闭着眼点外卖','楼下的决定'],
        'breakfast': ['油条','糯米鸡','馅饼','肉包子','煎堆','素包子','糊辣汤','肉粥','甜粥','馒头','饭团','昨晚的剩饭','锅贴','生煎','冷面','馄饨','小笼','煎饼果子','大饼夹一切','豆儿汁儿','焦儿圈儿','卤煮','炒肝','肉夹馍','鸡蛋灌饼'],
        'lunch': ['宫保鸡丁','红烧肉','扬州狮子头','腌笃鲜','冒菜','缅甸菜','赛百味','麦当劳','肯德基','汉堡王','德克士','华莱士','鱼香肉丝','西红柿炒鸡蛋','排骨饭','麻辣香锅','水煮鱼','卤肉饭','鸡排饭','沙拉','黄焖鸡','酸菜鱼'],
        'dinner': ['馒头','火锅','傣族菜','漆油鸡','柠檬撒','汉堡包','寿喜烧','方便面','意大利面','通心粉','拉面','盖饭','麻辣香锅','麻辣烫','麻辣拌','鸭血粉丝','鸡公煲','糖醋里脊','糖醋排骨','熏鱼']
    }

    dishes = dishlist['general'] + dishlist[meal] if meal in dishlist.keys() else dishlist['general']

    msg = ' '.join(random.sample(dishes, k=3))

    return msg


def breakfast():
    return food('breakfast')


def lunch():
    return food('lunch')


def dinner():
    return food('dinner')


def general():
    return food('')


# def msg_fetch(group_id, sender_id, lines=5):
#     try:
#         db = sqlite3.connect('qqbot.sqlite')
#         cursor = db.cursor()
#         cursor.execute(
#             '''SELECT message FROM messages WHERE group_id = ? AND sender_id = ? ORDER BY timestamp DESC LIMIT ?''',
#             (group_id,
#              sender_id,
#              lines))
#         rows = cursor.fetchall()
#         msg = '以下为[CQ:at,qq=%s]发送的最后%s条记录（如果有）：' % (sender_id, lines)
#         for row in rows:
#             msg += '\n%s' % (row[0])
#         return msg
#     except BaseException:
#         db.close()
#         return '[ERROR] Database error'


def msg_stalker(self_id, group_id, sender_id, lines=5):
    try:
        # It's already cached in CQP client, caching again is redundant
        raw_memberlist = requests.get('http://127.0.0.1:5700/get_group_member_list?group_id={}'.format(group_id)).json()
        memberlist = []
        if raw_memberlist['data']:
            for member in raw_memberlist['data']:
                memberlist.append(str(member['user_id']))
        else:
            return '[ERROR] 目标群号错误或系统故障'
        if str(self_id) in memberlist:
            try:
                db = sqlite3.connect('qqbot.sqlite')
                cursor = db.cursor()
                lines = 20 if int(lines) > 20 else lines
                cursor.execute(
                    '''SELECT message FROM messages WHERE group_id = ? AND sender_id = ? ORDER BY timestamp DESC LIMIT ?''',
                    (group_id,
                     sender_id,
                     lines))
                rows = cursor.fetchall()
                msg = '以下为QQ:%s在%s发送的最后%s条记录（如果有）：' % (
                    sender_id, group_id, lines)
                for row in rows:
                    msg += '\n%s' % (row[0])
                return msg
            except BaseException:
                db.close()
                return '[ERROR] 目标群号错误或系统故障'
        else:
            return '[ERROR] 你不在目标群中，你这个Stalker'
    except BaseException:
        return '[ERROR] 目标群号错误或系统故障'


def msg_ar_wrapper(j, resp):
    # if j['message'].startswith('/echo'):
    #     query_id = re.match(r'.*\[CQ:at,qq=(.*)\].*', j['message'])
    #     if query_id and j['message_type'] == 'group':
    #         # return msg_fetch(j['group_id'], query_id.group(1))
    #         return '请私聊机器人 /stalk {} {} 5'.format(
    #             j['group_id'], query_id.group(1))

    if j['post_type'] == 'message' and j['message_type'] == 'private':
        query_id = re.match(r'.* (\d+) (\d+) (\d+)', j['message'])
        if query_id:
            resp['reply'] = msg_stalker(
                j['sender']['user_id'],
                query_id.group(1),
                query_id.group(2),
                query_id.group(3))
            return resp, 200
    return '', 204


def msg_executioner(j, resp):
    if j['message_type'] == 'group':
        try:
            db = sqlite3.connect('qqbot.sqlite')
            cursor = db.cursor()
            cursor.execute(
                '''SELECT timestamp, sender_id FROM messages WHERE group_id = ? ORDER BY timestamp DESC LIMIT 2''',
                (j['group_id'],
                 ))
            rows = cursor.fetchall()
            if len(rows) == 2:
                timespan = float(rows[0][0]) - float(rows[1][0])
                if timespan > 180 and rows[0][1] == rows[1][1] and random.randint(1, 10) == 1:
                    resp['reply'] = random.choice(['哦', '这样', '真的吗', '挽尊', '然后呢', '嗯嗯'])
            return resp, 200
        except BaseException:
            db.close()
            return '', 204
    return '', 204


def msg_nature_of_humanity(j, resp):
    if j['message_type'] == 'group':
        try:
            db = sqlite3.connect('qqbot.sqlite')
            cursor = db.cursor()
            cursor.execute(
                '''SELECT message, sender_id FROM messages WHERE group_id = ? ORDER BY timestamp DESC LIMIT 3''',
                (j['group_id'],
                 ))
            rows = cursor.fetchall()
            msg = ''
            # Exactly 3 messages, last two messages are identical, last third is not.
            # Repeat the last message, and ensure repeating only once.
            if len(rows) == 3:
                messages = [rows[0][0], rows[1][0], rows[2][0]]
                senders = [rows[0][1], rows[1][1], rows[2][1]]
                if messages[0] == messages[1] and messages[1] != messages[2] and senders[0] != senders[1]:
                    resp['reply'] = rows[0][0]
                    return resp, 200
        except BaseException:
            db.close()
            return '', 204
    return '', 204


def let_me_baidu_that_for_you(j):
    msg = ''
    keyword = j['message'].replace(j['keyword'], '')[:255].strip()
    skip = ['', '呀', '啊', '哇', '一下', '一下你就知道']
    if keyword in skip:
        return ''
    if j['message_type'] == 'group':
        msg = '请点击以下链接直达百度搜索“{}”：\nhttps://www.baidu.com/s?ie=utf8&wd={}'.format(
            keyword, urllib.parse.quote_plus(keyword))
    return msg


def music_share(j):
    msg = ''
    if j['message_type'] == 'group':
        song_name = j['message'].replace(j['keyword'], '')[:20].strip()
        try:
            data = requests.get('https://c.y.qq.com/soso/fcgi-bin/client_search_cp?g_tk=5381&p=1&n=20&w={}&format=json&loginUin=0&hostUin=0&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&remoteplace=txt.yqq.song&t=0&aggr=1&cr=1&catZhida=1'.format(urllib.parse.quote_plus(song_name)), timeout=30).json()
            msg = '[CQ:music,type=qq,id={}]'.format(
                data['data']['song']['list'][0]['songid'])
        except BaseException:
            try:
                data = requests.get(
                    'https://api.mlwei.com/music/api/wy/?key=523077333&id={}&type=so&cache=0&nu=1'.format(urllib.parse.quote_plus(song_name)), timeout=30).json()
                msg = '[CQ:music,type=163,id={}]'.format(data['Body'][0]['id'])
            except BaseException:
                msg = '[ERROR]点歌失败，网络错误'
    return msg


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)) ,'data' ,'tarot.json') , 'r', encoding='utf-8') as E:
    tarot_deck = json.loads(E.read())


def draw_tarot(j):
    msg = ''
    draw_num = re.match(r'.* (\d)', j['message'])
    try:
        if draw_num:
            chosen_card = random.sample(tarot_deck, int(draw_num.group(1)))
            for card in chosen_card:
                msg += card['name'] + '\n'
                if random.randint(0, 1) == 0:
                    msg += card['desc'] + '\n'
                else:
                    msg += card['rdesc'] + '\n'
                msg += '\n'
            msg = msg[:-2]
        else:
            raise ValueError('No match')
    except BaseException:
        chosen_card = random.choice(tarot_deck)
        msg = chosen_card['name'] + '\n'
        if random.randint(0, 1) == 0:
            msg += chosen_card['desc']
        else:
            msg += chosen_card['rdesc']

    return msg


def msg_random_picture_rating(j):
    if j['message_type'] == 'group':
        try:
            db = sqlite3.connect('qqbot.sqlite')
            cursor = db.cursor()
            cursor.execute(
                '''SELECT message FROM messages WHERE group_id = ? AND message like '[CQ:image,file=%' ORDER BY timestamp DESC LIMIT 1''',
                (j['group_id'],
                 ))
            rows = cursor.fetchall()
            msg = ''
            raw_score = re.match(r'\[CQ\:image\,file\=(.).*\]', rows[0][0])
            rate = [
                '负分',
                '负分',
                '负分',
                'F',
                'F',
                'E',
                'D-',
                'D',
                'C-',
                'C',
                'B',
                'A',
                'A+',
                'S',
                'SS',
                'SSS']
            if raw_score:
                msg = rate[int(raw_score.group(1), 16)]
            return msg
        except BaseException:
            db.close()
            return ''
    return ''


def msg_translate(j):
    msg = ''
    source_text = j['message'].replace(j['keyword'], '', 1).strip()
    if len(source_text) > 0:
        try:
            appid = ''
            secretKey = ''
            payload = {
                'q': '',
                'from': 'auto',
                'to': 'zh',
                'appid': appid,
                'salt': '',
                'sign': ''
            }
            payload['q'] = source_text
            payload['salt'] = str(random.randint(32768, 65536))
            m = hashlib.md5()
            m.update(
                (appid +
                 payload['q'] +
                    payload['salt'] +
                    secretKey).encode('utf-8'))
            payload['sign'] = m.hexdigest()
            url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
            response = requests.post(url, data=payload)
            result = response.json()
            msg = '{} =>\n{}'.format(
                result['trans_result'][0]['src'],
                result['trans_result'][0]['dst'])
        except BaseException:
            msg = ''
    return msg


def msg_translate_bing(j, to='zh'):
    msg = ''
    source_text = j['message'].replace(j['keyword'], '', 1).strip()
    if len(source_text) > 0:
        try:
            subscriptionKey = '' # Refer to https://docs.microsoft.com/zh-cn/azure/cognitive-services/translator/quickstart-python-translate
            if 'TRANSLATOR_TEXT_KEY' in os.environ:
                subscriptionKey = os.environ['TRANSLATOR_TEXT_KEY']
            else:
                raise ValueError('No subscription key')

            url = 'https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={}'.format(to)
            headers = {
                'Ocp-Apim-Subscription-Key': subscriptionKey,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }
            body = [{
                    'text': source_text
                    }]
            request = requests.post(url, headers=headers, json=body)
            response = request.json()

            if request.status_code == 200:
                msg = '{} =>\n{}'.format(
                    source_text, response[0]['translations'][0]['text'])
        except BaseException:
            msg = ''
    return msg

def msg_translate_bing_2en(j):
    return msg_translate_bing(j, 'en')


def msg_bankrupt(j):
    return random.choice(['没有哦', '快了哦', '马上哦', '还没哦'])


data_dict = {}
#with open(os.path.dirname(os.path.abspath(__file__)) + '\\data\\demotivational.json', 'r', encoding='utf-8') as E:
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)) ,'data' ,'demotivational.json') , 'r', encoding='utf-8') as E: 
    data_dict['d'] = json.loads(E.read())


def msg_demotivational(j):
    return random.choice(data_dict['d'])


#with open(os.path.dirname(os.path.abspath(__file__)) + '\\data\\tackypickuplines.json', 'r', encoding='utf-8') as E:
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)) ,'data' ,'tackypickuplines.json') , 'r', encoding='utf-8') as E: 
    data_dict['t'] = json.loads(E.read())


def msg_tackypickuplines(j):
    return random.choice(data_dict['t'])


rr_init = {}
rr_stat = {}
rr_banned = {}
rr_max_round = 180
rr_ban_duration = 300
rr_magazine = 6

def russian_roulette(j):
    msg = ''
    if j['message_type'] == 'group':
        if time.time() - rr_init.get(j['group_id'], 0) > rr_max_round:
            rr_init[j['group_id']] = time.time()
            rr_stat[j['group_id']] = [0] * rr_magazine
            rr_stat[j['group_id']][random.randint(0, 5)] = 1
            msg += '新一轮开始。'

        if rr_stat[j['group_id']].pop() == 1:
            rr_init[j['group_id']] = 0
            msg += 'Bang！'
            payload = {
                'group_id': j['group_id'],
                'user_id': j['sender']['user_id'],
                'duration': rr_ban_duration
            }
            try:
                if j['sender']['user_id'] not in rr_banned:
                    rr_banned[j['sender']['user_id']] = {}
                rr_banned[j['sender']['user_id']][j['group_id']] = time.time()
                requests.post(
                    f'{j["base_url"]}/set_group_ban',
                    json=payload)
            except BaseException:
                return ''
        else:
            msg += '*咔哒*\n剩余次数{}，本轮将在{:.0f}秒后结束。'.format(len(
                rr_stat[j['group_id']]), rr_max_round - (time.time() - rr_init[j['group_id']]))
    elif j['message_type'] == 'private':
        if j['sender']['user_id'] in rr_banned:
            for group_id, ban_init in rr_banned[j['sender']['user_id']].items(
            ):
                if time.time() - ban_init <= rr_ban_duration:
                    payload = {
                        'group_id': group_id,
                        'user_id': j['sender']['user_id'],
                        'duration': 0
                    }
                    try:
                        del rr_banned[j['sender']['user_id']][group_id]
                        requests.post(
                            f'{j["base_url"]}/set_group_ban', json=payload)
                    except BaseException:
                        return ''
                return '由/rr产生的禁言已解除。'
    return msg


def misc_roll(j):
    msg = ''

    max_dices = 10
    max_faces = 1000

    # default to 1d100+0
    dice_num = 1
    dice_faces = 100
    dice_modifier = '+'
    dice_modifier_num = 0

    # xdy+z format
    dices = re.match(r'.* (\d+)[dD](\d+)([\+\-])(\d+)', j['message'])
    if dices:
        dice_num = int(
            dices.group(1)) if 0 < int(
            dices.group(1)) <= max_dices else max_dices
        dice_faces = int(dices.group(2)) if 0 < int(
            dices.group(2)) <= max_faces else max_faces
        dice_modifier = dices.group(3)
        dice_modifier_num = int(dices.group(4))
    else:
        # xdy format
        dices = re.match(r'.* (\d+)[dD](\d+)', j['message'])
        if dices:
            dice_num = int(
                dices.group(1)) if 0 < int(
                dices.group(1)) <= max_dices else max_dices
            dice_faces = int(
                dices.group(2)) if 0 < int(
                dices.group(2)) <= max_faces else max_faces
        else:
            # only a number
            dices = re.match(r'.* (\d+)', j['message'])
            if dices:
                dice_num = 1
                dice_faces = int(
                    dices.group(1)) if 0 < int(
                    dices.group(1)) <= max_faces else max_faces

    results = []

    try:
        for _ in range(0, dice_num):
            results.append(random.randint(1, dice_faces))
    except BaseException:
        dice_num = 1
        dice_faces = 100
        results.append(random.randint(1, 100))

    if len(results) <= 1:
        if dice_modifier_num > 0:
            msg = '{} {} {} = {}'.format(
                results[0],
                dice_modifier,
                dice_modifier_num,
                results[0] +
                dice_modifier_num if dice_modifier == '+' else results[0] -
                dice_modifier_num)
        else:
            msg = str(results[0])
    else:
        if dice_modifier_num > 0:
            msg = '('
            sum_dices = 0
            for result in results:
                msg += str(result) + ','
                sum_dices += result
            msg = msg[:-1]
            msg += ') {} {} = {}'.format(
                dice_modifier,
                dice_modifier_num,
                sum_dices +
                dice_modifier_num if dice_modifier == '+' else sum_dices -
                dice_modifier_num)
        else:
            msg = '('
            sum_dices = 0
            for result in results:
                msg += str(result) + ','
                sum_dices += result
            msg = msg[:-1]
            msg += ') = {}'.format(sum_dices)

    if msg != '':
        if dice_modifier_num > 0:
            return 'Roll({}d{}{}{}): {}'.format(
                dice_num, dice_faces, dice_modifier, dice_modifier_num, msg)
        else:
            return 'Roll({}d{}): {}'.format(dice_num, dice_faces, msg)
    else:
        return ''


def ask_8ball(j):
    replies = [
        '当然YES咯',
        '我觉得OK',
        '毫无疑问',
        '妥妥儿的',
        '你就放心吧',
        '让我说的话，YES',
        '基本上没跑了',
        '看起来没问题',
        'YES',
        '我听卡德加说YES，那就YES吧',
        '有点复杂，再试一次',
        '过会儿再问我',
        '我觉得还是别剧透了',
        '放飞自我中，过会儿再问',
        '你心不够诚，再试一次',
        '我觉得不行',
        '我必须说NO',
        '情况不容乐观',
        '我觉得根本就是NO',
        '我持怀疑态度']
    return random.choice(replies)


stella_ban_duration = 180

def msg_stella(j):
    msg = ''
    bot_role = ''
    if j['message_type'] == 'group':
        try:
            r = requests.get('http://10.11.68.115:5700/get_group_member_info?group_id={}&user_id={}'.format(j['group_id'], j['self_id']), timeout=30).json()
            bot_role = r['data']['role']
        except BaseException:
            pass
        if bot_role == 'admin' or bot_role == 'owner':
            target = re.match(r'.*\[CQ:at,qq=(\d+)\]', j['message'])
            if target:
                target_id = target.group(1)
                payload_self = {
                    'group_id': j['group_id'],
                    'user_id': j['sender']['user_id'],
                    'duration': stella_ban_duration
                }
                payload_target = {
                    'group_id': j['group_id'],
                    'user_id': target_id,
                    'duration': stella_ban_duration
                }
                try:
                    if random.randint(0, 1) > 0 and j['sender']['user_id'] != target_id:
                        requests.post('http://127.0.0.1:5700/set_group_ban_rate_limited', json=payload_self)
                        requests.post('http://127.0.0.1:5700/set_group_ban_rate_limited', json=payload_target)
                        msg = 'Stella发动成功！[CQ:at,qq={}]被同时禁言！'.format(target_id)
                    else:
                        requests.post('http://127.0.0.1:5700/set_group_ban_rate_limited', json=payload_self)
                        msg = 'Stella发动失败，你被单独禁言！'
                except BaseException:
                    pass
            else:
                msg = '未指定Stella的目标。'
    elif j['message_type'] == 'private':
        msg = 'Stella产生的禁言无法自助解除，请联系其他管理员。'
    return msg


def msg_aqi(j):
    token = '' # Get yours on http://aqicn.org/data-platform/token/#/
    msg = ''

    pol_dict = {
        'pm25': 'PM2.5',
        'pm10': 'PM10',
        'co': '一氧化碳',
        'no2': '二氧化氮',
        'o3': '臭氧',
        'so2': '二氧化硫',
    }

    match = re.match(r'.* \@(\d+)', j['message'])

    if match:
        try:
            api_data = requests.get('https://api.waqi.info/feed/@{}/?token={}'.format(match.group(1), token), timeout=30).json()
            if api_data['status'] != 'ok':
                raise 'API ERROR'
        except BaseException:
            return '[ERROR]天气信息获取失败。'
        
        data = api_data['data']
        msg = '城市或监测站：{}\nAQI：{}({})\n主要污染物：{}'.format(data['city']['name'], data['aqi'], aqi_level(data['aqi']), pol_dict[data['dominentpol']])
        
        msg += '\n污染物指数：'
        for pol in data['iaqi']:
            if pol in pol_dict:
                msg += '\n{}：{}'.format(pol_dict[pol], data['iaqi'][pol]['v'])
    else:
        try:
            keyword = j['message'].replace('/aqi', '', 1).strip()
            if len(keyword) > 0:
                api_data = requests.get('https://api.waqi.info/search/?keyword={}&token={}'.format(keyword, token), timeout=30).json()
            else:
                return '请指定要搜索的城市或监测站的名称。'
            if api_data['status'] != 'ok':
                raise 'API ERROR'
        except BaseException:
            return '[ERROR]天气信息获取失败。'

        data = api_data['data']
        msg = '根据关键字搜索到的城市或监测站：\n'

        for station in data:
            msg += '@{}：{}，AQI {}\n'.format(station['uid'], station['station']['name'], station['aqi'])
        
        msg += '详细信息可使用/aqi @数字id进行查询。'

    return msg

def aqi_level(aqi):
    aqi = int(aqi)
    if 0 <= aqi <= 50:
        return '优'
    elif 51 <= aqi <= 100:
        return '良'
    elif 101 <= aqi <= 150:
        return '轻度污染'
    elif 151 <= aqi <= 200:
        return '中度污染'
    elif 201 <= aqi <= 300:
        return '重度污染'
    elif aqi >= 301:
        return '严重污染'
    return '?'


def msg_exchange_rate(j):
    '''API: https://exchangeratesapi.io/

    No APPKEY needed, slightly inaccurate for Chinese players.
    '''
    msg = ''
    match = re.match(r'.*?(\d+\.*\d*).*?([A-Za-z]{3})', j['message'])
    if match:
        try:
            r = requests_cache.CachedSession(backend='sqlite', cache_name='er_cache', expire_after=3600)
            er = r.get('https://api.exchangeratesapi.io/latest?base=CNY', timeout=30).json()
            if match.group(2).upper() in er['rates']:
                if match.group(2).upper() == 'CNY':
                    return '按……等一下你是认真的吗？ {} CNY = {} CNY（确信）'.format(match.group(1), match.group(1))
                return '按当前汇率：{} {} = {:.3f} CNY ({:.3f})'.format(match.group(1), match.group(2).upper(), float(match.group(1)) / float(er['rates'][match.group(2).upper()]), 1 / float(er['rates'][match.group(2).upper()]))
            else:
                return '目前尚未有货币{}的汇率。'.format(match.group(2).upper())
        except BaseException:
            return ''
    msg = '命令格式：/汇率 数字 货币种类，支持小数点，货币种类如USD EUR HKD等。'
    return msg

def msg_exchange_rate_2(j):
    '''API: https://www.juhe.cn/docs/api/id/23

    Require APPKEY. More accurate for Chinese players.
    '''
    msg = ''
    appkey = '' # Your APPKEY here
    code = {
        '人民币': 'CNY',
        '美元': 'USD',
        '日元': 'JPY',
        '欧元': 'EUR',
        '英镑': 'GBP',
        '韩元': 'KRW',
        '港币': 'HKD',
        '澳大利亚元': 'AUD',
        '加拿大元': 'CAD',
        '阿尔及利亚第纳尔': 'DZD',
        '阿根廷比索': 'ARS',
        '爱尔兰镑': 'IEP',
        '埃及镑': 'EGP',
        '阿联酋迪拉姆': 'AED',
        '阿曼里亚尔': 'OMR',
        '奥地利先令': 'ATS',
        '澳门元': 'MOP',
        '百慕大元': 'BMD',
        '巴基斯坦卢比': 'PKR',
        '巴拉圭瓜拉尼': 'PYG',
        '巴林第纳尔': 'BHD',
        '巴拿马巴尔博亚': 'PAB',
        '保加利亚列弗': 'BGN',
        '巴西雷亚尔': 'BRL',
        '比利时法郎': 'BEF',
        '冰岛克朗': 'ISK',
        '博茨瓦纳普拉': 'BWP',
        '波兰兹罗提': 'PLN',
        '玻利维亚诺': 'BOB',
        '丹麦克朗': 'DKK',
        '德国马克': 'DEM',
        '法国法郎': 'FRF',
        '菲律宾比索': 'PHP',
        '芬兰马克': 'FIM',
        '哥伦比亚比索': 'COP',
        '古巴比索': 'CUP',
        '哈萨克坚戈': 'KZT',
        '荷兰盾': 'NLG',
        '加纳塞地': 'GHC',
        '捷克克朗': 'CZK',
        '津巴布韦元': 'ZWD',
        '卡塔尔里亚尔': 'QAR',
        '克罗地亚库纳': 'HRK',
        '肯尼亚先令': 'KES',
        '科威特第纳尔': 'KWD',
        '老挝基普': 'LAK',
        '拉脱维亚拉图': 'LVL',
        '黎巴嫩镑': 'LBP',
        '林吉特': 'MYR',
        '立陶宛立特': 'LTL',
        '卢布': 'RUB',
        '罗马尼亚新列伊': 'RON',
        '毛里求斯卢比': 'MUR',
        '蒙古图格里克': 'MNT',
        '孟加拉塔卡': 'BDT',
        '缅甸缅元': 'BUK',
        '秘鲁新索尔': 'PEN',
        '摩洛哥迪拉姆': 'MAD',
        '墨西哥比索': 'MXN',
        '南非兰特': 'ZAR',
        '挪威克朗': 'NOK',
        '葡萄牙埃斯库多': 'PTE',
        '瑞典克朗': 'SEK',
        '瑞士法郎': 'CHF',
        '沙特里亚尔': 'SAR',
        '斯里兰卡卢比': 'LKR',
        '索马里先令': 'SOS',
        '泰国铢': 'THB',
        '坦桑尼亚先令': 'TZS',
        '土耳其新里拉': 'TRY',
        '突尼斯第纳尔': 'TND',
        '危地马拉格查尔': 'GTQ',
        '委内瑞拉玻利瓦尔': 'VEB',
        '乌拉圭新比索': 'UYU',
        '西班牙比塞塔': 'ESP',
        '希腊德拉克马': 'GRD',
        '新加坡元': 'SGD',
        '新台币': 'TWD',
        '新西兰元': 'NZD',
        '匈牙利福林': 'HUF',
        '牙买加元': 'JMD',
        '义大利里拉': 'ITL',
        '印度卢比': 'INR',
        '印尼盾': 'IDR',
        '以色列谢克尔': 'ILS',
        '约旦第纳尔': 'JOD',
        '越南盾': 'VND',
        '智利比索': 'CLP',
        '白俄罗斯卢布': 'BYR'
    }
    match = re.match(r'.*?(\d+\.*\d*).*?([A-Za-z]{3})', j['message'])
    if match:
        try:
            r = requests_cache.CachedSession(backend='sqlite', cache_name='er_cache', expire_after=72000)
            er = r.get('http://web.juhe.cn:8080/finance/exchange/rmbquot?type=1&bank=0&key={}'.format(appkey), timeout=30).json()
            er_processed = {}
            for currency in er['result'][0]:
                if currency in code:
                    er_processed[code[currency]] = er['result'][0][currency]['bankConversionPri']

            if match.group(2).upper() in er_processed:
                if match.group(2).upper() == 'CNY':
                    return '按……等一下你是认真的吗？ {} CNY = {} CNY（确信）'.format(match.group(1), match.group(1))
                return '按当前汇率：{} {} = {:.4f} CNY ({:.4f})'.format(match.group(1), match.group(2).upper(), float(match.group(1)) * float(er_processed[match.group(2).upper()]) / 100, float(er_processed[match.group(2).upper()]) / 100)
            else:
                return '目前尚未有货币{}的汇率。'.format(match.group(2).upper())
        except BaseException:
            return ''
    msg = '命令格式：/汇率 数字 货币种类，支持小数点，货币种类如USD EUR HKD等。'
    return msg

def ac_turnip(j):
    msg = ''
    match = re.match(r'.* (\d{1,3}) (\d{1,3})', j['message'])
    if match:
        try:
            if 90 <= int(match.group(1)) <= 110:
                rate = float(match.group(2)) / float(match.group(1))
                rate_str = f'比例为{rate * 100:.2f}%（{match.group(2)}/{match.group(1)}）'
                wave = f'\n【波动型】最大值{int(match.group(1))*0.9:.0f}~{int(match.group(1))*1.4:.0f}。'
                three = f'\n【3期型】最大值{int(match.group(1))*2.0:.0f}~{int(match.group(1))*6.0:.0f}。'
                four = f'\n【4期型】最大值{int(match.group(1))*1.4:.0f}~{int(match.group(1))*2.0:.0f}。'
                if rate >= 0.91:
                    msg = f'{rate_str}，预测为【波动型】或【4期型】。{wave}{four}'
                elif rate >= 0.85:
                    msg = f'{rate_str}，预测为【递减型】或【3期型】或【4期型】。{three}{four}'
                elif rate >= 0.80:
                    msg = f'{rate_str}，预测为【3期型】或【4期型】。{three}{four}'
                elif rate >= 0.60:
                    msg = f'{rate_str}，预测为【波动型】或【4期型】。{wave}{four}'
                else:
                    msg = f'{rate_str}，预测为【4期型】。{four}'
            else:
                msg = f'错误：购入价格必须位于90~110区间。'
        except:
            pass
    else:
        msg = f'命令格式：{j["keyword"]} 购入价格 周一上午价格'
    return msg