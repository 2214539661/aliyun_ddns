#!/usr/bin/env python
# coding=utf-8
import sys

import requests
import re
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
import urllib.request
import json
import time
import argparse
import ssl
import configparser
import logging


# 利用API获取IP
def getRealIp():
    # 方案1
    r = requests.get("http://txt.go.sohu.com/ip/soip")
    ip = re.findall('\d+.\d+.\d+.\d+', r.text)
    return ip[0]
    # 方案2
    url = "https://api.ipify.org/?format=json"
    context = ssl._create_unverified_context()
    response = urllib.request.urlopen(url, context=context)
    html = response.read().decode('utf-8')
    jsonData = json.loads(html)
    return jsonData['ip']


# 利用API获取IP
def getRealIpV6():
    url = "https://api-ipv6.ip.sb/ip"
    response = urllib.request.urlopen(url)
    html = response.read().decode('utf-8')
    return html.strip()


def getRecords(client, rr, domain):
    request = DescribeDomainRecordsRequest()

    request.set_accept_format('json')
    request.set_DomainName(domain)
    request.set_RRKeyWord(rr)

    response = client.do_action_with_exception(request)
    # logging.info(str(response, encoding='utf-8'))
    jsonData = json.loads(response)
    return jsonData['DomainRecords']['Record']


def addDomainRecord(client, rr, domain, ip, type):
    request = AddDomainRecordRequest()
    request.set_accept_format('json')
    request.set_Value(ip)
    request.set_Type(type)
    request.set_RR(rr)
    request.set_DomainName(domain)
    response = client.do_action_with_exception(request)
    logging.info(str(response, encoding='utf-8'))
    logging.info(response)
    return json.loads(response)['RecordId']


def updateDomainRecord(client, rr, domain, ip, type):
    records = getRecords(client, rr, domain)
    record_id = None
    for record in records:
        if record['RR'] == rr and record['DomainName'] == domain and record['Type'] == type:
            record_id = record['RecordId']
            avail_ip = record['Value']
            avail_record = record
            break
    if record_id is None:
        logging.info("不存在记录，正在添加记录")
        addDomainRecord(client, rr, domain, ip, type)
    else:
        # logging.info("存在记录：" + str(avail_record))
        if avail_ip == ip:
            logging.info("ip未改变，不更改记录，原ip=" + avail_ip + "，现ip=" + ip)
        else:
            logging.info("ip已改变，准备更改记录，原ip=" + avail_ip + "，现ip=" + ip)
            request = UpdateDomainRecordRequest()
            request.set_action_name("UpdateDomainRecord")
            request.set_RR(rr)
            request.set_RecordId(record_id)
            request.set_Type(type)
            request.set_Value(ip)
            request.set_TTL(600)
            request.set_accept_format('json')
            response = client.do_action_with_exception(request)
            logging.info(str(response, encoding='utf-8'))
            return json.loads(response)['RecordId']


if __name__ == "__main__":
    _ip = ''

    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # 创建文件处理器
    file_handler = logging.FileHandler('log.log')  # 替换为你想要输出日志的文件路径

    # 配置文件处理器的日志格式
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # 将文件处理器添加到根日志记录器
    logging.getLogger().addHandler(file_handler)

    # 创建ConfigParser对象
    config = configparser.ConfigParser()
    # 读取.config文件
    try:
        config.read('aly.config')
        #         type = "A"
        #         key = 'LTAI5tGdSYrAmuQpsgPCfZvq'
        #         secret = 'QXuDLADxNKt4yrzDik3HgPF7iRxI4i'
        #         rr = 'ngnxs'
        #         domain = 'cqsqy.com'
        # 获取配置项的值
        type = "A"
        key = config.get('config', 'key')
        secret = config.get('config', 'secret')
        rr = config.get('config', 'rr')
        domain = config.get('config', 'domain')
    except Exception as e:
        logging.info('config配置不存在:' + str(e))
        sys.exit()

    while True:
        ip = getRealIp()
        logging.info('本机ip：' + ip)
        if _ip == ip:
            logging.info('ip未改变')
        else:
            _ip = ip
            try:
                client = AcsClient(key, secret, 'cn-hangzhou')
                updateDomainRecord(client, rr, domain, ip, type)
            except Exception as e:
                logging.info('配置参数错误无法更新：' + str(e))
                sys.exit()
        time.sleep(30)
