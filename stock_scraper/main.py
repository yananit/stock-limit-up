import requests
import time
import pandas as pd
from config import URL, HEADERS
# from utils import save_to_csv, clean_data
from fake_useragent import UserAgent
from utils import clean_data, save_to_excel
from utils import send_email_with_attachment


def get_limit_up_data():
    """获取涨停板数据"""
    # 生成随机User-Agent
    ua = UserAgent()
    headers = HEADERS.copy()
    headers["User-Agent"] = ua.random

    # 构造请求参数
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "500",  # 获取500条数据
        "sort": "fbt:asc",
        "date": time.strftime("%Y%m%d"),  # 当前日期
        "_": int(time.time() * 1000)  # 时间戳
    }

    try:
        response = requests.get(URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        json_data = response.json()

        if json_data['data'] is None:
            print("今日无涨停数据")
            return None

        return json_data['data']['pool']

    except Exception as e:
        print(f"请求失败: {e}")
        return None


def process_data(raw_data):
    """处理原始数据，返回字段为中文名的DataFrame"""

    # 中文字段映射
    field_map = {
        'c': '股票代码',
        'n': '股票名称',
        'p': '当前价格',
        'zdp': '涨跌幅',
        'lbc': '涨停天数',
        'fbt': '首次涨停时间',
        'hs': '换手率',
        'fund': '封单金额',
        'ltsz': '流通市值',
        'hybk': '所属行业'
    }

    processed_data = []
    for stock in raw_data:
        item = {cn_name: stock.get(en_key, '') for en_key, cn_name in field_map.items()}

        # ✅ 当前价格除以100，保留两位小数
        if isinstance(item['当前价格'], (int, float)):
            item['当前价格'] = round(item['当前价格'] / 1000, 2)

        # ✅ 涨跌幅取整并加 %
        if isinstance(item['涨跌幅'], (int, float)):
            item['涨跌幅'] = f"{int(round(item['涨跌幅']))}%"

        # 连板数据
        zttj = stock.get('zttj', {})
        if isinstance(zttj, dict):
            item['连板统计天数'] = zttj.get('days', '')
            item['连板概念数'] = zttj.get('ct', '')
        else:
            item['连板统计天数'] = ''
            item['连板概念数'] = ''

        # 占位字段
        item['概念题材'] = ''

        processed_data.append(item)

    return pd.DataFrame(processed_data)




if __name__ == "__main__":
    print("开始获取涨停板数据...")
    raw_data = get_limit_up_data()

    if raw_data:
        print(f"共获取到 {len(raw_data)} 条数据")
        df = process_data(raw_data)
        df = clean_data(df)

        # for stock in raw_data:
        #     print(stock)  # 打印单个原始数据字典

        # 显示前5行数据
        print("\n数据样例:")
        print(df.head())

        # 保存数据
        save_to_excel(df, time.strftime("%Y%m%d"))
    else:
        print("未获取到有效数据")

# 假设你已生成文件路径
file_path = f"D:/Thszt/limit_up_{time.strftime('%Y%m%d')}.xlsx"

# 调用发送函数
send_email_with_attachment(
    receiver_email="2627768814@qq.com",
    subject="今日涨停股数据",
    body="请查收今日的涨停股 Excel 数据。",
    attachment_path=file_path,
    sender_email="2627768814@qq.com",
    smtp_server="smtp.qq.com",  # QQ邮箱示例
    smtp_port=465,
    app_password="thuyewceuwazecai"  # SMTP授权码
)