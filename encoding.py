import base64
import hashlib
import os
import random


def encrypt(binary_data):
    result = []
    for i in range(len(binary_data)):
        x = binary_data[i]
        result.append(255 - x if (x <= 127 and x % 2 == 1) or (x > 127 and x % 2 == 0) else x)
    return bytes(result)


def split_data(binary_data):
    chunk_size = 10200
    if len(binary_data) <= chunk_size - 64:
        return [binary_data]
    result = [binary_data[:chunk_size - 64]]
    for i in range(chunk_size - 64, len(binary_data), chunk_size - 8):
        result.append(binary_data[i: i + chunk_size - 8])
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
    int_len = 4
    str_len = 20
    split_binary_data = split_data(binary_data)
    file_id_byte = file_id.to_bytes(int_len, byteorder='big')
    total_index_byte = len(split_binary_data).to_bytes(int_len, byteorder='big')
    path_byte = path.encode('utf-8')
    path_byte = path_byte[:str_len] if len(path_byte) >= str_len else path_byte + b'\x00' * (str_len - len(path_byte))
    result = []
    for index, data in enumerate(split_binary_data):
        index_byte = index.to_bytes(int_len, byteorder='big')
        if index == 0:
            result.append(file_id_byte + index_byte + total_index_byte + path_byte + sha256 + data)
        else:
            result.append(file_id_byte + index_byte + data)
    return result


def decoding_first_line(base64_data):
    data = base64.b64decode(base64_data)
    file_id = int.from_bytes(data[0: 4], byteorder='big')
    return file_id


def decoding_data(encoding_binary_data):
    int_len = 4
    str_len = 20
    result = {}
    file_id = 0
    total_index = 0
    path = ""
    sha256 = b''

    for da in encoding_binary_data:
        file_id = int.from_bytes(da[0: 1 * int_len], byteorder='big')
        index = int.from_bytes(da[1 * int_len: 2 * int_len], byteorder='big')
        if index == 0:
            total_index = int.from_bytes(da[2 * int_len: 3 * int_len], byteorder='big')
            path = da[3 * int_len: 3 * int_len + str_len].rstrip(b'\x00').decode('utf-8')
            sha256 = da[32:64]
            result[index] = da[64:]
        else:
            result[index] = da[8:]
    lack_index, binary_data = combine_data(result, total_index)
    if lack_index != total_index:
        print(f"lack {lack_index}")
    return binary_data, file_id, path, sha256, lack_index


def encoding(input_file_path, file_name):
    with open(os.path.join(input_file_path, file_name), 'rb') as file:
        binary_data = file.read()

    file_id = random.randint(10000000, 99999999)
    while os.path.exists(f"client_tmp/{file_id}.txt"):
        file_id = random.randint(10000000, 99999999)
    sha256 = hashlib.sha256(binary_data).digest()  # sha256在加密前
    binary_data = encrypt(binary_data)  # 加密
    encoding_binary_data = encoding_data(binary_data, file_id, file_name, sha256)  # 添加前缀

    # 将二进制数据编码为Base64
    base64_data = [base64.b64encode(da).decode() for da in encoding_binary_data]
    with open(f"client_tmp/{file_id}.txt", 'w') as f:
        f.write('\n'.join(base64_data))
    print(f"Done! Write to file client_tmp/{file_id}.txt")
    return f"client_tmp/{file_id}.txt"


def decoding(file_name):
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
    with open('server_files/' + path, 'wb') as file:
        file.write(binary_data)
        print(f"Write to {path}")
        write_status = True
    return lack_index, sha256_status, write_status


if __name__ == '__main__':
    path = encoding("client_files", "DJI_0002.JPG")
    print(path)
    lack_index, sha256_status, write_status = decoding(path)
    print(lack_index, sha256_status, write_status)
