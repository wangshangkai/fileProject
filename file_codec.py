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


def encrypt(binary_data):
    """对字节流做可逆的奇偶翻转加解密。

    规则：满足 (x <= 127 且 x 为奇数) 或 (x > 127 且 x 为偶数) 的字节取 255 - x，其余保持不变。
    该操作是自逆的，加密与解密使用同一函数。
    示例：0->0, 1->254, 2->2, 3->252, ..., 127->128, 128->127, 129->129, ..., 254->1, 255->255。

    Args:
        binary_data (bytes): 待处理的字节流。

    Returns:
        bytes: 处理后的字节流。
    """
    result = []
    for i in range(len(binary_data)):
        x = binary_data[i]
        result.append(255 - x if (x <= 127 and x % 2 == 1) or (x > 127 and x % 2 == 0) else x)
    return bytes(result)


def split_data(binary_data):
    """将字节流切分为若干分片，使每片加上头部后总长不超过 CHUNK_SIZE。

    首片头部为 FIRST_HEADER_LEN，其余片头部为 OTHER_HEADER_LEN，
    因此首片数据段长度为 CHUNK_SIZE - FIRST_HEADER_LEN，
    后续每片数据段长度为 CHUNK_SIZE - OTHER_HEADER_LEN。

    Args:
        binary_data (bytes): 待切分的字节流。

    Returns:
        list[bytes]: 分片列表。
    """
    if len(binary_data) <= CHUNK_SIZE - FIRST_HEADER_LEN:
        return [binary_data]
    result = [binary_data[:CHUNK_SIZE - FIRST_HEADER_LEN]]
    for i in range(CHUNK_SIZE - FIRST_HEADER_LEN, len(binary_data), CHUNK_SIZE - OTHER_HEADER_LEN):
        result.append(binary_data[i: i + CHUNK_SIZE - OTHER_HEADER_LEN])
    return result


def combine_data(split_binary_data, total):
    """按序号拼接收到的分片。

    Args:
        split_binary_data (dict[int, bytes]): {序号: 分片数据}。
        total (int): 分片总数。

    Returns:
        tuple[int, bytes]:
            数据完整时返回 (total, 拼接后的字节流)；
            数据缺失时返回 (缺失的序号, b'')。
    """
    result = b''
    for i in range(total):
        if i in split_binary_data:
            result = result + split_binary_data[i]
        else:
            return i, b''
    return total, result


def encoding_data(binary_data, file_id, path, sha256):
    """为各分片添加协议头部。

    头部布局：
        首片：file_id(4B) / index(4B) / total_index(4B) / path(20B) / sha256(32B) / data
        其余：file_id(4B) / index(4B) / data

    Args:
        binary_data (bytes): 已加密的字节流。
        file_id (int): 文件 ID。
        path (str): 文件名，最长 STR_LEN 字节。
        sha256 (bytes): 原始文件（加密前）的 SHA-256 摘要。

    Returns:
        list[bytes]: 添加头部后的分片列表。
    """
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


def get_file_id(base64_data):
    """从单个 Base64 分片中解析出所属的 file_id。

    Args:
        base64_data (str): 一行 Base64 编码的分片。

    Returns:
        int: 该分片对应的 file_id。
    """
    data = base64.b64decode(base64_data)
    file_id = int.from_bytes(data[0: INT_LEN], byteorder='big')
    return file_id


def decoding_data(encoding_binary_data):
    """解析各分片头部并合并数据。

    Args:
        encoding_binary_data (list[bytes]): 各分片的原始字节。

    Returns:
        tuple[bytes, int, str, bytes, int]:
            (合并后的字节流, file_id, 文件名, sha256, 缺失序号)。
            数据不完整时字节流为 b''，缺失序号为第一个缺失的分片下标。
    """
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


def encoding(file_name, output_dir):
    """将原始文件编码为「加密 + 分段 + Base64」的 txt 文件。

    流程：读取文件 -> 计算 SHA-256（加密前）-> 加密 -> 添加分片头部
    -> Base64 编码 -> 每行一片写入 output_dir/<file_id>.txt。

    Args:
        file_name (str): 待编码文件的完整路径。
        output_dir (str): 分片文件的输出目录。

    Returns:
        Path: 生成的分片文件路径。
    """
    file_path = Path(file_name)
    name = file_path.name
    with open(file_path, 'rb') as file:
        binary_data = file.read()

    file_id = random.randint(FILE_ID_MIN, FILE_ID_MAX)
    while (Path(output_dir) / f"{file_id}.txt").exists():
        file_id = random.randint(FILE_ID_MIN, FILE_ID_MAX)
    sha256 = hashlib.sha256(binary_data).digest()  # sha256在加密前
    binary_data = encrypt(binary_data)  # 加密
    encoding_binary_data = encoding_data(binary_data, file_id, name, sha256)  # 添加前缀

    # 将二进制数据编码为Base64
    base64_data = [base64.b64encode(da).decode() for da in encoding_binary_data]
    tmp_file_path = Path(output_dir) / f"{file_id}.txt"
    with open(tmp_file_path, 'w') as f:
        f.write('\n'.join(base64_data))
    print(f"Done! Write to file {tmp_file_path}")
    return tmp_file_path


def decoding(file_name, output_dir):
    """将「加密 + 分段 + Base64」的 txt 文件还原为原始文件。

    流程：读取分片 -> Base64 解码 -> 解析合并 -> 解密 -> SHA-256 校验
    -> 写入 output_dir/<文件名>。

    Args:
        file_name (str): 分片 txt 文件路径。
        output_dir (str): 还原后文件的输出目录。

    Returns:
        tuple[int, bool, bool]:
            (缺失序号, SHA-256 是否校验通过, 是否成功写入)。
            分片不完整时返回 (缺失序号, False, False)。
    """
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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="文件分片编解码工具")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('-encoding', action='store_true', help="将原始文件编码为分片 txt 文件")
    mode.add_argument('-decoding', action='store_true', help="将分片 txt 文件还原为原始文件")
    parser.add_argument('file_name', help="待处理文件路径")
    parser.add_argument('output_dir', help="输出目录")
    args = parser.parse_args()
    if args.encoding:
        result = encoding(args.file_name, args.output_dir)
    else:
        result = decoding(args.file_name, args.output_dir)
    print(result)
