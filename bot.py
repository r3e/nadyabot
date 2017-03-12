# -*- coding: utf-8 -*-
"""
This module contains definition of vk chatbot class which uses VK API
Todo: import bot
"""
import sys
import os
import errno
import datetime
from time import sleep
from random import randint
import vk


"""
config file parsing parameters
"""
CONFIG_FMTS = '###'
CONFIG_COMMENT = '#'
CONFIG_ARG_DELIM = '|'
CONFIG_ARG_STR_DELIM = '('
CONFIG_BLOCK_INDEX = 0
REPLYCS_BLOCK_INDEX = 2
"""
frequency parameters
"""

TICK_TIME = 1       # seconds
ANSWER_TIME = 7     # seconds
REFRESH_TIME = 47   # seconds
REQUEST_PER_SECOND = 3 #
STATS_UPDATE_TIME = 50
wait_between_req = 1 / REQUEST_PER_SECOND
"""
answer parameters
"""
MESSAGES_COUNT = 3  # how much msgs should bot answer
SYMBOLS_COUNT = 50  # how much symbols should bot get per message
"""
command parameters
"""
COMMAND_SYMBOL = '#'    # to send command, you should write <COMMAND_SYMBOL><botname> <command>
KICK_TIME = 30
KICK_TIME_INT = 5

"""
repost parameters
"""
MAXIMUM_POSTS = 20

class Bot:
    """vk bot class"""
    phrases = {}
    name = "bot"
    API = 0
    tick = 0
    stats = 0
    current_stats = {'msg': 0, 'posts': 0, 'uptime': 0}
    global_stats = {'msg': 0, 'posts': 0, 'uptime': 0}
    parameters = {}
    replycs = {}
    commands = {}
    other = {}
    config=0
    start_time = 0
    votekick = {'+': 0, '-': 0, 'voted':[]}
    answered_messages = {'before': [], 'now': [], 'count': 0}
    sent_posts = {'before': [], 'now': [], 'count': 0}
    uptime = 0
    def __init__(self, API, name):
        self.name = name
        self.API = API
        self.stats = name + '.stats'
        self.attributes = name + '.attributes'
        self.config = name + '.config'
        self.init_files()
        self.get_config()
        print(self.parameters['conversations'])
        print(self.replycs)
        self.start_time = self.API.utils.getServerTime()

        while True:
            sleep(TICK_TIME)
            self.tick += TICK_TIME

            try:
                if self.tick % ANSWER_TIME == 0:
                    print("trying to find messages")
                    self.answer(MESSAGES_COUNT)
                    self.answered_messages['count'] += len(self.answered_messages['now'])
                    self.answered_messages['before'] = self.answered_messages['now']
                    self.answered_messages['now'] = []
                    print(self.answered_messages)
                if self.tick % REFRESH_TIME == 0:
                    print("trying to repost")
                    self.refresh()
                    self.sent_posts['count'] += len(self.sent_posts['now'])
                    self.sent_posts['before'] = self.sent_posts['now']
                    self.sent_posts['now'] = []
                    print("posts:")
                    print(self.sent_posts)
                if self.tick % STATS_UPDATE_TIME == 0:
                    work_time = self.API.utils.getServerTime() - self.start_time
                    self.current_stats['uptime'] += work_time
                    self.current_stats['msg'] += self.answered_messages['count']
                    self.current_stats['posts'] += self.sent_posts['count']

                    if not(self.stats_add(self.answered_messages['count'], self.sent_posts['count'], work_time)):
                        self.start_time += work_time
                        self.sent_posts['count'] = 0
                        self.answered_messages['count'] = 0
                    else:
                        print("Stat write error!")
                    self.tick = 0


            except vk.exceptions.VkAPIError as e:
                print("API error:" + str(e.errno))

    def stats_add(self, msg, posts, work_time):
        try:
            statsfile = open(self.stats, 'r')
            lines = statsfile.readlines()
            self.global_stats['msg'] = msg + int(lines[0].split(' ')[1])
            self.global_stats['posts'] = posts + int(lines[1].split(' ')[1])
            self.global_stats['uptime'] = work_time + int(lines[2].split(' ')[1])
            statsfile.close()
        except OSError as e:
            print("Error reading statsfile")
            return -1
        try:
            statsfile = open(self.stats, 'w')
            statsfile.write("msg: " + str(self.global_stats['msg']) + "\nposts: " + str(self.global_stats['posts']) \
                            + "\nuptime: " + str(self.global_stats['uptime']))
        except OSError as e:
            print("Error writing to statsfile")
            return -1
        return 0


    def send_repost(self, post):
        print(post)

    def refresh(self, time_offset = REFRESH_TIME, count = MAXIMUM_POSTS):
        """
        gathers last posts from
        :param time_offset:
        :param count:
        :return:
        """
        msg = self.other['repost']
        conv = self.parameters['conversations']
        ll = [v for k, v in conv.items()]
        all = []
        for lst in ll:
            all.extend(lst)
        groups = set([x for x in all if x != ''])
        print(groups)
        posts_count = int(count / len(groups))
        time = self.API.utils.getServerTime()
        all = []
        for x in groups:
            sleep(wait_between_req)
            y = self.API.wall.get(owner_id=-int(x), count=posts_count, query='vk')['items']
            print(y)
            for post in y:
                if (time - int(post['date']) <= time_offset) and not(post['id'] in self.sent_posts['before']):
                    print(post)

                    all.append(post)

        if all:
            sendposts = [('wall' + str(x['owner_id']) + '_' + str(x['id'])) for x in all]

            print(sendposts)


            for k, v in conv.items():
                for x in sendposts:
                    if x.split('-')[1].split('_')[0] in v:
                        sleep(wait_between_req)
                        addr_id = k
                        if str(k)[0] == 'u':
                            addr_id = int(k[1:])
                        else:
                            addr_id = int(addr_id)
                            addr_id += 2000000000
                        self.API.messages.send(peer_id = addr_id, message = msg[randint(0, len(msg)-1)], attachment=x)
                        if not(int(x.split('_')[1]) in self.sent_posts['now']):
                            self.sent_posts['now'].append(int(x.split('_')[1]))

        else:

            return 0

    def commands_votekick(self, chatid, uid):
        users = self.API.messages.getChatUsers(chat_id=chatid, fields='first_name')
        sleep(wait_between_req)
        kickuser = [x for x in users if x['id'] == int(uid)]
        users = [x['id'] for x in users]
        if kickuser == []:
            self.API.messages.send(peer_id=int(chatid + 2000000000), message="Пользователь не найден, проверьте введённый id! \n")
            return 0
        else:
            kickuser = kickuser[0]
        self.API.messages.send(peer_id=int(chatid + 2000000000), message="Начинается голосование за кик пользователя\n" \
                                                                         + kickuser['first_name'] + ' ' + kickuser['last_name'] \
                               + "!\nГолосов \"за\": 0, Голосов \"против\": 0\nНапишите мне в личку '+', чтобы проголосовать \"ЗА\" \
                               кик.\nЧтобы проголосовать \"ПРОТИВ\" кика - пришлите '-'. (без кавычек)")
        time = 0
        sleep(wait_between_req)
        votes = self.votekick
        print(users)

        while time < KICK_TIME:
            messages = self.API.messages.get(count=10, time_offset=KICK_TIME_INT, preview_length=1)['items']
            #print([x for x in messages if not('chat_id' in x)])
            messages = [x for x in messages if x['user_id'] != kickuser['id'] and not(x['user_id'] in votes['voted']) \
                        and x['body'] in ['+', '-'] \
                        and not('chat_id' in x) \
                        and x['user_id'] in users]

            print(messages)

            if messages != []:
                for x in messages:
                    print('lol')
                    if x['body'] == '+':
                        votes['+'] += 1
                    else:
                        votes['-'] += 1
                    votes['voted'].append(x['user_id'])
                print(votes)
                self.API.messages.send(peer_id=int(chatid + 2000000000), \
                                       message="Ещё кое-кто проголосовал! (Голосование за кик " \
                                               + kickuser['first_name'] + ' ' + kickuser['last_name'] \
                                               + ")\nТекущее положение дел:\nГолосов 'за': " + str(votes['+']) \
                                               + "\nГолосов 'против': " + str(votes['-']))
            time += KICK_TIME_INT
            sleep(KICK_TIME_INT)
        sendmsg = "Голосование окончено! Виновник - " + kickuser['first_name'] + ' ' + kickuser['last_name'] + ".\n \
                    ЗА исключение: "  + str(votes['+']) \
                    + "\nПРОТИВ исключения: " + str(votes['-']) + '\n'
        if votes['+'] > votes['-']:
            sendmsg += "Голосованием было решено, что пользователь БУДЕТ ИСКЛЮЧЁН."
            self.API.messages.send(peer_id=int(chatid + 2000000000), message=sendmsg)
        else:
            sendmsg += "Голосованием было решено, что пользователь НЕ БУДЕТ ИСКЛЮЧЁН."
            self.API.messages.send(peer_id=int(chatid + 2000000000), message=sendmsg)

    def commands_users(self, chatid):
        users = self.API.messages.getChatUsers(chat_id=chatid, fields='first_name')
        sleep(wait_between_req)
        sendmsg = ''
        for x in range(0, len(users)):
            sendmsg += (str(x + 1) + '. ' + users[x]['last_name'] + ' ' + users[x]['first_name'] + ' ' + str(users[x]['id']) + "\n")
        self.API.messages.send(peer_id=int(chatid+2000000000), message= "Вот список пользователей чата \n" + sendmsg)
        sleep(wait_between_req)
        return 0

    def commands_showstats(self, chatid):
        sendmsg = "Вот моя скромная статистика \o/\nВ этот раз я ответила на " + str(self.current_stats['msg']) + " сообщений (всего - " + \
            str(self.global_stats['msg']) + " сообщений)\nПереслала " + str(self.current_stats['posts']) + " постов (всего - " + \
            str(self.global_stats['posts']) + " постов)\n"
        sendmsg+= "А проработала уже " + str(datetime.timedelta(seconds=self.current_stats['uptime'])) +\
            "часоминутосекунд (всего - " + str(datetime.timedelta(seconds=self.global_stats['uptime'])) + ")!\nКогда перерыв?"
        self.API.messages.send(peer_id=int(chatid + 2000000000), message=sendmsg)

    def command(self, commandmsg):
        uid = commandmsg['user_id']
        api = self.API
        txt = [x.lower() for x in commandmsg['body'].split(' ')][1:]
        if 'chat_id' in commandmsg:
            addr_id = int(commandmsg['chat_id']) + 2000000000
        else:
            addr_id = uid
        if txt[0] == "members":
            self.commands_users(commandmsg['chat_id'])
        elif txt[0] == "votekick":
            self.commands_votekick(commandmsg['chat_id'], int(txt[1]))
        elif txt[0] == "poweroff":
            self.API.messages.send(peer_id=int(commandmsg['chat_id'] + 2000000000), \
                                   message="Выключаюсь... Ту-ту-ту-туууу... ")
            sys.exit(0)
        elif txt[0] == "стата":
            self.commands_showstats(commandmsg['chat_id'])

        return 0

    def answer_message(self, message):
        """
        parse message, send proper answer
        :param message:
        :return:
        """
        uid = message['user_id']
        api = self.API
        txt = [x.lower() for x in message['body'].split(' ')]
        if txt[0] in self.parameters['pseudonames']:
            txt = txt[1:]
        else:
            return 0
        txt = ' '.join(txt)
        repl = self.replycs
        print(message)
        if 'chat_id' in message:
            addr_id = int(message['chat_id']) + 2000000000
        else:
            addr_id = uid
        print(txt)
        admins = [int(x) for x in self.parameters['admin_ids']]
        print(admins, "lol", uid)
        if uid not in admins:
            repl = {k : v for k, v in repl.items() if k.find('admin') == -1}
        else:
            repl = {k: v for k, v in repl.items() if k.find('admin') >= 0 or k.find('usual') <= 0}
        for k, v in repl.items():
            flag = False
            for x in v[0]:
                if txt.find(x) >= 0 and x != '':
                    flag = True

                    sendmsg = v[1][randint(0, len(v[1])-1)]


                    try:
                        uname = api.users.get(user_ids = int(uid))[0]['first_name']
                        print(uname)
                        api.messages.send(peer_id=int(addr_id), message=uname + " " + sendmsg)
                        self.answered_messages['now'].append(message['id'])
                    except:

                        return -1
                    else:
                        return 0
                    break
            if flag:
                return 0
        try:
            uname = api.users.get(user_ids=int(uid))[0]['first_name']
            print(repl)
            sendmsg = repl['idontknow'][1][randint(0, len(repl['idontknow'][1])-1)]
            print(sendmsg)

            api.messages.send(peer_id=int(addr_id), message=uname + " " + sendmsg)
            self.answered_messages['now'].append(message['id'])
        except:
            return -1
        else:

            return 0

    def answer(self, count):
        """
        gets new incoming messages and call answer_message or command
        :param count:
        :return:
        """
        api = self.API
        names = self.parameters['pseudonames']
        messages = api.messages.get(count=count, time_offset=ANSWER_TIME, preview_length=SYMBOLS_COUNT)['items']
        messages = [x for x in messages if not(x['id'] in self.answered_messages['before'])]
        try:
            print(api.utils.getServerTime())
        except:
            return -1
        for x in messages:
            print(x['user_id'])
        commands = [x for x in messages if str(x['user_id']) in self.parameters['admin_ids'] and \
                    (x['body'].split(" ")[0].lower().find(COMMAND_SYMBOL+names[1]) >= 0 or \
                     x['body'].split(" ")[0].lower().find(COMMAND_SYMBOL + names[0]) >= 0)]
        messages = [x for x in messages if not(str(x['user_id']) in self.parameters['blacklist']) and (x['body'].split(" ")[0].lower() in names or not('chat_id' in x))]
        print(commands)
        if commands:
            for x in commands:
                sleep(wait_between_req)
                self.command(x)
        if messages:
            for x in messages:
                sleep(wait_between_req)
                self.answer_message(x)

    def get_config(self):
        """
        this function parses <botname>.config file and reloads class variables from it
        :return: 0
        """
        lines = 0
        try:
            config = open(self.config, 'r')
        except OSError as e:
            if e.errno in {errno.EBUSY,errno.EBADF}:  # Failed as the file already exists.
                pass
            else:  # Something unexpected went wrong so reraise the exception.
                raise
        else:  # No exception, so the file must have been created successfully.
            lines = config.readlines()
            config.close()
            lines = [x[:-1] for x in lines if not(x[0] == CONFIG_COMMENT and x[:3] != CONFIG_FMTS)]

            fmt_lines = [x for x in range(0, len(lines)) if lines[x][:3] == CONFIG_FMTS ]

            fmt_lines.sort()
            for x in fmt_lines:
                if lines[x] == "###END OF CONFIG###":
                    break
                elif x == fmt_lines[CONFIG_BLOCK_INDEX]:
                    for i in range(x+1, fmt_lines[CONFIG_BLOCK_INDEX+1]):

                        vl = {}
                        key = lines[i].split(" ")[0][:-1]
                        if key != 'conversations':
                            vl = lines[i].split(" ")[1:]

                        else:
                            value = lines[i].split(' ')[1:]
                            for x in value:
                                x = x.split('_')
                                key_conv = x[0]
                                value_conv = x[1:]
                                vl[key_conv] = value_conv
                        self.parameters[key] = vl
                    continue
                elif x == fmt_lines[REPLYCS_BLOCK_INDEX]:
                    for i in range(x + 1, fmt_lines[REPLYCS_BLOCK_INDEX + 1]-1):
                        key = lines[i].split(" ")[0][:-1]
                        line = lines[i].split(CONFIG_ARG_STR_DELIM)

                        value_0 = lines[i].split(CONFIG_ARG_STR_DELIM)[1][:-2].split(CONFIG_ARG_DELIM)

                        value_1 = lines[i].split(CONFIG_ARG_STR_DELIM)[2][:-1].split(CONFIG_ARG_DELIM)
                        value_1 = [x for x in value_1 if x !=')']
                        self.replycs[key] = [value_0, value_1]
                    continue
                else:
                    for i in range(x + 1, fmt_lines[fmt_lines.index(x) + 1] - 1):
                        key = lines[i].split(" ")[0][:-1]
                        line = lines[i].split(CONFIG_ARG_STR_DELIM)
                        value = line[1][:-1].split(CONFIG_ARG_DELIM)
                        self.other[key] = value

    def init_files(self):
        return 0


if __name__ == '__main__':
    while True:
        try:
            session = vk.AuthSession(5816048, num, 'pass', scope='wall, messages, groups')
            vk_api = vk.API(session, v = '5.62')
            a = Bot(vk_api, 'plot')
        except vk.exceptions.VkAuthError as e:
            print("AuthError: " + str(e.errno))
        finally:
            print("Bot is restarting... or not?")
