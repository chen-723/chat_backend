# 服务器配置文件
# 部署时可以通过环境变量或直接修改这个文件

import os

# 服务器IP配置
# 优先使用环境变量，否则使用默认值
# 开发环境使用 localhost
# 生产环境改为服务器IP，例如: '192.168.1.100'
# SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_HOST = os.getenv("SERVER_HOST", "192.168.2.38")

# 服务器端口
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# 获取完整的服务器地址
def get_server_url() -> str:
    """返回完整的服务器URL"""
    #这里记得修改有没有https
    return f"https://{SERVER_HOST}:{SERVER_PORT}"

# 获取静态文件访问地址
def get_static_url(path: str) -> str:
    """
    返回静态文件的完整URL
    :param path: 相对路径，例如 '/static/avatars/xxx.jpg'
    """
    return f"{get_server_url()}{path}"
