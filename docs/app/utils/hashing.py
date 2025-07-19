import hashlib

def hash_file(file_b: bytes) -> str:
    """生成文件内容的 SHA-256 哈希值"""
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest() 