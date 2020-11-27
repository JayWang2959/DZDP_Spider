from Utils import GetHtml
from lxml import etree
import time
import random
import json

baseurl = 'http://www.dianping.com/shanghai/ch10'
get_html = GetHtml()
html = get_html.get_html_zhimaip(baseurl)
print(html)

selector = etree.HTML(html)

# 行政区及商圈
while True:
    try:
        region_area = selector.xpath('//*[@id="region-nav"]/a')
        region_name = selector.xpath('//*[@id="region-nav"]/a/span/text()')
        break
    except:
        print('验证码')
        time.sleep(random.randint(1, 3))
        html = get_html.get_html_zhimaip(baseurl)
        selector = etree.HTML(html)

region_list = []
for i in range(len(region_area)):
    region_list.append({
        'region_id': 'r' + region_area[i].get("data-cat-id"),
        'region_name': region_name[i]
    })
print(region_list)

for item in region_list:
    item['sub_region_id'] = []
    item['sub_region_name'] = []
    url = baseurl + '/' + item['region_id']
    print(url)
    new_html = get_html.get_html_zhimaip(url)
    selector = etree.HTML(new_html)
    while True:
        try:
            sub_region = selector.xpath('//*[@id="region-nav-sub"]/a')
            sub_region_name = selector.xpath('//*[@id="region-nav-sub"]/a/span/text()')
            break
        except:
            print('验证码')
            time.sleep(random.randint(1, 3))
            new_html = get_html.get_html_zhimaip(url)
            selector = etree.HTML(new_html)

    for i in range(1, len(sub_region)):
        item['sub_region_id'].append('r' + sub_region[i].get("data-cat-id"))
        item['sub_region_name'].append(sub_region_name[i])

print(region_list)
# with open('region.json', 'w') as f:
#     json.dump(region_list, f)


