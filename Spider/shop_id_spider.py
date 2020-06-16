"""
大众点评的 爬虫
"""
import random
import time

import requests
import re
import json
from threading import Thread, Lock
from lxml import etree
from Utils import get_ua, get_ref, get_proxies

# lock = Lock()


class ShopIdSpider:
    def __init__(self,
                 available_ip_list,
                 shop_id_queue):
        self.__available_ip_list = available_ip_list
        self.__shop_id_queue = shop_id_queue

        # 餐饮品类 用于构建url
        self.food_label_list = []
        # 地区
        self.location = {}
        # 商户id
        self.shop_list = []

        self.__init_threads()

    def __init_threads(self):
        """
        初始化各工作线程
        :return:
        """
        self.__get_food_thread = Thread(target=self.get_food_labels)
        # self.__get_location_thread = Thread(target=self.get_location_labels)
        self.__monitor_thread = Thread(target=self.monitor)

    def start_threads(self):
        # start threads
        self.__get_food_thread.start()
        # self.__get_location_thread.start()

        # todo 优化此处逻辑
        self.__init__shopip_threads()
        for i in range(len(self.__shopid_threads)):
            self.__shopid_threads[i].start()

        self.__monitor_thread.start()

        self.__monitor_thread.join()
        # wait threads to stop
        for i in range(len(self.__shopid_threads)):
            self.__shopid_threads[i].join()

        # self.__get_location_thread.join()
        self.__get_food_thread.join()

    def get_html(self, url):
        """
        爬取页面 若代理ip失效，则从池中移除
        :param url:
        :return: html 文本
        """
        if not self.__available_ip_list:
            print('waiting for proxies')
        while True:
            if self.__available_ip_list:
                ip = random.choice(self.__available_ip_list)
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
                # todo 这里删除ip仍有可能因为多个进程同时访问出错，应使用互斥锁
                if ip in self.__available_ip_list:
                    # lock.acquire()
                    self.__available_ip_list.remove(ip)
                    # lock.release()
                if not self.__available_ip_list:
                    print('waiting for proxies')
                while True:
                    if self.__available_ip_list:
                        ip = random.choice(self.__available_ip_list)
                        break
                    time.sleep(.1)
                proxies = get_proxies(ip)
            else:
                html = request.text
                return html

    def get_food_labels(self):
        """
        爬取食物品类的id
        :return:
        """
        url = 'http://www.dianping.com/shanghai/ch10'
        html = self.get_html(url)

        selector = etree.HTML(html)
        labels = selector.xpath('//*[@id="classfy"]/a')
        labels_text = selector.xpath('//*[@id="classfy"]/a/span/text()')

        # 如果遇到验证码，重新获取页面，绕过去
        while not labels_text:
            html = self.get_html(url)
            selector = etree.HTML(html)
            labels = selector.xpath('//*[@id="classfy"]/a')
            labels_text = selector.xpath('//*[@id="classfy"]/a/span/text()')

        for i in range(len(labels)):
            # print('g' + labels[i].get("data-cat-id"), end='  ')
            # print(labels_text[i])
            self.food_label_list.append({
                'label_id': 'g' + labels[i].get("data-cat-id"),
                'label_name': labels_text[i]
            })
        print('食物品类爬取完毕')
        with open('labels.json', 'w') as f:
            json.dump(self.food_label_list, f)

    def get_location_labels(self):
        """
        爬取热门商圈，行政区划的id
        :return:
        """
        url = 'http://www.dianping.com/shanghai/ch10'
        html = self.get_html(url)
        selector = etree.HTML(html)

        # 如果遇到验证码，重新获取页面，绕过去
        check = selector.xpath('//*[@id="bussi-nav"]/a/span/text()')
        while not check:
            html = self.get_html(url)
            selector = etree.HTML(html)

        # 热门商圈
        bussiness_area = selector.xpath('//*[@id="bussi-nav"]/a')
        bussiness_name = selector.xpath('//*[@id="bussi-nav"]/a/span/text()')
        bussiness_list = []
        for i in range(len(bussiness_area)):
            bussiness_list.append({
                'bussi_id': 'r' + bussiness_area[i].get("data-cat-id"),
                'bussi_name': bussiness_name[i]
            })

        # 行政区
        region_area = selector.xpath('//*[@id="region-nav"]/a')
        region_name = selector.xpath('//*[@id="region-nav"]/a/span/text()')
        region_list = []
        for i in range(len(region_area)):
            region_list.append({
                'region_id': 'r' + region_area[i].get("data-cat-id"),
                'region_name': region_name[i]
            })

        # 地铁
        metro_area = selector.xpath('//*[@id="metro-nav"]/a')
        metro_name = selector.xpath('//*[@id="metro-nav"]/a/span/text()')
        metro_list = []
        for i in range(len(metro_area)):
            metro_list.append({
                'metro_id': 'r' + metro_area[i].get("data-cat-id"),
                'metro_name': metro_name[i]
            })

        self.location = {
            'bussiness': bussiness_list,
            'region': region_list,
            'metro': metro_list
        }
        print('商户地区爬取完毕')
        with open('location.json', 'w') as fp:
            json.dump(self.location, fp)

    def get_shopid(self, url):
        """
        爬取单页排行中的十五家商户 id 用于构建商户页面url
        :param url:
        :return:
        """
        html = self.get_html(url)
        shop_ids = re.findall('shopIDs: \[ (.*?)\]', html, re.S)

        # 如果遇到验证码，重新获取页面，绕过去
        while not shop_ids:
            html = self.get_html(url)
            shop_ids = re.findall('shopIDs: \[ (.*?)}}\)', html, re.S)

        shop_id_list = shop_ids[0].split(',')
        shop_id_list.pop()
        for shop_id in shop_id_list:
            shop_id = shop_id.replace('"', '')
            self.shop_list.append({
                'shop_id': shop_id
            })
        print('get shop id:', len(self.shop_list))
        with open('shops.json', 'w') as f:
            json.dump(self.shop_list, f)

    def __init__shopip_threads(self):
        base_url = 'http://www.dianping.com/shanghai/ch10/'
        while True:
            if self.food_label_list:
                urls = [base_url + label['label_id'] for label in self.food_label_list]
                break
            time.sleep(.1)

        self.__shopid_threads = []
        for i in range(len(urls)):
            thread = Thread(target=self.get_shopid, args=(urls[i],))
            self.__shopid_threads.append(thread)

    def monitor(self):
        """
        监控各线程，进行调度
        :return:
        """
        # 检查商店ip是否爬取完毕
        # todo 这种方式不够安全
        thread_num = len(self.__shopid_threads)
        count = None
        while count != 0:
            count = thread_num
            for i in self.__shopid_threads:
                if not i.is_alive():
                    count -= 1
            print('shopid thread count', count)
            time.sleep(1)
        print('----商铺id爬取完毕----')
        self.__shop_id_queue.put(self.shop_list)
