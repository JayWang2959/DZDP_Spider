import pymysql

from Conf import default_conf


class SqlDB:
    """
    数据库操作类
    """
    def __init__(self):
        self.__conn = pymysql.connect(host=default_conf['database']['host'],
                                      user=default_conf['database']['user'],
                                      password=default_conf['database']['password'],
                                      database=default_conf['database']['dbname'])

        self.__cursor = self.__conn.cursor()

    def add_shop(self, shop):
        """
        插入商户信息
        :param shop:
        :return:
        """

        sql = "INSERT INTO restaurants (shop_id, shop_name, food_type, address, review_count, avg_price, taste_points, env_points, service_points)" \
              "VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" \
              % (shop['shop_id'], shop['shop_name'], shop['food_type'], shop['address'], shop['review_count'],
                 shop['avg_price'], shop['taste_points'], shop['env_points'],
                 shop['service_points'])

        try:
            self.__cursor.execute(sql)
            self.__conn.commit()
            print('插入成功')
        except:
            print('插入商户信息失败')

    def close_connection(self):
        """
        关闭数据库连接
        :return:
        """
        self.__cursor.close()
        self.__conn.close()


if __name__ == '__main__':
    sql = SqlDB()
    shop = {'shop_id': 'jiMtykJ2lReZwmyP', 'shop_name': '万酥脆北京烤鸭(东建路店)', 'food_type': '北京菜', 'region': '浦东新区',
            'address': '东建路350号-31', 'review_count': '33', 'avg_price': '68', 'taste_points': '8.0',
            'env_points': '7.9', 'service_points': '7.9'}

    sql.add_shop(shop)
