# fileProject

一个基于 HTTP 请求的隐蔽文件传输工具。客户端将文件分块、加密并编码为 Base64，随后作为 URL 路径片段通过 GET 请求发送到服务端；服务端在收到全部分片后重组、校验并还原文件。

## 功能特性

- **分块传输**：大文件按固定大小切分为多个分片，逐片发送。
- **轻量加密**：对字节按奇偶性进行数值翻转（`255 - x`），避免明文传输。
- **完整性校验**：使用 SHA-256 校验还原后的文件，确保数据未被篡改或缺失。
- **断点续传**：服务端返回缺失的分片索引，客户端自动补发缺失分片。
- **文件服务**：内置 Flask 文件上传、目录浏览与下载页面。
- **路径安全**：所有文件访问均做目录遍历防护。

## 项目结构

```
fileProject/
├── file_codec.py      # 编码 / 解码核心逻辑
├── file_codec_test.py # 编解码测试代码
├── client.py          # 客户端：发送编码后的文件分片
├── server.py          # 服务端：接收分片并提供文件服务
├── templates/         # 服务端 HTML 模板
│   ├── upload_page.html  # 上传页面
│   └── file_list.html    # 目录浏览页面
├── server_files/      # 服务端还原后的文件存储目录
└── server_tmp/        # 服务端接收到的分片临时存储目录
```

## 环境要求

- Python 3
- 依赖库：

```bash
pip install flask requests
```

## 工作原理

1. **编码**（`file_codec.py`）
   - 读取原始文件，计算 SHA-256。
   - 对数据做轻量加密，并添加文件 ID、分片索引、总分片数、文件名与摘要等前缀信息。
   - 每个分片转为 Base64 文本，写入 `client_tmp/<file_id>.txt`，每行一个分片。
2. **发送**（`client.py`）
   - 随机打乱分片顺序后逐行读取。
   - 以 `GET {base_url}/wskkey<base64>` 形式发送，服务端将 URL 路径作为载荷接收。
3. **接收与还原**（`server.py`）
   - `/log/<base64_content>` 接口校验 `wskkey` 前缀后，将分片追加到 `server_tmp/<file_id>.txt`。
   - 尝试重组、解密并通过 SHA-256 校验，成功后写入 `server_files/<文件名>`。
   - 返回仍需补发的分片索引，客户端据此循环补发直到完整。

## 使用方法

### 1. 启动服务端

```bash
python server.py
```

默认监听 `0.0.0.0:80`。

### 2. 发送文件

编辑 `client.py` 中的文件路径与目标地址后运行：

```bash
python client.py
```

其中：

- `file_codec.encoding(file_codec.CLIENT_FILES_DIR, "DJI_0006.JPG")` 指定待发送文件。
- `base_url` 指定服务端地址，例如 `http://127.0.0.1/log`。

> 注意：客户端编码依赖 `client_files` 目录（存放待发送文件）与 `client_tmp` 目录（存放编码结果），请提前创建。

### 3. 直接编解码（可选）

`file_codec_test.py` 用于本地测试编解码流程：

```bash
python file_codec_test.py
```

## 服务端接口

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 重定向到文件列表 |
| GET | `/files/<path:filename>` | 浏览目录 / 下载文件 |
| GET | `/upload` | 上传页面 |
| POST | `/upload` | 处理文件上传，支持指定子路径 |
| GET | `/log/<base64_content>` | 接收文件分片并尝试还原 |

## 安全说明

- 服务端已对文件路径做目录遍历防护（`relative_to` 校验）。
- `/log` 接口仅接受以 `wskkey` 开头的请求。
- 本工具用于学习与研究网络传输原理，请勿用于未授权的场景。
