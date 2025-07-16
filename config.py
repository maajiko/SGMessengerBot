# 配置管理模块
import os
from typing import Optional
from dotenv import load_dotenv
import logging
import re

load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    """机器人配置类"""
    BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    GROUP_ID: int = int(os.getenv("GROUP_ID", "0"))
    DB_NAME: str = os.getenv("DB_NAME", "forward_bot.db")
    FLOOD_LIMIT_SECONDS: int = int(os.getenv("FLOOD_LIMIT_SECONDS", "5"))

    @classmethod
    def validate(cls) -> None:
        """验证配置有效性"""
        if not cls.BOT_TOKEN or not isinstance(cls.BOT_TOKEN, str) or len(cls.BOT_TOKEN) < 30:
            raise ValueError("BOT_TOKEN 未设置或格式不正确")
        if not re.match(r'^\d+$', str(cls.OWNER_ID)) or int(cls.OWNER_ID) <= 0:
            raise ValueError("OWNER_ID 必须为正整数")
        if not re.match(r'^-?\d+$', str(cls.GROUP_ID)) or int(cls.GROUP_ID) == 0:
            raise ValueError("GROUP_ID 必须为非零整数")
        if not isinstance(cls.DB_NAME, str) or not cls.DB_NAME.endswith('.db'):
            raise ValueError("DB_NAME 配置不正确，必须以 .db 结尾")
        if not isinstance(cls.FLOOD_LIMIT_SECONDS, int) or not (1 <= cls.FLOOD_LIMIT_SECONDS <= 3600):
            raise ValueError("FLOOD_LIMIT_SECONDS 配置不正确，必须为1-3600之间的整数")
        token_preview = cls.BOT_TOKEN[:5] + "..." if cls.BOT_TOKEN else "None"
        logger.info(f"配置验证通过: BOT_TOKEN={token_preview}, OWNER_ID={cls.OWNER_ID}, GROUP_ID={cls.GROUP_ID}")

