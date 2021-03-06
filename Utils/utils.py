"""
通用工具
"""
import json
import time
import requests
import random
from lxml import etree
from fontTools.ttLib import TTFont
from Conf import user_agents, referers, woff_string


def get_html(url):
    """
    获取 html
    :param url:
    :return:
    """

    header = {'Connection': 'keep-alive',
              'Cache-Control': 'max-age=0',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8',
              }
    try:
        html = requests.get(url=url, headers=header)
    except:
        request_status = 500
        print('fail  %s', request_status)
    else:
        return html.text


def get_html_tree(url):
    """
    获取html tree
    :param url:
    :return:
    """

    header = {'Connection': 'keep-alive',
              'Cache-Control': 'max-age=0',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8',
              }
    try:
        html = requests.get(url=url, headers=header)
    except:
        print('fail  %s', html.status_code)
    else:
        return etree.HTML(html.content)


def check_ip(ip):
    """
    检测IP地址是否可用
    """
    check_url = 'http://www.dianping.com/shanghai/ch10'
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }

    ip_url = '://' + ip['ip'] + ':' + ip['port']
    proxies = {'http': 'http' + ip_url, 'https': 'https' + ip_url}
    # print(ip_url)
    try:
        html = requests.get(check_url, headers=header, proxies=proxies, timeout=3)
        status_code = html.status_code
    except:
        # print('fail-%s' % ip['address'])
        return False
    else:
        # ip_info = {'address': address, 'port': port}
        if status_code == 200:
            # print('success-%s' % ip['address'])
            return True
        else:
            return False


def get_ua():
    """
    随机获取 user-agent
    :return:
    """
    user_agent = random.choice(user_agents)
    return user_agent


def get_ref():
    """
    随机获取 referer
    :return:
    """
    referer = random.choice(referers)
    return referer


def get_proxies(ip):
    ip_url = '://' + ip['ip'] + ':' + str(ip['port'])
    proxies = {'http': 'http' + ip_url, 'https': 'https' + ip_url}
    return proxies


def get_font():
    """
    解密字体映射关系
    数字使用的是 64c220e4.woff 文件
    汉字使用的是 8e65e977.woff 文件
    :return: 加密字体映射表
    """
    font_num = TTFont('../50819d54.woff')
    font_word = TTFont('../50819d54.woff')
    font_num_keys = font_num.getGlyphOrder()
    font_word_keys = font_word.getGlyphOrder()
    texts = ['', ''] + [i for i in woff_string if i != '\n' and i != ' ']
    font_num_dict = {}
    font_word_dict = {}
    for index, value in enumerate(texts):
        a = font_num_keys[index].replace('uni', '&#x').lower() + ';'
        b = font_word_keys[index].replace('uni', '&#x').lower() + ';'
        font_num_dict[a] = value
        font_word_dict[b] = value

    return font_num_dict, font_word_dict


class GetHtml:
    def __init__(self):
        self.load_ip()

    def load_ip(self):
        # 可用ip列表
        with open('../Utils/available_ip.json', 'r') as f:
            ips = json.load(f)
        self.available_ip_list = ips['data']

    def get_html_zhimaip(self, url):
        if not self.available_ip_list:
            print('waiting')
            self.load_ip()
            print(self.available_ip_list)

        while True:
            if self.available_ip_list:
                ip = random.choice(self.available_ip_list)
                break
            time.sleep(.1)

        proxies = get_proxies(ip)
        ua = get_ua()
        ref = get_ref()

        headers = {
            "User-Agent": ua,
            "Referer": ref,
        }

        while True:
            try:
                request = requests.get(url=url, headers=headers, proxies=proxies, timeout=3)
            except:
                request_status = 500
            else:
                request_status = request.status_code

            if request_status != 200:
                print(request_status)
                if ip in self.available_ip_list:
                    self.available_ip_list.remove(ip)
                if not self.available_ip_list:
                    print('waiting for proxies')
                    self.load_ip()
                    print(self.available_ip_list)

                while True:
                    if self.available_ip_list:
                        ip = random.choice(self.available_ip_list)
                        break
                    time.sleep(.1)
                proxies = get_proxies(ip)
            else:
                html = request.text
                return html


if __name__ == '__main__':
    get_font()