import json
import re
import copy
from threading import Thread
from lxml import etree
from queue import Queue
from Utils import GetHtml

shop_list = []
region_queue = Queue(maxsize=1000)
get_html = GetHtml()
sub_url_list = []

sub_url_queue = Queue()
unfinished_url_queue = Queue()


def load_regionIds():
    with open('region.json', 'r') as f:
        region_list = json.load(f)

    for region in region_list:
        for sub_region in region['sub_region_id']:
            region_queue.put(sub_region)


def load_subUrlQueue():
    with open('unfinished_urls.json', 'r') as f:
        sub_urls = json.load(f)

    for url in sub_urls:
        sub_url_queue.put(url)
    # print(sub_url_queue.qsize())


def save_progress():
    unfinished_url_queue.queue = copy.deepcopy(sub_url_queue.queue)
    unfinished_list = []
    while not unfinished_url_queue.empty():
        unfinished_list.append(unfinished_url_queue.get())
    with open('unfinished_urls.json', 'w') as f:
        json.dump(unfinished_list, f)


def get_url_thread():
    while True:
        if region_queue.empty():
            break
        sub_region_id = region_queue.get()
        baseurl = 'http://www.dianping.com/shanghai/ch10'
        url = baseurl + '/' + sub_region_id
        # 检查页面，若失败则重新获取
        while True:
            html = get_html.get_html_zhimaip(url)
            selector = etree.HTML(html)
            if selector is None:
                continue
            sub_region = selector.xpath('//*[@id="region-nav-sub"]/a')
            if not sub_region:
                continue
            break

        page = selector.xpath('//a[@class="PageLink"]/text()')
        # print(i, page)
        max_page = find_max_page(page)
        for j in range(1, max_page+1):
            sub_region_url = url + 'p' + str(j)
            print(sub_region_url)
            sub_url_list.append(sub_region_url)

        with open('sub_urls.json', 'w') as f:
            json.dump(sub_url_list, f)


def find_max_page(pages):
    """
    找到当前分类总共有多少页
    :param pages: class为"PageLink"的元素列表
    :return: 最大页码
    """
    max_page = 1
    for i in pages:
        if int(i) > max_page:
            max_page = int(i)
    return max_page


def get_shopid():
    """
    爬取单页排行中的十五家商户 id 用于构建商户页面url
    :return:
    """

    while True:
        if sub_url_queue.empty():
            break
        url = sub_url_queue.get()
        print(url)
        # 检查页面，若失败重新获取
        while True:
            html = get_html.get_html_zhimaip(url)
            selector = etree.HTML(html)
            if selector is None:
                continue
            sub_region = selector.xpath('//*[@id="region-nav-sub"]/a')
            if not sub_region:
                continue
            break

        shop_ids = re.findall('shopIDs: \[ (.*?)\]', html, re.S)
        shop_id_list = shop_ids[0].split(',')
        shop_id_list.pop()

        for shop_id in shop_id_list:
            shop_id = shop_id.replace('"', '')
            shop_list.append({
                'shop_id': shop_id
            })
        print('get shop id:', len(shop_list))

        with open('shops.json', 'w') as f:
            json.dump(shop_list, f)
        save_progress()


def _main():
    # load_regionIds()
    load_subUrlQueue()
    thread_list = []
    for i in range(24):
        # 爬取url
        # thread_list.append(Thread(target=get_url_thread()))
        # 根据url爬取shop id
        thread_list.append(Thread(target=get_shopid()))

    for i in range(24):
        thread_list[i].start()

    for i in range(24):
        thread_list[i].join()


if __name__ == '__main__':
    _main()

