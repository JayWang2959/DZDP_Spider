import time
from multiprocessing import Process


class UpdateIpProcess(Process):
    """
    维护代理ip池 更新新爬取的可用ip
    """
    def __init__(self,
                 available_ip_list,
                 proxies_queue,
                 stop_queue):
        Process.__init__(self)

        self.__available_ip_list = available_ip_list
        self.__proxies_queue = proxies_queue
        self.__stop_queue = stop_queue

    def update_new_proxies(self):
        """
        更新可用的代理ip
        :return:
        """
        while True:
            if not self.__stop_queue.empty():
                msg = self.__stop_queue.get()
                if msg['type'] == 99 and msg['cmd'] == 99:
                    break

            if not self.__proxies_queue.empty():
                proxies = self.__proxies_queue.get()
                self.__available_ip_list.extend(proxies)
                print('available ip count:', len(self.__available_ip_list))

            time.sleep(.1)

    def run(self) -> None:
        self.update_new_proxies()
