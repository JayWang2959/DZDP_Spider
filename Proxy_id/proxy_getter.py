import re
import time
from threading import Thread
from multiprocessing import Pool
from Utils import get_html, get_html_tree, check_ip


class ProxyGetter:
    """
    get free proxies
    """
    def __init__(self):
        self.ip_list = []

    def get_proxy_xici(self):
        """
        西刺代理
        """
        url = 'https://www.xicidaili.com/nn'
        html = get_html_tree(url)
        proxy_list = html.xpath('.//table[@id="ip_list"]//tr[position()>1]')
        for proxy in proxy_list:
            ip = {
                'address': proxy.xpath('./td/text()')[0],
                'port': proxy.xpath('./td/text()')[1]
            }
            # checked_ip = check_ip(ip[0], ip[1])
            # if checked_ip is not None:
            self.ip_list.append(ip)
            # yield ip

    def get_proxy_kuaidl(self):
        """
        快代理
        """
        url = 'https://www.kuaidaili.com/free/inha/'
        html = get_html_tree(url)
        proxy_list = html.xpath('.//table//tr')
        for tr in proxy_list[1:]:
            ip = {
                'address': tr.xpath('./td/text()')[0],
                'port': tr.xpath('./td/text()')[1]
            }
            self.ip_list.append(ip)

    def get_proxy_yundl(self):
        """
        云代理
        """
        url = 'http://www.ip3366.net/free/?stype=1'
        html = get_html(url)
        proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', html)
        for proxy in proxies:
            ip = {
                'address': proxy[0],
                'port': proxy[1]
            }
            self.ip_list.append(ip)

    def get_proxy_xiladl(self):
        """
        西拉代理
        """
        url = "http://www.xiladaili.com/gaoni/"
        html = get_html(url)
        ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", html)
        for ip in ips:
            ip = ip.split(':')
            self.ip_list.append({
                'address': ip[0],
                'port': ip[1]
            })

    def print_proxy(self):
        print(len(self.ip_list))
        for ip in self.ip_list:
            print(ip)

    def start_proxy_getter(self):
        """
        通过多线程从多个网站爬取免费代理
        """
        print('----抓取代理ip----')
        thread1 = Thread(target=self.get_proxy_xici)
        thread2 = Thread(target=self.get_proxy_kuaidl)
        thread3 = Thread(target=self.get_proxy_xiladl)
        thread4 = Thread(target=self.get_proxy_yundl)

        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()

        thread4.join()
        thread3.join()
        thread2.join()
        thread1.join()

    def check_available_ip(self, ip):
        """
        清洗ip
        """
        flag = check_ip(ip)
        if flag:
            return ip

        # # 注意这里应倒序遍历
        # for i in range(len(self.ip_list) - 1, -1, -1):
        #     flag = check_ip(self.ip_list[i])
        #     if not flag:
        #         self.ip_list.remove(self.ip_list[i])

    def start_check_ip(self):
        """
        使用进程池 提高清洗ip效率
        :return ips 可用的ip列表
        """
        ips = []
        print('----清洗ip----')
        start_time = time.time()
        pool = Pool(processes=16)
        ips.append(pool.map(self.check_available_ip, self.ip_list))
        end_time = time.time()
        print('----清洗ip耗时：', end_time-start_time)
        pool.close()
        pool.join()
        ips = [ip for ip in ips[0] if ip is not None]
        return ips


if __name__ == '__main__':
    import json
    proxy = ProxyGetter()
    proxy.start_proxy_getter()
    proxy.print_proxy()
    ips = proxy.start_check_ip()
    print(len(ips))
    print(ips)
    with open('../ip.txt', 'w') as fp:
        json.dump(ips, fp)

