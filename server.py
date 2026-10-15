import logging

from flask import Flask, send_from_directory, abort, render_template, request, redirect, url_for, flash
from pathlib import Path
import file_codec

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于flash消息加密
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)  # 只记录错误

# 配置文件服务目录
FILE_SERVER_ROOT = Path("./server_files")
TMP_DIR = Path("./server_tmp")

# 服务监听配置
HOST = '0.0.0.0'
PORT = 80

# 确保必要目录存在
FILE_SERVER_ROOT.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查是否有文件被上传
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    # 检查是否选择了文件
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    # 上传路径与安全检查
    upload_path = request.form.get('path', '')
    if upload_path:
        target_dir = FILE_SERVER_ROOT / upload_path
        # 安全检查
        try:
            target_dir.resolve().relative_to(FILE_SERVER_ROOT.resolve())
        except ValueError:
            abort(403)
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = FILE_SERVER_ROOT

    # 保存文件
    save_path = target_dir / file.filename
    file.save(save_path)
    flash(f'File {file.filename} uploaded successfully to {upload_path or "/"}')
    return redirect(url_for('serve_files', filename=upload_path))


@app.route('/upload', methods=['GET'])
def upload_file_page():
    # GET请求显示上传表单
    return render_template('upload_page.html')


@app.route('/')
def main_page():
    return redirect(request.url + "files/")


@app.route('/files/<path:filename>')
@app.route('/files/')
def serve_files(filename=''):
    target_path = FILE_SERVER_ROOT / filename
    # 安全检查：防止目录遍历攻击
    try:
        target_path.resolve().relative_to(FILE_SERVER_ROOT.resolve())
    except ValueError:
        abort(403)  # 禁止访问超出根目录的路径

    # 如果是目录，显示目录列表
    if target_path.is_dir():
        files = []
        dirs = []
        for item in target_path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                dirs.append(item.name)

        # 生成目录列表HTML
        return render_template('file_list.html', path=filename or '/', dirs=dirs,
                               files=files, is_root=(filename == ''))

    # 如果是文件，发送文件内容
    elif target_path.is_file():
        return send_from_directory(
            FILE_SERVER_ROOT,
            filename,
            as_attachment=False  # False表示尝试在浏览器中显示，True强制下载
        )

    # 文件不存在
    else:
        abort(404)


@app.route('/log/<path:base64_content>')
def log_request(base64_content):
    if not base64_content.startswith(file_codec.KEY_PREFIX):
        print("Key error")
        return "Key error", 200
    base64_content = base64_content[len(file_codec.KEY_PREFIX):]
    # 获取文件名
    try:
        file_id = file_codec.decoding_first_line(base64_content)
        filename = TMP_DIR / f"{file_id}.txt"
    except:
        print("Base64 error")
        return "Base64 error", 200

    # 将内容写入文件
    with open(filename, 'a') as f:
        f.write(base64_content + '\n')
    lack_index, sha256_status, write_status = file_codec.decoding(filename, FILE_SERVER_ROOT)
    return f"Need {lack_index} file_id {file_id} sha256 {sha256_status} write {write_status}", 200


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=True)
