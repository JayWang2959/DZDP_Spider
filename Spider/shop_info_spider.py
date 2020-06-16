import re
import time
import requests
import random
from lxml import etree
from multiprocessing import Pool, Lock

from db import SqlDB
from Utils import get_ua, get_ref, get_proxies, get_font

# lock = Lock()


class ShopInfoSpider:
    def __init__(self,
                 available_ip_list,
                 shop_id_queue,
                 scheduler_stop_queue,
                 update_ip_stop_queue):

        self.__available_ip_list = available_ip_list
        self.__shop_id_queue = shop_id_queue
        self.__scheduler_stop_queue = scheduler_stop_queue
        self.__update_ip_stop_queue = update_ip_stop_queue

        # 获取解密字典映射
        self.num_dict, self.word_dict = get_font()

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

    def get_shop_info(self, url):
        """
        获取商户信息
        :return:
        """
        html = self.get_html(url)
        # 破解字体加密
        for key in self.num_dict:
            if key in html:
                html = html.replace(key, str(self.num_dict[key]))
        for key in self.word_dict:
            if key in html:
                html = html.replace(key, str(self.word_dict[key]))

        selector = etree.HTML(html)
        # 如果遇到验证码，重新获取页面，绕过去
        check_name = selector.xpath('//h1[@class="shop-name"]/text()')
        while not check_name:
            html = self.get_html(url)
            selector = etree.HTML(html)

        print('-------------------------')
        # shop id
        shop_id = re.findall('http://www\.dianping\.com/shop/(.*)', url)[0]
        print('shop id:', shop_id)

        # 店名
        shop_name = selector.xpath('//h1[@class="shop-name"]/text()')[0]
        shop_name = shop_name.replace(' ', '')
        print('shop name:', shop_name)

        # 食物品类
        food_type = selector.xpath('//div[@class="breadcrumb"]/a/text()')
        if food_type:
            food_type = food_type[1].replace(' ', '')
        print('food type:', food_type)
        # 行政区
        region = selector.xpath('//div[@class="breadcrumb"]/a/text()')
        if region:
            region = region[2].replace(' ', '')
        print('region:', region)
        # 地址
        address = re.findall('address: "(.*?)",', html, re.S)[0]
        print('address:', address)

        # 都用正则去拼
        # 评论数
        review_count_str = re.findall('<span id="reviewCount"(.*?)</d> 条评论 </span>', html, re.S)
        if review_count_str:
            review_nums = re.findall('\d+', review_count_str[0], re.S)
            review_count = ''.join(review_nums)
        else:
            review_count = ''
        print('review count:', review_count)

        # 人均价格
        avg_price_str = re.findall('<span id="avgPriceTitle" class="item">(.*?)</span>', html, re.S)
        if avg_price_str:
            price_nums = re.findall('\d+', avg_price_str[0], re.S)
            avg_price = ''.join(price_nums)
        else:
            avg_price = ''
        print('avg price:', avg_price)

        # 口味
        taste_str = re.findall('口味:(.*?)</span>', html, re.S)
        if taste_str:
            taste_num = re.findall('\d+', taste_str[0], re.S)
            taste_points = '.'.join(taste_num)
        else:
            taste_points = ''
        print('taste points:', taste_points)

        # 环境
        env_str = re.findall('环境:(.*?)</span>', html, re.S)
        if env_str:
            env_num = re.findall('\d+', env_str[0], re.S)
            env_points = '.'.join(env_num)
        else:
            env_points = ''
        print('environment points', env_points)

        # 服务
        service_str = re.findall('服务:(.*?)</span>', html, re.S)
        if service_str:
            service_num = re.findall('\d+', service_str[0], re.S)
            service_points = '.'.join(service_num)
        else:
            service_points = ''
        print('service points', service_points)

        shop_info = {
            'shop_id': shop_id,
            'shop_name': shop_name,
            'food_type': food_type,
            'region': region,
            'address': address,
            'review_count': review_count,
            'avg_price': avg_price,
            'taste_points': taste_points,
            'env_points': env_points,
            'service_points': service_points
        }
        print(shop_info)

        # todo 优化 进程之间相互独立 无法共享同一个数据库连接，故只能每次建立新的连接，造成比较大的开销
        # 连接数据库
        db = SqlDB()
        # 插入数据库
        db.add_shop(shop_info)
        # 关闭数据库连接
        db.close_connection()

    def start_spider(self):
        """
        使用进程池并行爬取商户信息
        :return
        """
        base_url = 'http://www.dianping.com/shop/'
        while True:
            print('is shop id empty?', self.__shop_id_queue.empty())
            if not self.__shop_id_queue.empty():
                shop_ids = self.__shop_id_queue.get()
                break
            time.sleep(1)
        urls = [base_url + shop['shop_id'] for shop in shop_ids]

        # print(urls)
        print('----爬取商户----')
        start_time = time.time()
        pool = Pool(processes=8)
        pool.map(self.get_shop_info, urls)
        end_time = time.time()
        print('----爬取商户耗时：', end_time - start_time)
        pool.close()
        pool.join()
        print('----爬取完毕----')
        stop_msg = {
            'type': 99,
            'cmd': 99
        }

        # 停止其他进程
        self.__scheduler_stop_queue.put(stop_msg)
        self.__update_ip_stop_queue.put(stop_msg)


if __name__ == '__main__':
    import json

    with open('../ip.txt', 'r') as f:
        ip_list = json.load(f)

    info_spider = ShopInfoSpider(ip_list)

    info_spider.start_spider()

# urls = ['http://www.dianping.com/shop/H9D3EhwmzEvErmdw', 'http://www.dianping.com/shop/H9CDhWhRY88pNNTp', 'http://www.dianping.com/shop/H4bCGJ3u7cqEFg1z', 'http://www.dianping.com/shop/H9pQr3xgTq2Wke1F', 'http://www.dianping.com/shop/G2lNazIWFa2PXxI0', 'http://www.dianping.com/shop/k7cQTkoBocFLgtqp', 'http://www.dianping.com/shop/k6M808TAhkoQIqyR', 'http://www.dianping.com/shop/l6hRkWXlyoCk25pf', 'http://www.dianping.com/shop/EPUtTsUfAUCxSmc5', 'http://www.dianping.com/shop/H5957jSkSZIklxg2', 'http://www.dianping.com/shop/G2LQYgctM49uMwzc', 'http://www.dianping.com/shop/Ea6r7eSCe9h779JH', 'http://www.dianping.com/shop/k7pR2oozM9YCnKmI', 'http://www.dianping.com/shop/k7EfP3AYujLc86zt', 'http://www.dianping.com/shop/k87oaNpfOEThb5hW', 'http://www.dianping.com/shop/kakRNLFU76lg1Ork', 'http://www.dianping.com/shop/l7NW3SXVMFimfglh', 'http://www.dianping.com/shop/GajThZqZVdKSXuOx', 'http://www.dianping.com/shop/l6IKh0gse9Ah65ZQ', 'http://www.dianping.com/shop/l8vKiMHf25j9Viks', 'http://www.dianping.com/shop/H4UrFMNSAMqWKdv9', 'http://www.dianping.com/shop/l4pVr71YBebxaOpt', 'http://www.dianping.com/shop/l5qQPxrA3yoD2faY', 'http://www.dianping.com/shop/k1L9MWTKi31lugxs', 'http://www.dianping.com/shop/k3jwx2Z3KiyDyNo1', 'http://www.dianping.com/shop/l3HPvnbtLrFcOO8x', 'http://www.dianping.com/shop/jriZe4G6ij53TsdO', 'http://www.dianping.com/shop/kawZyxqX2hPsKZqE', 'http://www.dianping.com/shop/k813kloUv15No2ZR', 'http://www.dianping.com/shop/l5Q9l0FwQOMD4GJJ', 'http://www.dianping.com/shop/k3lL9sLZwDIPcOK0', 'http://www.dianping.com/shop/jSdSCRZB7UmSjCn6', 'http://www.dianping.com/shop/G9c1DH7LgvMH7MPb', 'http://www.dianping.com/shop/k3vGdJhC2sZnI4AC', 'http://www.dianping.com/shop/G9pH8qLUyeVPUN39', 'http://www.dianping.com/shop/k9mr4aX2GaaH8V7U', 'http://www.dianping.com/shop/l6B8bJOCuPeRY75f', 'http://www.dianping.com/shop/G40NaSmR2aqM5cf8', 'http://www.dianping.com/shop/k1y8bh3zMDNSLN0h', 'http://www.dianping.com/shop/H6lnJuJPGe0glGgu', 'http://www.dianping.com/shop/ixXOcEUOsAMZFN2O', 'http://www.dianping.com/shop/H5qc7Y3SszDlWk8g', 'http://www.dianping.com/shop/k8oAhEd9JYFICzIC', 'http://www.dianping.com/shop/l5Zcp3TIvvuLdEbz', 'http://www.dianping.com/shop/H1HTgY71p9PAeRCZ', 'http://www.dianping.com/shop/k2RHKxIFaoQXW01y', 'http://www.dianping.com/shop/l2rRpqtvhUhErTLW', 'http://www.dianping.com/shop/k5BbWz6ojdq0eHsr', 'http://www.dianping.com/shop/l85fcFrh7XzuuCLb', 'http://www.dianping.com/shop/H3F3gTj42qjXPaxQ', 'http://www.dianping.com/shop/G6ezN7lz9SoqnzGU', 'http://www.dianping.com/shop/G89yhQWOoPOMVD8x', 'http://www.dianping.com/shop/k847iL0VU3GAWVRf', 'http://www.dianping.com/shop/HaJ6hUu19Bo0RynV', 'http://www.dianping.com/shop/H4B6SfePZ3EAekLE', 'http://www.dianping.com/shop/l27XEdbQTmYZyWpS', 'http://www.dianping.com/shop/k9wAalYvJf7JLqTm', 'http://www.dianping.com/shop/k98DLcit8VxUMMeQ', 'http://www.dianping.com/shop/k2iZrfQyn6RwOMSU', 'http://www.dianping.com/shop/H1M1ZVpo7UY2EaOb', 'http://www.dianping.com/shop/G9parnTPI1bpOZ2W', 'http://www.dianping.com/shop/G9LToMNDUtk2M7Re', 'http://www.dianping.com/shop/G93KizEq0AprY1JW', 'http://www.dianping.com/shop/k5E0E7ekSXJs9d71', 'http://www.dianping.com/shop/G9RmCgJ9KlKcvkyI', 'http://www.dianping.com/shop/k8o2ZffKMsiueUSb', 'http://www.dianping.com/shop/H7s38tgIvEEHGCpF', 'http://www.dianping.com/shop/l2tmt1ON2HzH3zw1', 'http://www.dianping.com/shop/H6qvl596palNPZ7n', 'http://www.dianping.com/shop/G1WPQ98Tv60HySgB', 'http://www.dianping.com/shop/kalrFYItRBHZpO67', 'http://www.dianping.com/shop/H4CrP0bswIGP59v9', 'http://www.dianping.com/shop/Gaftx1DGdODh0cM1', 'http://www.dianping.com/shop/l51NHaIQshbQmKs1', 'http://www.dianping.com/shop/k14qdgi3S61JmuKg', 'http://www.dianping.com/shop/FgvjOOZzdezxmJym', 'http://www.dianping.com/shop/k170E0l3ibxr57ae', 'http://www.dianping.com/shop/G2aWy6J3nxhAic7E', 'http://www.dianping.com/shop/k118UNZ7GH7hAt5g', 'http://www.dianping.com/shop/k5Jvq9rWMTAe9lI3', 'http://www.dianping.com/shop/k8jYGwpjX4VDyUUT', 'http://www.dianping.com/shop/l4hFHHWmfNgLXejD', 'http://www.dianping.com/shop/H6b27riWvurVd4Ws', 'http://www.dianping.com/shop/l5xSU9T3TUOs3jbu', 'http://www.dianping.com/shop/k4W6I8xPgwtE2BW1', 'http://www.dianping.com/shop/H41cD2WnM0ECKDuY', 'http://www.dianping.com/shop/l4eMbH3P15RJl4jO', 'http://www.dianping.com/shop/H9Ue7UZxdC5FGsbV', 'http://www.dianping.com/shop/G75oVZrMv6ahvNjO', 'http://www.dianping.com/shop/l1CMhnWwDxUplehN', 'http://www.dianping.com/shop/G3X7A8FdKLvzl4Gc', 'http://www.dianping.com/shop/k2dLNM2tQuiv7Vzh', 'http://www.dianping.com/shop/l3eg7imxUJX8d2hz', 'http://www.dianping.com/shop/l2qhBRdECt6ZRFzD', 'http://www.dianping.com/shop/H6yPknMgOQQDSZCJ', 'http://www.dianping.com/shop/k2xBCm86gcA3EBwC', 'http://www.dianping.com/shop/l1yXBrwHP2CaGWws', 'http://www.dianping.com/shop/H9dXJ0fSpPPELw87', 'http://www.dianping.com/shop/EOkpS1Uxk91xKxep', 'http://www.dianping.com/shop/G1ojAq19PN2pp4Qb', 'http://www.dianping.com/shop/F7UMDsu0zY9TMwmB', 'http://www.dianping.com/shop/k353MXWhUl5YV12F', 'http://www.dianping.com/shop/G8lhC7Lkssyv69EK', 'http://www.dianping.com/shop/k6w6DsglU8bV1Ia0', 'http://www.dianping.com/shop/G2IxP0JxYpXjBnAx', 'http://www.dianping.com/shop/l1RrUsweyvuUY3yr', 'http://www.dianping.com/shop/G6lUt8p6xQvkx4jf', 'http://www.dianping.com/shop/FAIlPkCa1AvcEgoQ', 'http://www.dianping.com/shop/l5CSxLTNWJcKgWRT', 'http://www.dianping.com/shop/G6ukwtXTr8588UAV', 'http://www.dianping.com/shop/G2efD6PKRjQsmZvE', 'http://www.dianping.com/shop/l9ue8Uds0Jt9xTPE', 'http://www.dianping.com/shop/G9WbKA54dTTSFtAw', 'http://www.dianping.com/shop/G4iT0fsJsgFvGZjB', 'http://www.dianping.com/shop/G2a9qzZ9uQQAsWBJ', 'http://www.dianping.com/shop/H50CSf69APq5I5T8', 'http://www.dianping.com/shop/G7sxEFFPpYWIrUH8', 'http://www.dianping.com/shop/jHSDZRx8JU0zzbQ5', 'http://www.dianping.com/shop/G7lZQSVUguP43EIT', 'http://www.dianping.com/shop/G8vQ1zgGBMlcfSli', 'http://www.dianping.com/shop/G8UBEqEidxPxJkb5', 'http://www.dianping.com/shop/G1rrksnDtXGdAV0c', 'http://www.dianping.com/shop/H7ZthLhWhyYebT0E', 'http://www.dianping.com/shop/l28iDss7Yklj9IJY', 'http://www.dianping.com/shop/l6aMRQauVhPrG4fN', 'http://www.dianping.com/shop/G4TTs5CIGiv97ojy', 'http://www.dianping.com/shop/l25o3uvltOPbFbQR', 'http://www.dianping.com/shop/l3so8I7dWtv1MAKA', 'http://www.dianping.com/shop/G6lUt8p6xQvkx4jf', 'http://www.dianping.com/shop/H4D1n9lfP484ZB85', 'http://www.dianping.com/shop/G9WbKA54dTTSFtAw', 'http://www.dianping.com/shop/l8TgvI8tAo12JuAy', 'http://www.dianping.com/shop/k7ejxzpnwxKZedds', 'http://www.dianping.com/shop/l9ue8Uds0Jt9xTPE', 'http://www.dianping.com/shop/laODYKzHb1gDS5yV', 'http://www.dianping.com/shop/l5GNYYVrgLzGYSmK', 'http://www.dianping.com/shop/FI8kwJdJXDpCvjsS', 'http://www.dianping.com/shop/k2luG190OJFzec0G', 'http://www.dianping.com/shop/la3ofIxNwHsGMBQr', 'http://www.dianping.com/shop/l6eAr7hXCHtap0Fi', 'http://www.dianping.com/shop/l4Ix6a3FFvS7qo0S', 'http://www.dianping.com/shop/k36ZbnSyZePGDLM7', 'http://www.dianping.com/shop/G8XbKaurtE5g1I2F', 'http://www.dianping.com/shop/k13aHF1xLApAIe4G', 'http://www.dianping.com/shop/k1JbBd6YYJLY23lr', 'http://www.dianping.com/shop/jI3R6ytWfNHHHyqC', 'http://www.dianping.com/shop/k1M1Z7IImvInZJVG', 'http://www.dianping.com/shop/l2qyDUnqUr9hHZjb', 'http://www.dianping.com/shop/H8jvLCTlulaLwHg8', 'http://www.dianping.com/shop/H9jlkELCfIXDjcTs', 'http://www.dianping.com/shop/k7XpvlywS5aIBZtI', 'http://www.dianping.com/shop/k18XUq4AYeYzOfSd', 'http://www.dianping.com/shop/G2m7gND3yiRkQri1', 'http://www.dianping.com/shop/Hagk5U0zApdRoEp6', 'http://www.dianping.com/shop/G297cKBXIfciwtoz', 'http://www.dianping.com/shop/k5LbC1TTWL2JP8Ez', 'http://www.dianping.com/shop/H5zguiMmDMjcad2m', 'http://www.dianping.com/shop/l5GNYYVrgLzGYSmK', 'http://www.dianping.com/shop/k2amBc1LVrFC3XOT', 'http://www.dianping.com/shop/k5u9bHpNtkJFJUIy', 'http://www.dianping.com/shop/k1uWVJjKnarQutO2', 'http://www.dianping.com/shop/G5ewllmMsVdc2qaO', 'http://www.dianping.com/shop/k8ITMGV2IhOmX5IM', 'http://www.dianping.com/shop/H40IpONDofke1Bfx', 'http://www.dianping.com/shop/G9L6fFXft5I95TtV', 'http://www.dianping.com/shop/kam2LPrRfEN2KuUS', 'http://www.dianping.com/shop/k9oYRvTyiMk4HEdQ', 'http://www.dianping.com/shop/k14SsNrSnS5sSSxG', 'http://www.dianping.com/shop/H4laJMZImBCji9vX', 'http://www.dianping.com/shop/H2UJdTQ1WsnADEam', 'http://www.dianping.com/shop/l9h8XAEspl5I3qdV', 'http://www.dianping.com/shop/GaOecS1g5Uu2XKPV', 'http://www.dianping.com/shop/H3myWQCItWuSYx72', 'http://www.dianping.com/shop/G9HRzX3sI5GN8xbg', 'http://www.dianping.com/shop/FFyTp5INQLk5x4eh', 'http://www.dianping.com/shop/G5LGVutdTgThaQip', 'http://www.dianping.com/shop/l1LINuIT6KAZADli', 'http://www.dianping.com/shop/l1tIQGZq0t9HEdQO', 'http://www.dianping.com/shop/iTPFgKCbOhA0sF4b', 'http://www.dianping.com/shop/lazhn53jlO8Hb73Z', 'http://www.dianping.com/shop/l4oKxKfWqLsvs2Qt', 'http://www.dianping.com/shop/G4j8SPJkHtfcvBzU', 'http://www.dianping.com/shop/HaboLN7SjS0i3Pto', 'http://www.dianping.com/shop/H6INroXJgnYHlR7f', 'http://www.dianping.com/shop/G5aE6guzsFNdfJVV', 'http://www.dianping.com/shop/l6n20LNluL159ae6', 'http://www.dianping.com/shop/G1vD6mRJ9jyHaoAj', 'http://www.dianping.com/shop/k1PAAgdownP8rXsS', 'http://www.dianping.com/shop/k6M2DXP0UV0z0KjO', 'http://www.dianping.com/shop/G1CDQZCqWFvtEz8N', 'http://www.dianping.com/shop/k4QWjj6Xcmd91V2j', 'http://www.dianping.com/shop/H1LyGX63J7iIsoL0', 'http://www.dianping.com/shop/H8qlJFnGfKHwCSTW', 'http://www.dianping.com/shop/H9uwgTFrTDT7B6Ti', 'http://www.dianping.com/shop/G3bpuAaLBgWLqt6U', 'http://www.dianping.com/shop/G9vPsqMwT9SnsR17', 'http://www.dianping.com/shop/GapPwnquuTahfL1P', 'http://www.dianping.com/shop/G4BNnfc1t3ilmjbr', 'http://www.dianping.com/shop/k6ocA7IhTsO3Cxlf', 'http://www.dianping.com/shop/k8mzbSseUAKTYkAy', 'http://www.dianping.com/shop/k5NusAHKegqFrjw0', 'http://www.dianping.com/shop/k4SqECSQlYwPXNLR', 'http://www.dianping.com/shop/k9aXcq0RxQlAWeSN', 'http://www.dianping.com/shop/G2ASgLT4WPFoHQzA', 'http://www.dianping.com/shop/k3cr5vEm4P5N6GAT', 'http://www.dianping.com/shop/l1L8B9jvGGyvkJxb', 'http://www.dianping.com/shop/l3VhmlPfnNuaMBQu', 'http://www.dianping.com/shop/kaDZUpPjkFrftmci', 'http://www.dianping.com/shop/k46OI9fZqHdpNHVg', 'http://www.dianping.com/shop/laaiP6fJBMsbHZDI', 'http://www.dianping.com/shop/l2p6Zk0OLjKMt9UG', 'http://www.dianping.com/shop/jdbYu1rHnrntQoZ6', 'http://www.dianping.com/shop/l5svU39fN5JWySN6', 'http://www.dianping.com/shop/k7Y2zVvZHlfNmqVO', 'http://www.dianping.com/shop/G8w72WaFxMHLDIrB', 'http://www.dianping.com/shop/G5ewllmMsVdc2qaO', 'http://www.dianping.com/shop/G9ngnNYW36KnA0je', 'http://www.dianping.com/shop/lauuN8U1z8Cj6SBn', 'http://www.dianping.com/shop/laACdDXn4prdu3nw', 'http://www.dianping.com/shop/k6Uql2nDLHRPHNqv', 'http://www.dianping.com/shop/H8o8oefrPNH7AtaP', 'http://www.dianping.com/shop/H5iGdD8kTDD7klAr', 'http://www.dianping.com/shop/l5pmW6JUWQbFpyw4', 'http://www.dianping.com/shop/G4EuCkcoUadjTNxL', 'http://www.dianping.com/shop/FelFy13Xky4JLBIv', 'http://www.dianping.com/shop/l7rSQZLBVKVbaUFJ', 'http://www.dianping.com/shop/G1NDNz3vZSssXX28', 'http://www.dianping.com/shop/H1stCKkqXd4ZzNkt', 'http://www.dianping.com/shop/G8q06G18IaSdfKJU', 'http://www.dianping.com/shop/l7Gkok5OM5sIWyw8', 'http://www.dianping.com/shop/H1EuwGXXjlsbvSjo', 'http://www.dianping.com/shop/larDty6QLr4xLW7X', 'http://www.dianping.com/shop/k8haXdCy0ohtIwCW', 'http://www.dianping.com/shop/H98SlOaVXmWIgwSd', 'http://www.dianping.com/shop/l4i6LKpcjPJjLxky', 'http://www.dianping.com/shop/H4CFmYW28wsTezVf', 'http://www.dianping.com/shop/F1Vwfw8XyXTA8ivh', 'http://www.dianping.com/shop/k1XFpBVpFlIe6y9d', 'http://www.dianping.com/shop/l5dmwvx3d7DGhkjK', 'http://www.dianping.com/shop/H9XaUTW5aJekS7Q8', 'http://www.dianping.com/shop/H4zmUTD3dnVGTCVX', 'http://www.dianping.com/shop/H8bsxDF5Uz70h4w5', 'http://www.dianping.com/shop/l6JyL6mYFLo1Y9KG', 'http://www.dianping.com/shop/l4FMrFX9EN7xOERY', 'http://www.dianping.com/shop/FKzFNePAeUFneXcu', 'http://www.dianping.com/shop/G8DfpYe0sagiiqts', 'http://www.dianping.com/shop/k3dZ6hOhabu9zWTy', 'http://www.dianping.com/shop/H81iJF8mNm8r3bTv', 'http://www.dianping.com/shop/laxz60lMy2QiZLBS', 'http://www.dianping.com/shop/lam9sDiL5LmjrfDI', 'http://www.dianping.com/shop/G9t5GhruBgSF3SWP', 'http://www.dianping.com/shop/k2f3lXbBYNjuAH4F', 'http://www.dianping.com/shop/G8nP1QlTHIX2qZvw', 'http://www.dianping.com/shop/H7R6pBoyeef2FmHp', 'http://www.dianping.com/shop/l5Y3q10sjBdzEU8O', 'http://www.dianping.com/shop/H1NiIvh2QgX2ffPN', 'http://www.dianping.com/shop/HaUMaCf28elSrdx1', 'http://www.dianping.com/shop/GaGbqS4i8SYpu1Af', 'http://www.dianping.com/shop/k8aT6UA77DC27Eag', 'http://www.dianping.com/shop/G3IUyK345y6UEi70', 'http://www.dianping.com/shop/k4nxnU3eBFWTRoAF', 'http://www.dianping.com/shop/laM9TDsOL4YlQDJG', 'http://www.dianping.com/shop/l27mFEtM7cT7Sgt4', 'http://www.dianping.com/shop/H1MO2M5AeoNeCxWd', 'http://www.dianping.com/shop/H9JDQ3EgqjXIyyuW', 'http://www.dianping.com/shop/l2JFYHSNrQLqQfzL', 'http://www.dianping.com/shop/EUdgcu6OJTGd0Efe', 'http://www.dianping.com/shop/G1BzyuY2cZ7REwEp', 'http://www.dianping.com/shop/l5yVvZ7knnBcDVZZ', 'http://www.dianping.com/shop/H2ijxfnicbxrY0Rg', 'http://www.dianping.com/shop/G6Rgezm5IVVyjSSr', 'http://www.dianping.com/shop/H1ANNxGO0WxaaOg0', 'http://www.dianping.com/shop/GaMEtY4ylfyIFbds', 'http://www.dianping.com/shop/G4BhdcIyMdEyk8iJ', 'http://www.dianping.com/shop/G1AKdfJkY428tg7w', 'http://www.dianping.com/shop/G420IOA0jJUidpeI', 'http://www.dianping.com/shop/l4oKk8KfMj5z3NNT', 'http://www.dianping.com/shop/k86DDmBuXFNNY17L', 'http://www.dianping.com/shop/G1c6FjXFe0KWxMnW', 'http://www.dianping.com/shop/G9C85TZLT6SkMvPv', 'http://www.dianping.com/shop/G41TRhMLL80DPFTN', 'http://www.dianping.com/shop/HahLy6gOUnOtt1zt', 'http://www.dianping.com/shop/FKdCr3L1i0wZ97WV', 'http://www.dianping.com/shop/k9Sreb0bXu6fq1Ue', 'http://www.dianping.com/shop/k5JmcwCPWhYPn7NR', 'http://www.dianping.com/shop/G5fkD33G5aLyFJWb', 'http://www.dianping.com/shop/H9tOyr6LMPXgiEIY', 'http://www.dianping.com/shop/k1OgxslPm76UbudN', 'http://www.dianping.com/shop/EDUjKOMnuMdy6bnn', 'http://www.dianping.com/shop/G7YuH2B7AMTWh8mY', 'http://www.dianping.com/shop/GaDEgavc6Nvwlh1s', 'http://www.dianping.com/shop/G7pAlXlvwjlhAFpO', 'http://www.dianping.com/shop/k9duB7ERUreULETx', 'http://www.dianping.com/shop/H8nVZfBHbjvmWSgh', 'http://www.dianping.com/shop/l8hsQQ27sL2F6h9f', 'http://www.dianping.com/shop/jmWTvX0vqcdmaRsf', 'http://www.dianping.com/shop/G4bR14hlbsKdoIgF', 'http://www.dianping.com/shop/G5EM9fwYZsMdul2Y', 'http://www.dianping.com/shop/k1scObgfk6lOL2jk', 'http://www.dianping.com/shop/H1mk2XXs8RZnX2tc', 'http://www.dianping.com/shop/k3hPzc0GeoGBsKXH', 'http://www.dianping.com/shop/H26MgG1i3zCTlLji', 'http://www.dianping.com/shop/G6QA1zh5Ioja70qh', 'http://www.dianping.com/shop/H1l2K5kGgLeaDa6a', 'http://www.dianping.com/shop/G1FeU9FucJTLYjcq', 'http://www.dianping.com/shop/H384HDw2Tt4aHzsW', 'http://www.dianping.com/shop/k1L5M1stfHc4QstT', 'http://www.dianping.com/shop/l6s29P6uvOjxga3S', 'http://www.dianping.com/shop/k4izwDTOIfiYQDsF', 'http://www.dianping.com/shop/H7WeJCajkgObiK2n', 'http://www.dianping.com/shop/k82XoKbtHhgxiPI2', 'http://www.dianping.com/shop/k7os7hUeVGgKng9Z', 'http://www.dianping.com/shop/l9sBMlRgOuo3MK9J', 'http://www.dianping.com/shop/G5tG02B1RMco2ydO', 'http://www.dianping.com/shop/H5LTi2e7TlRBn6LK', 'http://www.dianping.com/shop/l6FHyURK5GhsY5Xl', 'http://www.dianping.com/shop/G9o6FPCzwqjr2XZ1', 'http://www.dianping.com/shop/H4hyCBIP8evEzYpS', 'http://www.dianping.com/shop/kaGbqABAi0orJ4Yo', 'http://www.dianping.com/shop/H4SLm0WeCpOCclJU', 'http://www.dianping.com/shop/l3xDi47GTr3zoMYf', 'http://www.dianping.com/shop/l91SZ061PDKTLBvY', 'http://www.dianping.com/shop/H57qLW2A4kmROGe4', 'http://www.dianping.com/shop/k9oYRvTyiMk4HEdQ', 'http://www.dianping.com/shop/kaIwgIsqdroljhR8', 'http://www.dianping.com/shop/l1NnJatcMWV1B1By', 'http://www.dianping.com/shop/H6y5V8txie08xrL9', 'http://www.dianping.com/shop/H6Az9PK3TFq0GZCk', 'http://www.dianping.com/shop/H6bpti9lSVd1DmUp', 'http://www.dianping.com/shop/Ha63g03GDs0xk3lz', 'http://www.dianping.com/shop/H2NIYOnTh4avxnfu', 'http://www.dianping.com/shop/EDUjKOMnuMdy6bnn', 'http://www.dianping.com/shop/H6cZPrge2xMqcgQO', 'http://www.dianping.com/shop/EkJwGYM2A6OMQc93', 'http://www.dianping.com/shop/G99tC8i5QLhdDbl0', 'http://www.dianping.com/shop/G2UHFLgvz7oY6jEC', 'http://www.dianping.com/shop/irlgPcgTCl8SSzCR', 'http://www.dianping.com/shop/k8uWoVspGvvrqpDc', 'http://www.dianping.com/shop/H8FJyLx1yPUcJKaJ', 'http://www.dianping.com/shop/l8eTph2dvMs5N0fn', 'http://www.dianping.com/shop/iG3GFNPVVXJShqlF', 'http://www.dianping.com/shop/G56YAzkbFQc8gS2J', 'http://www.dianping.com/shop/H1BvtxN9T3aLYhiF', 'http://www.dianping.com/shop/k8ErcXd82LgZSXEQ', 'http://www.dianping.com/shop/H9yiCWvbXGu1G252', 'http://www.dianping.com/shop/H8DQWsAlmce5QYi8', 'http://www.dianping.com/shop/H5YOXHNXBbj2uYBl', 'http://www.dianping.com/shop/H7wrgj0TwfITzQfz', 'http://www.dianping.com/shop/l5wKevJN6fLUINTG', 'http://www.dianping.com/shop/G3Hj3JoRii3nAwkP', 'http://www.dianping.com/shop/l1rlPgnfyFI8IQ9e', 'http://www.dianping.com/shop/l2c1GwFj8iMKKAJV', 'http://www.dianping.com/shop/k9yiU9pJJBxzkixw', 'http://www.dianping.com/shop/G9u2vY8liZJmISVK', 'http://www.dianping.com/shop/H35Uetb6XNG9hc41', 'http://www.dianping.com/shop/G796VMMPScCQ8mS2', 'http://www.dianping.com/shop/l1ihXoH2uKPBOmzu', 'http://www.dianping.com/shop/H8wbIlmARSHGfpVj', 'http://www.dianping.com/shop/G9K3cKbCX8CRzc2Z', 'http://www.dianping.com/shop/H90u0jvX1RDjX8dg', 'http://www.dianping.com/shop/H2KxiWLftiJRt4EM', 'http://www.dianping.com/shop/G36n1MCPKr1Dcrfw', 'http://www.dianping.com/shop/l3LGqQmpKaSEdxym', 'http://www.dianping.com/shop/laXEG8ssWPIyP900', 'http://www.dianping.com/shop/k7iRivn4O4eyD066', 'http://www.dianping.com/shop/H4pjCdqxMI2pbk0E', 'http://www.dianping.com/shop/G99x0gW1xJ219Qha', 'http://www.dianping.com/shop/H84DPYnVVVPMm8q4', 'http://www.dianping.com/shop/k4xiHu5MmJ7I5X9a', 'http://www.dianping.com/shop/k4c4WQYUfnF2XJgd', 'http://www.dianping.com/shop/G9t5GhruBgSF3SWP', 'http://www.dianping.com/shop/H7MFNonWZiPXP6AK', 'http://www.dianping.com/shop/kabhI5aJEVLw8epq', 'http://www.dianping.com/shop/G6X9LLT2z2oKJ66f', 'http://www.dianping.com/shop/Haj6WkFinaPQKu2f', 'http://www.dianping.com/shop/k49tXwxza2y8dHeS', 'http://www.dianping.com/shop/l9IFkepiRtS1MoOX', 'http://www.dianping.com/shop/k749L4HhoZBY368D', 'http://www.dianping.com/shop/latKHmydHP9GPtl9', 'http://www.dianping.com/shop/GakLyjCfViu6eyJz', 'http://www.dianping.com/shop/H1NiIvh2QgX2ffPN', 'http://www.dianping.com/shop/G5EakQQCYQVdWjUT', 'http://www.dianping.com/shop/k8MIJrVZ0xaIGSz9', 'http://www.dianping.com/shop/kanPvBAFjhHLgFAq', 'http://www.dianping.com/shop/H9okaepDxOmQ6kOG', 'http://www.dianping.com/shop/iEc5yyX7oBOfNDJX', 'http://www.dianping.com/shop/GayFhzWVaIiYbQxF', 'http://www.dianping.com/shop/H7nvPN0wkINfNpsc', 'http://www.dianping.com/shop/H5Wc1RYXVbJqvkHh', 'http://www.dianping.com/shop/Hav8UOqYVip3tFm6', 'http://www.dianping.com/shop/i1B7XWksb3Tblaab', 'http://www.dianping.com/shop/k4f7kZqBSx2Jg3hh', 'http://www.dianping.com/shop/l6e9cQkaT4lLmXsZ', 'http://www.dianping.com/shop/G5xJRTOlAuqjP8B0', 'http://www.dianping.com/shop/k1usRMDJXgfV3UHJ', 'http://www.dianping.com/shop/k6OhfMPjpvSO82CT', 'http://www.dianping.com/shop/G7jZrXBQSRhaMECh', 'http://www.dianping.com/shop/labI6WZlhch7PqKW', 'http://www.dianping.com/shop/H7FKtlOUVdMFHKOS', 'http://www.dianping.com/shop/H8NN2N6iN2wCgCjz', 'http://www.dianping.com/shop/l35tKdqLK2r6SbXm', 'http://www.dianping.com/shop/H74IV3SAO4t2W2CR', 'http://www.dianping.com/shop/l7nAULzsvwK9mfo0', 'http://www.dianping.com/shop/k3FSYn9mELWlaOSf', 'http://www.dianping.com/shop/k8m3Dzx3KaaJqaKe', 'http://www.dianping.com/shop/EPkeG1QlYQCAk5eF', 'http://www.dianping.com/shop/k73Drq1dJFc4Bcli', 'http://www.dianping.com/shop/G9krLlqXXSl5Mgk9', 'http://www.dianping.com/shop/k6S2GGLpnnqptAjU', 'http://www.dianping.com/shop/H9Ke3PTHnWT1ntmG', 'http://www.dianping.com/shop/H6fnP84z9lXDv1Ax', 'http://www.dianping.com/shop/k5DKzZwTzBwFtTnc', 'http://www.dianping.com/shop/l79duueNqPMZ77mY', 'http://www.dianping.com/shop/GaPk11PjPgXLHS9K', 'http://www.dianping.com/shop/H1MO2M5AeoNeCxWd', 'http://www.dianping.com/shop/l6EoW5F5RSx3AAMY', 'http://www.dianping.com/shop/G7Aly40sT8jgraGr', 'http://www.dianping.com/shop/l9tR4pTPS7ArLj8i', 'http://www.dianping.com/shop/l3P7MYGEsUyoYVRW', 'http://www.dianping.com/shop/GaMEtY4ylfyIFbds', 'http://www.dianping.com/shop/H5dBLgDNXFIcoPrb', 'http://www.dianping.com/shop/l9i2rn0aT5qTLErq', 'http://www.dianping.com/shop/jNpK3Ag7PwmfFgtK', 'http://www.dianping.com/shop/H2TNvdfoW5fd2WQV', 'http://www.dianping.com/shop/H81M3LdKGKJun9S7', 'http://www.dianping.com/shop/iDKOPYUKQVb4jgIv', 'http://www.dianping.com/shop/G6erSkmAMD4vDKWW', 'http://www.dianping.com/shop/FDJGqyl55IWxbklR', 'http://www.dianping.com/shop/k9Sreb0bXu6fq1Ue', 'http://www.dianping.com/shop/katkO8m0ZgxtRKqa', 'http://www.dianping.com/shop/H66RmosXEBDzjrrM', 'http://www.dianping.com/shop/l1tIQGZq0t9HEdQO', 'http://www.dianping.com/shop/H2j0eJ8tRHZiBigw', 'http://www.dianping.com/shop/iHdwYQNQPZ1CasSf', 'http://www.dianping.com/shop/G8GUAQjT2xTJywUc', 'http://www.dianping.com/shop/H9019Mtm1F1Fa1sM', 'http://www.dianping.com/shop/G3x7R0Y1GubHDEG7', 'http://www.dianping.com/shop/Hag2beCmF8Z63BHf', 'http://www.dianping.com/shop/G4mmqiZrzgkpQZGY', 'http://www.dianping.com/shop/l4LSkZ25uyGUhLiU', 'http://www.dianping.com/shop/k6whGJySoFHmuty4', 'http://www.dianping.com/shop/l9tC25mn0CwgioO9', 'http://www.dianping.com/shop/G7ENYf5dMa2sR2BK', 'http://www.dianping.com/shop/H1qIDbHhi7RwOlI2', 'http://www.dianping.com/shop/H8O27Py77wx5bQef', 'http://www.dianping.com/shop/G9AKfux3TQeTogVZ', 'http://www.dianping.com/shop/H5u6d111TH50sRdu', 'http://www.dianping.com/shop/jZ7j9h0a4UthXkk7', 'http://www.dianping.com/shop/k19mfPBfLH3fYssC', 'http://www.dianping.com/shop/l9Yiac7SHqQ9hLfu', 'http://www.dianping.com/shop/k6gPyzhhn4oi6abr', 'http://www.dianping.com/shop/G5AY50GytVK0Jkdg', 'http://www.dianping.com/shop/H1l3Ju3bcTGbji3K', 'http://www.dianping.com/shop/l1QQFQNzMyOm24m7', 'http://www.dianping.com/shop/l8JAMYodZvzedEbs', 'http://www.dianping.com/shop/k6ZfR858Pwj09W4i', 'http://www.dianping.com/shop/k3qy42l8xIo0i0AQ', 'http://www.dianping.com/shop/G98MaATMxpd3OX1b', 'http://www.dianping.com/shop/G59XIyBpiYAyZoWp', 'http://www.dianping.com/shop/k170E0l3ibxr57ae', 'http://www.dianping.com/shop/G8TywxvKJWNHXPBB', 'http://www.dianping.com/shop/H7FaQkL6IkDUQaVs', 'http://www.dianping.com/shop/H8IQVwjiQZrRw3m0', 'http://www.dianping.com/shop/G21VGHhEFqWooDOy', 'http://www.dianping.com/shop/l5zpZn3oGQY2zKSv', 'http://www.dianping.com/shop/k8zGDnVZyB046roI', 'http://www.dianping.com/shop/k6ocA7IhTsO3Cxlf', 'http://www.dianping.com/shop/l4ufEbMy9gAhABBL', 'http://www.dianping.com/shop/G3H69CZBajD5kfAE', 'http://www.dianping.com/shop/k8mzbSseUAKTYkAy', 'http://www.dianping.com/shop/FixMiPcV1lUSoibs', 'http://www.dianping.com/shop/l1L8B9jvGGyvkJxb', 'http://www.dianping.com/shop/j3uTuM4AvRXSjMcq', 'http://www.dianping.com/shop/YtPSMfqXJZp5Nr8c', 'http://www.dianping.com/shop/G57Ca1poqnrAIeIq', 'http://www.dianping.com/shop/k4aSKS5lj7To75wd', 'http://www.dianping.com/shop/FqQZQKoSWt85FsMM', 'http://www.dianping.com/shop/k7LOkVcfPmNoxPdC', 'http://www.dianping.com/shop/H9zi8r0C5M6Y5ID0', 'http://www.dianping.com/shop/G2FY2twZ6YXt3xTy', 'http://www.dianping.com/shop/G2mVBr8x9THlvcOc', 'http://www.dianping.com/shop/k7vNkct5YKbAiXBF', 'http://www.dianping.com/shop/Eel12KSAP6WLMiJD', 'http://www.dianping.com/shop/H9qBVK3Jlk3GXNMK', 'http://www.dianping.com/shop/k8V02S89mrjhvI5B', 'http://www.dianping.com/shop/l4vC1vYGzzO8nDiv', 'http://www.dianping.com/shop/k3jGXLNuh0Bku9qf', 'http://www.dianping.com/shop/l8wYgnInU2iPhmN0', 'http://www.dianping.com/shop/k9oYRvTyiMk4HEdQ', 'http://www.dianping.com/shop/k75buZODHJaHPyBp', 'http://www.dianping.com/shop/G4Fj4EkMSHguX588', 'http://www.dianping.com/shop/H2GFyVas1gcdESWg', 'http://www.dianping.com/shop/k344ik9mj4R4WmLe', 'http://www.dianping.com/shop/k7os7hUeVGgKng9Z', 'http://www.dianping.com/shop/G9o6FPCzwqjr2XZ1', 'http://www.dianping.com/shop/l477orPQSurb5xKJ', 'http://www.dianping.com/shop/iI4gmOZhc1qjUWoW', 'http://www.dianping.com/shop/HakKUU3zE9LGyGp3', 'http://www.dianping.com/shop/l7f90KZ5VLbyOtCU', 'http://www.dianping.com/shop/H5xAlRtah26yuVl4', 'http://www.dianping.com/shop/H3YpGqFvUsraKRzW', 'http://www.dianping.com/shop/kaGbqABAi0orJ4Yo', 'http://www.dianping.com/shop/l4lA8PL9yjCbMOZ2', 'http://www.dianping.com/shop/H3eGK26grQzXUZmG', 'http://www.dianping.com/shop/G9ItTppe4Qefq3d8', 'http://www.dianping.com/shop/k9cB2wBlquuDQqIF', 'http://www.dianping.com/shop/EDUjKOMnuMdy6bnn', 'http://www.dianping.com/shop/irlgPcgTCl8SSzCR', 'http://www.dianping.com/shop/G26GZLFUbJi2xjfd', 'http://www.dianping.com/shop/k86QquSR5ZW6gjKP', 'http://www.dianping.com/shop/H1stCKkqXd4ZzNkt', 'http://www.dianping.com/shop/k7d4DUqe7MQllVYM', 'http://www.dianping.com/shop/ixXOcEUOsAMZFN2O', 'http://www.dianping.com/shop/l2HRE5OYFB1BUEcG', 'http://www.dianping.com/shop/k1wSgSrN96KjWmEZ', 'http://www.dianping.com/shop/kaUlO8Ezu06rEgWp', 'http://www.dianping.com/shop/H2XGDoGkqLFO55Ll', 'http://www.dianping.com/shop/HaxwbOkV1auFUeTo', 'http://www.dianping.com/shop/G9parnTPI1bpOZ2W', 'http://www.dianping.com/shop/G93KizEq0AprY1JW', 'http://www.dianping.com/shop/lazhn53jlO8Hb73Z', 'http://www.dianping.com/shop/G9LToMNDUtk2M7Re', 'http://www.dianping.com/shop/Gaz9iX5IJoautQlo', 'http://www.dianping.com/shop/H6oPMJg4Mh9ms6FL', 'http://www.dianping.com/shop/k8o2ZffKMsiueUSb', 'http://www.dianping.com/shop/k9yVgeqF5BqHfHY4', 'http://www.dianping.com/shop/k5E0E7ekSXJs9d71', 'http://www.dianping.com/shop/G9RmCgJ9KlKcvkyI', 'http://www.dianping.com/shop/G1WPQ98Tv60HySgB', 'http://www.dianping.com/shop/lajaF85sbYrfwCqX', 'http://www.dianping.com/shop/Gaftx1DGdODh0cM1', 'http://www.dianping.com/shop/H29mExBc9Yt39IPa', 'http://www.dianping.com/shop/l8A1Fe8moJT7yzgh', 'http://www.dianping.com/shop/k9oYRvTyiMk4HEdQ', 'http://www.dianping.com/shop/G9parnTPI1bpOZ2W', 'http://www.dianping.com/shop/l76ydJ0jqbsIKdoO', 'http://www.dianping.com/shop/FKdCr3L1i0wZ97WV', 'http://www.dianping.com/shop/k4izwDTOIfiYQDsF', 'http://www.dianping.com/shop/G93KizEq0AprY1JW', 'http://www.dianping.com/shop/k3aFWpnIhwpJ6iO0', 'http://www.dianping.com/shop/H8O5zKFGunQrn712', 'http://www.dianping.com/shop/G1NwfPzLsu9f8grY', 'http://www.dianping.com/shop/H5qxTMyFyfh5PnY0', 'http://www.dianping.com/shop/FdSHn5jinsuDlTFy', 'http://www.dianping.com/shop/H5xAlRtah26yuVl4', 'http://www.dianping.com/shop/k5MkZ7SYvpJpNJmM', 'http://www.dianping.com/shop/k1L9MWTKi31lugxs', 'http://www.dianping.com/shop/G9vPsqMwT9SnsR17', 'http://www.dianping.com/shop/G6lUt8p6xQvkx4jf', 'http://www.dianping.com/shop/k3aADutnIpCnNjPE', 'http://www.dianping.com/shop/H1W2mC5d63SjmcnF', 'http://www.dianping.com/shop/EPrY0oE7dyf41NMQ', 'http://www.dianping.com/shop/k86QquSR5ZW6gjKP', 'http://www.dianping.com/shop/Had5wt1Z5mV74Lhe', 'http://www.dianping.com/shop/k8qJr1EwHaWl9Aox', 'http://www.dianping.com/shop/FSdNCaoKW1TUBX8Y', 'http://www.dianping.com/shop/H7uSMaLJm9EyiGTW', 'http://www.dianping.com/shop/Eq0yO5cl02AV6UGI', 'http://www.dianping.com/shop/G43WC0iPjm2dF6T5', 'http://www.dianping.com/shop/k4hoKYt8uN5A6zkH', 'http://www.dianping.com/shop/H7JFW1JMBHpXP15Y', 'http://www.dianping.com/shop/l7f90KZ5VLbyOtCU', 'http://www.dianping.com/shop/k1cvPxTilYYaL7cN', 'http://www.dianping.com/shop/H2v8lQEJw7leMEG0', 'http://www.dianping.com/shop/Emnne5KsrYwPeJ4I', 'http://www.dianping.com/shop/lakTlSI9aLKMB5rd', 'http://www.dianping.com/shop/G3FiXaj3dvc7rFiD', 'http://www.dianping.com/shop/l5lVepCrQNcog8m9', 'http://www.dianping.com/shop/H4edEgXBK7BLXqkn', 'http://www.dianping.com/shop/jiMtykJ2lReZwmyP', 'http://www.dianping.com/shop/k5Yoo3BQwAZ5KYNF', 'http://www.dianping.com/shop/k9F2tpyppPHVZ3oR', 'http://www.dianping.com/shop/G1Po7kunSAgOSm7z', 'http://www.dianping.com/shop/l6J4HdEd83pD8LwN', 'http://www.dianping.com/shop/H7I3j24Ap8doT8fX', 'http://www.dianping.com/shop/H2W4fgGNa5Qvx6Aq', 'http://www.dianping.com/shop/iKtmnKswQkdzE1Pe', 'http://www.dianping.com/shop/G31UkUVF1cwkVC9u']
