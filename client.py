import requests
import random
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
    file_path = file_codec.encoding(file_codec.CLIENT_FILES_DIR, "DJI_0006.JPG")
    print(file_path)
    base_url = "http://127.0.0.1/log"
    send_logs(file_path, base_url)

