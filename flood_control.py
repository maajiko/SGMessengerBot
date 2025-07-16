# 防洪控制模块
import time
import logging
from collections import defaultdict
from typing import Dict
from config import Config

logger = logging.getLogger(__name__)

MAX_IDLE_SECONDS = 3600 * 24  # 24小时未活跃自动清理

class FloodControl:
    """防洪控制类"""
    def __init__(self) -> None:
        self.last_message_time: Dict[int, float] = defaultdict(float)
    def check_flood(self, user_id: int) -> bool:
        """检查用户是否发送消息过于频繁"""
        self._cleanup_idle_users()
        if user_id == Config.OWNER_ID:
            return False
        current_time = time.time()
        last_time = self.last_message_time.get(user_id, 0)
        if current_time - last_time < Config.FLOOD_LIMIT_SECONDS:
            logger.debug(f"用户 {user_id} 发送消息过于频繁")
            return True
        self.last_message_time[user_id] = current_time
        return False
    def reset_user_flood(self, user_id: int) -> None:
        """重置用户的防洪状态"""
        if user_id in self.last_message_time:
            del self.last_message_time[user_id]
            logger.debug(f"已重置用户 {user_id} 的防洪状态")
    def _cleanup_idle_users(self):
        now = time.time()
        to_delete = [uid for uid, t in self.last_message_time.items() if now - t > MAX_IDLE_SECONDS]
        for uid in to_delete:
            del self.last_message_time[uid]
            logger.debug(f"已清理长时间未活跃的用户 {uid}")

