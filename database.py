# 数据库操作模块
import sqlite3
import logging
import time
from typing import Optional, List, Tuple
from contextlib import contextmanager
from config import Config

logger = logging.getLogger(__name__)

class Database:
    """数据库操作类"""
    def __init__(self) -> None:
        self.db_path = Config.DB_NAME
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()
    def _init_db(self) -> None:
        retry = 0
        while retry < 3:
            try:
                if self.conn is None:
                    raise RuntimeError("数据库连接已关闭，无法初始化表结构")
                cursor = self.conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        verified BOOLEAN DEFAULT 0,
                        last_active INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_topics (
                        user_id INTEGER PRIMARY KEY,
                        topic_id INTEGER,
                        topic_name TEXT,
                        created_at INTEGER
                    )
                """)
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, verified, last_active) VALUES (?, 1, ?)", 
                    (Config.OWNER_ID, int(time.time()))
                )
                if self.conn is None:
                    raise RuntimeError("数据库连接已关闭，无法提交事务")
                self.conn.commit()
                logger.info("数据库初始化完成")
                return
            except Exception as e:
                retry += 1
                logger.error(f"数据库初始化失败（第{retry}次）: {e}")
                time.sleep(1)
        raise RuntimeError("数据库初始化失败，已重试3次")
    def _ensure_connection(self):
        """确保数据库连接可用，不可用时自动重连。"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            logger.warning("数据库连接为None，已自动重连")
            return
        try:
            self.conn.execute('SELECT 1')
        except Exception:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            logger.warning("数据库连接已断开，已自动重连")

    @contextmanager
    def get_cursor(self):
        self._ensure_connection()
        if self.conn is None:
            raise RuntimeError("数据库连接已关闭，无法获取游标")
        try:
            cursor = self.conn.cursor()
            try:
                yield cursor
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                logger.error(f"数据库操作异常: {e}")
                raise
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"获取数据库游标失败: {e}")
            raise
    def is_user_verified(self, user_id: int) -> bool:
        """检查用户是否已验证"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
    def verify_user(self, user_id: int) -> None:
        """验证用户"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, verified, last_active) VALUES (?, 1, ?)", 
                (user_id, int(time.time()))
            )
        logger.info(f"用户 {user_id} 已通过验证")
    def update_user_activity(self, user_id: int) -> None:
        """更新用户活跃时间"""
        if user_id == Config.OWNER_ID:
            return
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (int(time.time()), user_id)
            )
        logger.debug(f"已更新用户 {user_id} 的活跃时间")
    def get_recent_users(self, top_n: int = 1) -> List[int]:
        """获取最近活跃的用户列表"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM users WHERE verified=1 AND user_id!=? ORDER BY last_active DESC LIMIT ?", 
                (Config.OWNER_ID, top_n)
            )
            return [row[0] for row in cursor.fetchall()]
    def get_verified_users(self) -> List[int]:
        """获取所有已验证的用户列表（不包括管理员）"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE verified=1 AND user_id!=?", (Config.OWNER_ID,))
            return [row[0] for row in cursor.fetchall()]
    def save_user_topic(self, user_id: int, topic_id: int, topic_name: str) -> None:
        """保存用户话题关联信息"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO user_topics (user_id, topic_id, topic_name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, topic_id, topic_name, int(time.time()))
            )
        logger.info(f"已为用户 {user_id} 保存话题 {topic_id}: {topic_name}")
    def get_user_topic(self, user_id: int) -> Tuple[Optional[int], Optional[str]]:
        """获取用户对应的话题信息"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT topic_id, topic_name FROM user_topics WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
            return (result[0], result[1]) if result else (None, None)
    def get_user_by_topic(self, topic_id: int) -> Optional[int]:
        """根据话题ID获取对应的用户ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_topics WHERE topic_id=?", (topic_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {e}")
            finally:
                self.conn = None

