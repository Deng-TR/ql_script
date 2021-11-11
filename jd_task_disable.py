# coding: utf-8
# __author__ = JimDeng
# __time__   = '2021/11/11 13:12'
'''
cron: 20 10 * * *
new Env('禁用重复任务');
'''

# 环境变量
# REPO_SORT_LIST="black1,black2,black3,......"
# 当有同名重复任务时，优先保留black1的任务，然后是black2、black3，优先级按填写顺序依次降低，逗号分隔


import os
import time
import json
import requests
from collections import Counter


if 'REPO_SORT_LIST' in os.environ:
    repo_sort_list = os.getenv('REPO_SORT_LIST').split(',')
else:
    repo_sort_list = []


def send_notify(title='禁用重复任务', content=''):
    """
    通过 企业微信机器人 推送消息。
    """
    if not os.environ.get('QYWX_KEY'):
        print("未配置企业微信机器人的 QYWX_KEY \n取消推送")
        return

    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s" % os.environ.get('QYWX_KEY')
    data = {"msgtype": "text", "text": {"content": "%s\n\n%s" % (title, content)}}

    try:
        response = requests.post(
            url=url, data=json.dumps(data), headers={"Content-Type": "application/json"}, timeout=5
        )
        data = response.json()
        if data.get("errcode") == 0:
            print("推送成功！")
        else:
            print("推送失败, error：%s" % response.text)
    except Exception as e:
        print(f"脚本异常：%s" % e)


headers={
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
}


def get_task_list():
    url = "http://localhost:5700/api/crons?searchValue=&t=%d" % round(time.time() * 1000)
    response = requests.get(url=url, headers=headers)
    content = json.loads(response.content.decode('utf-8'))
    if content['code'] == 200:
        task_list = content['data']
        return task_list
    else:
        return []


def get_repeat_task(task_list):
    """
    获取重复的任务
    """
    rep_dict = {}
    disable_list = []
    task_name_list = [i['name'] for i in task_list]
    # 名字重复的任务列表
    repeat_task_list = [k for k, v in Counter(task_name_list).items() if v > 1]
    for task in task_list:
        if task['name'] in repeat_task_list:
            for j in repo_sort_list:
                if task['command'].find(j) > 0:
                    if task['name'] not in rep_dict.keys():
                        rep_dict[task['name']] = [repo_sort_list.index(j), task['_id']]
                    elif rep_dict[task['name']][0] < repo_sort_list.index(j):
                        disable_list.append(task['_id'])
                        print(task['name'])
                    else:
                        print(task['name'])
                        disable_list.append(rep_dict[task['name']][1])
                        rep_dict[task['name']] = [repo_sort_list.index(j), task['_id']]
    return disable_list


def disable_tasks(disable_list):
    url = "http://localhost:5700/api/crons/disable?t=%d" % round(time.time() * 1000)
    data=json.dumps(disable_list)
    headers["Content-Type"]="application/json;charset=UTF-8"
    response = requests.put(url=url, headers=headers, data=data)
    msg = json.loads(response.content.decode('utf-8'))
    if msg['code'] != 200:
        print("出错！，错误信息为：%s"%msg)
    else:
        print("成功禁用重复任务")


def load_token():
    try:
        with open("/ql/config/auth.json","r",encoding="utf-8") as f:
            token = json.load(f)['token']
    except Exception as e:
        send_notify(content="获取token异常：%s" % e)
        token = ''
    return token


if __name__ == '__main__':
    token = load_token()
    headers["Authorization"] = "Bearer %s" % token
    task_list = get_task_list()
    if len(task_list) == 0:
        print("未获取到任务列表!")
    disable_list = get_repeat_task(task_list)
    before = "禁用前数量为：%d" % len(task_list)
    print(before)
    after = "禁用重复任务后，数量为:%d" % (len(task_list)-len(disable_list))
    print(after)
    if len(disable_list)==0:
        print("没有重复任务")
    else:
        disable_tasks(disable_list)
        send_notify("禁用成功", "\n%s\n%s" % (before,after))
