import logging
import sys
from datetime import datetime

# 创建logger
logger = logging.getLogger("crypto_ticker")
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

# 确保logger没有重复的处理器
if not logger.handlers:
    # 添加处理器到logger
    logger.addHandler(console_handler) 