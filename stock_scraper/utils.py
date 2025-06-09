import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import requests
from config import SAVE_PATH
import smtplib
from email.message import EmailMessage

import pandas as pd
import os

def save_to_excel(data: pd.DataFrame, filename: str):
    """保存为Excel文件并居中对齐，添加单位，并按行业上色"""

    # 确保文件夹存在
    save_dir = 'D:/Thszt'
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, f"limit_up_{filename}.xlsx")

    # 添加单位：封单金额、流通市值（亿元）
    data['封单金额'] = data['封单金额'].apply(lambda x: f"{x / 1e8:.2f} 亿" if isinstance(x, (int, float)) else x)
    data['流通市值'] = data['流通市值'].apply(lambda x: f"{x / 1e8:.2f} 亿" if isinstance(x, (int, float)) else x)

    # 分配行业颜色
    data = assign_colors_by_industry(data)

    # 保存并设置样式
    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        data.drop(columns=['行业颜色']).to_excel(writer, index=False, sheet_name='涨停股数据')
        workbook = writer.book
        worksheet = writer.sheets['涨停股数据']

        # 设置格式：居中对齐
        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        col_num = len(data.columns) - 1  # 去掉“行业颜色”列
        worksheet.set_column(0, col_num - 1, 15, center_format)

        # 找到“所属行业”列索引
        industry_col = data.columns.get_loc("所属行业")

        # 设置行业颜色填充
        for row_num, color in enumerate(data["行业颜色"], start=1):  # 从第2行开始（0是表头）
            if pd.notna(color):
                fill_format = workbook.add_format({
                    'bg_color': color,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                worksheet.write(row_num, industry_col, data.iloc[row_num - 1, industry_col], fill_format)

    print(f"数据已保存至: {filepath}")




def clean_data(df):
    """清洗涨停股数据，字段为中文"""

    import pandas as pd

    # 1. 删除包含“ST”的股票
    if '股票名称' in df.columns:
        df = df[~df['股票名称'].astype(str).str.contains('ST', na=False)]

    # 2. 替换异常空值
    df.replace(['--', '', None], pd.NA, inplace=True)

    # 3. 数值处理
    # 3.1 封单金额：保留两位小数（单位：万元）
    if '封单金额' in df.columns:
        df['封单金额'] = pd.to_numeric(df['封单金额'], errors='coerce') / 1e4
        df['封单金额'] = df['封单金额'].map(lambda x: f"{x:.2f}" if pd.notna(x) else '')

    # 3.2 流通市值：保留两位小数（单位：亿元）
    if '流通市值' in df.columns:
        df['流通市值'] = pd.to_numeric(df['流通市值'], errors='coerce') / 1e8
        df['流通市值'] = df['流通市值'].map(lambda x: f"{x:.2f}" if pd.notna(x) else '')

    # 3.3 换手率：保留两位小数 + 添加百分号
    if '换手率' in df.columns:
        df['换手率'] = pd.to_numeric(df['换手率'], errors='coerce')
        df['换手率'] = df['换手率'].map(lambda x: f"{x:.2f}%" if pd.notna(x) else '')

    # 4. 首次涨停时间格式化为 HH:MM
    if '首次涨停时间' in df.columns:
        def fmt_time(x):
            if pd.isna(x): return ''
            x_str = str(int(float(x))).rjust(6, '0')  # 补足6位
            return f"{x_str[:2]}:{x_str[2:4]}"
        df['首次涨停时间'] = df['首次涨停时间'].apply(fmt_time)





    # 5. 填充空值
    df.fillna('', inplace=True)

    return df
def get_stock_concepts(stock_code):
    """获取个股所属概念板块（来自东方财富）"""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_THEME_CONCEPT",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{stock_code}")',
        "source": "WEB",
        "client": "WEB",
        "_": int(time.time() * 1000)
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        json_data = response.json()

        # 添加健壮性判断
        if (
            json_data.get('result') is None or
            json_data['result'].get('data') is None
        ):
            return ''  # 无概念信息

        data = json_data['result']['data']
        concepts = [item['CONCEPT_NAME'] for item in data if 'CONCEPT_NAME' in item]
        return ', '.join(concepts)

    except Exception as e:
        print(f"获取 {stock_code} 概念失败: {e}")
        return ''



def assign_colors_by_industry(df):
    """
    给“所属行业”分配唯一颜色，并添加“行业颜色”列。
    """
    unique_industries = df['所属行业'].dropna().unique()
    color_map = plt.cm.get_cmap('tab20', len(unique_industries))

    # 映射行业到颜色（RGB转Hex）
    industry_color_dict = {
        industry: '#{:02x}{:02x}{:02x}'.format(
            int(255 * r), int(255 * g), int(255 * b)
        )
        for industry, (r, g, b, _) in zip(unique_industries, color_map.colors)
    }

    # 添加颜色列
    df['行业颜色'] = df['所属行业'].map(industry_color_dict)
    return df

def send_email_with_attachment(receiver_email, subject, body, attachment_path,
                                sender_email, smtp_server, smtp_port, app_password):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg.set_content(body)

        # 添加附件
        with open(attachment_path, 'rb') as f:
            file_data = f.read()
            filename = os.path.basename(attachment_path)
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=filename)

        # 连接 SMTP 服务器并发送邮件
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)

        print(f"邮件已发送至 {receiver_email}")
    except Exception as e:
        print(f"发送邮件失败: {e}")

