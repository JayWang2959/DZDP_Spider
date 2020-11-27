import json
import re
import copy
from threading import Thread
from lxml import etree
from queue import Queue
from Utils import GetHtml, get_font

shop_id_queue = Queue()
unfinished_shop_id_queue = Queue()
get_html = GetHtml()
shop_info_list = []

# 获取解密字典映射
num_dict, word_dict = get_font()


def load_shopIdQueue():
    with open('unfinished_shops_id.json', 'r') as f:
        shop_ids = json.load(f)

    for id in shop_ids:
        shop_id_queue.put(id)
    # shop_id_queue.put({'shop_id': 'H2uGiD2ivbOvPvlX'})
    # print(shop_id_queue.qsize())


def save_progress():
    unfinished_shop_id_queue.queue = copy.deepcopy(shop_id_queue.queue)
    unfinished_list = []
    while not unfinished_shop_id_queue.empty():
        unfinished_list.append(unfinished_shop_id_queue.get())
    # print(len(unfinished_list))
    with open('unfinished_shops_id.json', 'w') as f:
        json.dump(unfinished_list, f)


def get_shop_info():
    baseurl = 'http://www.dianping.com/shop/'
    while True:
        if shop_id_queue.empty():
            break
        url = baseurl + shop_id_queue.get()['shop_id']
        print('-------------------------')
        print(url)
        # 检查页面，若失败重新获取
        while True:
            html = get_html.get_html_zhimaip(url)
            selector = etree.HTML(html)
            if selector is None:
                continue
            shop_name = selector.xpath('//h1[@class="shop-name"]/text()')
            if not shop_name:
                continue
            break

        # 破解字体加密
        for key in num_dict:
            if key in html:
                html = html.replace(key, str(num_dict[key]))
        for key in word_dict:
            if key in html:
                html = html.replace(key, str(word_dict[key]))

        selector = etree.HTML(html)
        # print(html)

        # shop id
        shop_id = re.findall('http://www\.dianping\.com/shop/(.*)', url)[0]
        print('shop id:', shop_id)

        # 店名
        shop_name_str = re.findall('<h1 class="shop-name">(.*?)<a class="qr-contrainer"', html, re.S)[0].replace(' ', '')
        shop_name_str = shop_name_str.replace('\n', '')
        selector1 = etree.HTML(shop_name_str)
        shop_name_words = selector1.xpath('//text()')
        shop_name = ''
        for i in shop_name_words:
            shop_name = shop_name + i
        print('shop name:', shop_name)

        breadcrumb = selector.xpath('//div[@class="breadcrumb"]/a/text()')
        # 食物品类
        food_type = breadcrumb[1].replace(' ', '')
        print('food type:', food_type)
        # 行政区
        region = breadcrumb[2].replace(' ', '')
        print('region:', region)
        # 子地区
        sub_region = breadcrumb[3].replace(' ', '')
        print('sub_region:', sub_region)

        # 地址
        address_str = re.findall('地址：(.*?) </span>', html, re.S)[0].replace(' ', '')
        address_str = address_str.replace('\n', '')
        selector2 = etree.HTML(address_str)
        words = selector2.xpath('//text()')
        address = ''
        for i in words:
            address = address + i
        # address = selector.xpath('//e[@class="address"]/text')
        print('address:', address)

        # 都用正则去拼
        # 评论数
        review_count_str = re.findall('<span id="reviewCount"(.*?)条评价 </span>', html, re.S)
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
            'sub_region': sub_region,
            'address': address,
            'review_count': review_count,
            'avg_price': avg_price,
            'taste_points': taste_points,
            'env_points': env_points,
            'service_points': service_points
        }
        shop_info_list.append(shop_info)
        print('---------------------')

        with open('final_shop_infos.json', 'w') as f:
            json.dump(shop_info_list, f)
        save_progress()
        print('shop count:', len(shop_info_list))


def _main():
    load_shopIdQueue()
    thread_list = []
    for i in range(24):
        thread_list.append(Thread(target=get_shop_info()))

    for i in range(24):
        thread_list[i].start()

    for i in range(24):
        thread_list[i].join()


if __name__ == '__main__':
    _main()
