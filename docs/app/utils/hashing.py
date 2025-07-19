import hashlib

def hash_file(file_b: bytes) -> str:
    """
    生成文件内容的SHA-256哈希值，用于唯一标识上传文件。
    """
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest() 