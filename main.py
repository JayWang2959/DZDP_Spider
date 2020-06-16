from multiprocessing import Manager
import time
import json
from Proxy_id import ProxyGetter, UpdateIpProcess
from Scheduler import ProxyScheduler
from Spider import ShopIdSpider, ShopInfoSpider


def _main():
    with Manager() as process_manager:
        # init share variables
        proxies_queue = process_manager.Queue(maxsize=1000)
        shop_id_queue = process_manager.Queue(maxsize=1000)
        scheduler_stop_queue = process_manager.Queue(maxsize=1000)
        update_ip_stop_queue = process_manager.Queue(maxsize=1000)

        # 可用的代理ip列表,需要不断维护
        available_ip_list = process_manager.list()
        # 读取本地的代理ip 以免一开始就得等待新的代理ip
        with open('ip.txt', 'r') as f:
            available_ip_list.extend(json.load(f))

        # init proxy
        proxy = ProxyGetter()

        # init scheduler process
        scheduler = ProxyScheduler(proxy,
                                   proxies_queue,
                                   scheduler_stop_queue)
        scheduler.start()

        # init update ip process
        ip_updater = UpdateIpProcess(available_ip_list,
                                     proxies_queue,
                                     update_ip_stop_queue)
        ip_updater.start()

        # init shop id spider process
        id_spider = ShopIdSpider(available_ip_list,
                                 shop_id_queue)
        id_spider.start_threads()

        # init shop info spider process
        info_spider = ShopInfoSpider(available_ip_list,
                                     shop_id_queue,
                                     scheduler_stop_queue,
                                     update_ip_stop_queue)
        info_spider.start_spider()

        # wait for stoping
        ip_updater.join()
        scheduler.join()


if __name__ == '__main__':
    _main()
