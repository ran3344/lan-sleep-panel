import os
import ipaddress
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置类"""

    # Flask 配置
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # 安全配置
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    APP_USERNAME = os.getenv('APP_USERNAME', '')
    APP_PASSWORD = os.getenv('APP_PASSWORD', '')

    # IP 白名单配置
    IP_WHITELIST_STR = os.getenv('IP_WHITELIST', '')

    @classmethod
    def get_ip_whitelist(cls):
        """解析 IP 白名单列表"""
        if not cls.IP_WHITELIST_STR:
            return []
        return [ip.strip() for ip in cls.IP_WHITELIST_STR.split(',') if ip.strip()]

    @classmethod
    def is_ip_allowed(cls, client_ip: str) -> bool:
        """检查客户端 IP 是否在白名单内"""
        whitelist = cls.get_ip_whitelist()
        if not whitelist:
            return True

        try:
            ip_obj = ipaddress.ip_address(client_ip)
        except ValueError:
            return False

        for entry in whitelist:
            try:
                if '/' in entry:
                    network = ipaddress.ip_network(entry, strict=False)
                    if ip_obj in network:
                        return True
                elif ip_obj == ipaddress.ip_address(entry):
                    return True
            except ValueError:
                if client_ip == entry:
                    return True
        return False

    @classmethod
    def validate_login(cls, username: str, password: str) -> bool:
        """验证登录账号密码"""
        return username == cls.APP_USERNAME and password == cls.APP_PASSWORD

    @classmethod
    def validate(cls):
        """验证必要配置项"""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY 环境变量未设置，请在 .env 文件中配置")
        if not cls.APP_USERNAME:
            raise ValueError("APP_USERNAME 环境变量未设置，请在 .env 文件中配置")
        if not cls.APP_PASSWORD:
            raise ValueError("APP_PASSWORD 环境变量未设置，请在 .env 文件中配置")
        return True
