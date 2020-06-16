"""
调度器，定时更新维护代理ip池
"""
import time
from multiprocessing import Lock, Process
from apscheduler.schedulers.background import BackgroundScheduler


class ProxyScheduler(Process):

    def __init__(self,
                 proxy,
                 proxies_queue,
                 stop_queue):
        Process.__init__(self)

        self.__proxy = proxy
        self.__proxies_queue = proxies_queue
        self.__stop_queue = stop_queue
        self.__lock = Lock()
        self.__scheduler = None

    def update_proxies(self):
        self.__proxy.start_proxy_getter()
        proxies = self.__proxy.start_check_ip()
        print(len(proxies))
        if not self.__proxies_queue.full():
            self.__proxies_queue.put(proxies)

    def run(self) -> None:
        print('coming!!')
        self.update_proxies()
        self.__scheduler = BackgroundScheduler()
        self.__scheduler.add_job(func=self.update_proxies,
                                 trigger='interval',
                                 seconds=70,
                                 id='proxy_scheduler')
        self.__scheduler.start()
        while True:
            if not self.__stop_queue.empty():
                msg = self.__stop_queue.get()
                # print("I've to stop     ", msg)
                if msg['type'] == 99 and msg['cmd'] == 99:
                    self.__scheduler.shutdown()
                    break
            time.sleep(.1)

