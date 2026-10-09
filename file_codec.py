import base64
import hashlib
import random
from pathlib import Path

# 网络协议常量（客户端与服务端共用）
KEY_PREFIX = "wskkey"

# 编码协议布局常量
INT_LEN = 4
STR_LEN = 20
SHA256_LEN = 32
CHUNK_SIZE = 10200
FIRST_HEADER_LEN = 3 * INT_LEN + STR_LEN + SHA256_LEN  # 64
OTHER_HEADER_LEN = 2 * INT_LEN  # 8
FILE_ID_MIN = 10000000
FILE_ID_MAX = 99999999

# 客户端目录常量
CLIENT_FILES_DIR = Path("client_files")
CLIENT_TMP_DIR = Path("client_tmp")


def encrypt(binary_data):
    result = []
    for i in range(len(binary_data)):
        x = binary_data[i]
        result.append(255 - x if (x <= 127 and x % 2 == 1) or (x > 127 and x % 2 == 0) else x)
    return bytes(result)


def split_data(binary_data):
    if len(binary_data) <= CHUNK_SIZE - FIRST_HEADER_LEN:
        return [binary_data]
    result = [binary_data[:CHUNK_SIZE - FIRST_HEADER_LEN]]
    for i in range(CHUNK_SIZE - FIRST_HEADER_LEN, len(binary_data), CHUNK_SIZE - OTHER_HEADER_LEN):
        result.append(binary_data[i: i + CHUNK_SIZE - OTHER_HEADER_LEN])
    return result


def combine_data(split_binary_data, total):
    result = b''
    for i in range(total):
        if i in split_binary_data:
            result = result + split_binary_data[i]
        else:
            return i, b''
    return total, result


def encoding_data(binary_data, file_id, path, sha256):
    split_binary_data = split_data(binary_data)
    file_id_byte = file_id.to_bytes(INT_LEN, byteorder='big')
    total_index_byte = len(split_binary_data).to_bytes(INT_LEN, byteorder='big')
    path_byte = path.encode('utf-8')
    path_byte = path_byte[:STR_LEN] if len(path_byte) >= STR_LEN else path_byte + b'\x00' * (STR_LEN - len(path_byte))
    result = []
    for index, data in enumerate(split_binary_data):
        index_byte = index.to_bytes(INT_LEN, byteorder='big')
        if index == 0:
            result.append(file_id_byte + index_byte + total_index_byte + path_byte + sha256 + data)
        else:
            result.append(file_id_byte + index_byte + data)
    return result


def decoding_first_line(base64_data):
    data = base64.b64decode(base64_data)
    file_id = int.from_bytes(data[0: INT_LEN], byteorder='big')
    return file_id


def decoding_data(encoding_binary_data):
    result = {}
    file_id = 0
    total_index = 0
    path = ""
    sha256 = b''

    for da in encoding_binary_data:
        file_id = int.from_bytes(da[0: INT_LEN], byteorder='big')
        index = int.from_bytes(da[INT_LEN:2 * INT_LEN], byteorder='big')
        if index == 0:
            total_index = int.from_bytes(da[2 * INT_LEN:3 * INT_LEN], byteorder='big')
            path = da[3 * INT_LEN:3 * INT_LEN + STR_LEN].rstrip(b'\x00').decode('utf-8')
            sha256 = da[3 * INT_LEN + STR_LEN:FIRST_HEADER_LEN]
            result[index] = da[FIRST_HEADER_LEN:]
        else:
            result[index] = da[OTHER_HEADER_LEN:]
    lack_index, binary_data = combine_data(result, total_index)
    if lack_index != total_index:
        print(f"lack {lack_index}")
    return binary_data, file_id, path, sha256, lack_index


def encoding(input_file_path, file_name):
    with open(Path(input_file_path) / file_name, 'rb') as file:
        binary_data = file.read()

    file_id = random.randint(FILE_ID_MIN, FILE_ID_MAX)
    while (CLIENT_TMP_DIR / f"{file_id}.txt").exists():
        file_id = random.randint(FILE_ID_MIN, FILE_ID_MAX)
    sha256 = hashlib.sha256(binary_data).digest()  # sha256在加密前
    binary_data = encrypt(binary_data)  # 加密
    encoding_binary_data = encoding_data(binary_data, file_id, file_name, sha256)  # 添加前缀

    # 将二进制数据编码为Base64
    base64_data = [base64.b64encode(da).decode() for da in encoding_binary_data]
    tmp_file_path = CLIENT_TMP_DIR / f"{file_id}.txt"
    with open(tmp_file_path, 'w') as f:
        f.write('\n'.join(base64_data))
    print(f"Done! Write to file {tmp_file_path}")
    return tmp_file_path


def decoding(file_name, output_dir):
    with open(file_name, 'r') as file:
        base64_data = file.readlines()
    encoding_binary_data = [base64.b64decode(da.replace('\n', '')) for da in base64_data]
    binary_data, file_id, path, sha256, lack_index = decoding_data(encoding_binary_data)
    sha256_status = False
    write_status = False
    if binary_data == b'':
        return lack_index, sha256_status, write_status
    binary_data = encrypt(binary_data)  # 解密
    if sha256 == hashlib.sha256(binary_data).digest():
        print("Sha256 checking pass!")
        sha256_status = True
    else:
        print("Sha256 checking error!")
    with open(Path(output_dir) / path, 'wb') as file:
        file.write(binary_data)
        print(f"Write to {path}")
        write_status = True
    return lack_index, sha256_status, write_status
