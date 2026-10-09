import file_codec

SERVER_FILES_DIR = "server_files"


if __name__ == '__main__':
    path = file_codec.encoding(file_codec.CLIENT_FILES_DIR, "DJI_0002.JPG")
    print(path)
    lack_index, sha256_status, write_status = file_codec.decoding(path, SERVER_FILES_DIR)
    print(lack_index, sha256_status, write_status)
