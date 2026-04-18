from network_info_module import get_external_ip
from output_module import print_ip

if __name__ == '__main__':
    external_ip = get_external_ip()
    print_ip(external_ip)