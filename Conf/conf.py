"""
默认配置
"""
__all__ = [
    'default_conf',
    'user_agents',
    'referers',
    'woff_string'
]

default_conf = {
    'database': {
        'host': '',
        'user': '',
        'password': '',
        'dbname': ''
    }
}

# ua池
user_agents = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 OPR/26.0.1656.60',
    'Opera/8.0 (Windows NT 5.1; U; en)',
    'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 9.50',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
    'Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2 ',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0) ',
]

# referer 池
referers = [
    'http://www.dianping.com/shanghai/ch10/g102',
    'http://www.dianping.com/shanghai/ch10/g102r811',
    'http://www.dianping.com/shanghai/ch10/g113',
    'http://www.dianping.com/shanghai/ch10/g101',
    'http://www.dianping.com/shanghai/ch10/r854',
    'http://www.dianping.com/shanghai/ch10/r836',
    'http://www.dianping.com/shanghai/ch10/g114',
    'http://www.dianping.com/shanghai/ch10/g508',
    'http://www.dianping.com/shanghai/ch10/g34236',
    'http://www.dianping.com/shanghai/ch10/g115',
    'http://www.dianping.com/shanghai/ch10/g2714',
    'http://www.dianping.com/shanghai/ch10/r840',
    'http://www.dianping.com/shanghai/ch10/r3',
    'http://www.dianping.com/shanghai/ch10/r4',
    'http://www.dianping.com/shanghai/ch10/r5938',
    'http://www.dianping.com/shanghai/ch10/r8847',
    'http://www.dianping.com/shanghai/ch10/r90243',

]

# 大众点评的字符集
woff_string = '''
1234567890店中美家馆
小车大市公酒行国品发电金心业商司
超生装园场食有新限天面工服海华水
房饰城乐汽香部利子老艺花专东肉菜
学福饭人百餐茶务通味所山区门药银
农龙停尚安广鑫一容动南具源兴鲜记
时机烤文康信果阳理锅宝达地儿衣特
产西批坊州牛佳化五米修爱北养卖建
材三会鸡室红站德王光名丽油院堂烧
江社合星货型村自科快便日民营和活
童明器烟育宾精屋经居庄石顺林尔县
手厅销用好客火雅盛体旅之鞋辣作粉
包楼校鱼平彩上吧保永万物教吃设医
正造丰健点汤网庆技斯洗料配汇木缘
加麻联卫川泰色世方寓风幼羊烫来高
厂兰阿贝皮全女拉成云维贸道术运都
口博河瑞宏京际路祥青镇厨培力惠连
马鸿钢训影甲助窗布富牌头四多妆吉
苑沙恒隆春干饼氏里二管诚制售嘉长
轩杂副清计黄讯太鸭号街交与叉附近
层旁对巷栋环省桥湖段乡厦府铺内侧
元购前幢滨处向座下臬凤港开关景泉
塘放昌线湾政步宁解白田町溪十八古
双胜本单同九迎第台玉锦底后七斜期
武岭松角纪朝峰六振珠局岗洲横边济
井办汉代临弄团外塔杨铁浦字年岛陵
原梅进荣友虹央桂沿事津凯莲丁秀柳
集紫旗张谷的是不了很还个也这我就
在以可到错没去过感次要比觉看得说
常真们但最喜哈么别位能较境非为欢
然他挺着价那意种想出员两推做排实
分间甜度起满给热完格荐喝等其再几
只现朋候样直而买于般豆量选奶打每
评少算又因情找些份置适什蛋师气你
姐棒试总定啊足级整带虾如态且尝主
话强当更板知己无酸让入啦式笑赞片
酱差像提队走嫩才刚午接重串回晚微
周值费性桌拍跟块调糕'''