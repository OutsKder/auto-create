import requests

def get_external_ip():
    """
    获取外网IP地址
    :return: 外网IP地址字符串
    """
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        ip_info = response.json()
        return ip_info['ip']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching external IP: {e}")
        return None