import requests
import random
from pathlib import Path

import file_codec


def send_logs(file_path, base_url):
    with open(file_path, 'r') as file:
        content = file.readlines()
    send_index_list = list(range(len(content)))
    random.shuffle(send_index_list)
    lack_index = len(content)
    for index, send_index in enumerate(send_index_list):
        line = content[send_index].replace('\n', '')
        if not line:
            continue  # 跳过空行
        try:
            response = requests.get(f"{base_url}/{file_codec.KEY_PREFIX}{line}", timeout=5)
            print(f"Index {index}, Line {send_index}: [HTTP {response.status_code}] {response.text}")
            if response.text.startswith("Need"):
                lack_index = int(response.text.split(" ")[1])
        except requests.exceptions.RequestException as e:
            print(f"Index {index}, Line {send_index}: Failed to send - {str(e)}")
    while lack_index != len(content):
        line = content[lack_index].replace('\n', '')
        if not line:
            continue  # 跳过空行
        try:
            response = requests.get(f"{base_url}/{file_codec.KEY_PREFIX}{line}", timeout=5)
            print(f"Index NULL, Line {lack_index}: [HTTP {response.status_code}] {response.text}")
            if response.text.startswith("Need"):
                lack_index = int(response.text.split(" ")[1])
        except requests.exceptions.RequestException as e:
            print(f"Index NULL, Line {lack_index}: Failed to send - {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="文件分片发送客户端")
    parser.add_argument("ip", help="服务端 IP 地址")
    parser.add_argument("file_path", help="待发送文件的路径")
    args = parser.parse_args()

    tmp_dir = Path(args.file_path).parent
    tmp_file = file_codec.encoding(args.file_path, tmp_dir)
    print(tmp_file)
    base_url = f"http://{args.ip}/log"
    send_logs(tmp_file, base_url)

