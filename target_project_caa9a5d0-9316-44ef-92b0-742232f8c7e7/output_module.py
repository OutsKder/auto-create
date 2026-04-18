def print_ip(ip):
    """
    打印IP地址
    :param ip: IP地址字符串
    """
    if ip:
        print(f"Your public IP address is: {ip}")
    else:
        print("Failed to retrieve your public IP address.")