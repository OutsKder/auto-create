import requests

def get_external_ip():
    """
    获取本机外网IP地址
    :return: 外网IP地址字符串
    """
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        return parse_ip(response.json())
    except requests.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def parse_ip(data):
    """
    解析从外部服务返回的数据，提取出公网IP地址
    :param data: 字典类型，包含IP地址信息
    :return: IP地址字符串
    """
    return data['ip']

if __name__ == '__main__':
    ip_address = get_external_ip()
    if ip_address:
        print(f"Your public IP address is: {ip_address}")