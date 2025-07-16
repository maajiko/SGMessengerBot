# Telegram消息处理模块
import logging
from typing import Optional, Dict, Any, Union, cast
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Message
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TelegramError
from config import Config
from database import Database
from flood_control import FloodControl

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 命令"""
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if user_id == Config.OWNER_ID:
        keyboard = ReplyKeyboardMarkup([
            ["全体广播"]
        ], resize_keyboard=True)
        await update.message.reply_text(
            "管理员您好！请使用下方菜单操作",
            reply_markup=keyboard
        )
        return
    if context.application.bot_data['db'].is_user_verified(user_id):
        await update.message.reply_text("您已验证，可以直接发送消息给主人。")
    else:
        keyboard = [[InlineKeyboardButton("我不是机器人", callback_data="verify")]]
        await update.message.reply_text(
            "请点击下方按钮证明您不是机器人：",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户验证回调"""
    if not update.callback_query or not update.callback_query.from_user:
        return
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id == Config.OWNER_ID:
        await query.edit_message_text("您已是管理员，无需验证")
        return
    context.application.bot_data['db'].verify_user(user_id)
    await query.edit_message_text("验证成功！您现在可以给主人发送消息了。")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理普通用户消息"""
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name if update.effective_user.first_name else ""
    if user_id == Config.OWNER_ID:
        return
    if context.application.bot_data['flood_control'].check_flood(user_id):
        await update.message.reply_text(f"您发送得太快了，请等待{Config.FLOOD_LIMIT_SECONDS}秒后再试！")
        return
    if not context.application.bot_data['db'].is_user_verified(user_id):
        keyboard = [[InlineKeyboardButton("我不是机器人", callback_data="verify")]]
        await update.message.reply_text(
            "请点击下方按钮证明您不是机器人：",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    try:
        context.application.bot_data['db'].update_user_activity(user_id)
        await process_user_message(update, context, user_id, user_name)
    except Exception as e:
        logger.error(f"处理用户 {user_id} 的消息失败: {e}")
        try:
            if update.message:
                await update.message.forward(Config.OWNER_ID)
        except Exception as e2:
            logger.error(f"转发给主人也失败: {e2}")

async def process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_name: str) -> None:
    """处理用户消息的核心逻辑"""
    if not update.message:
        return
    topic_id, topic_name = context.application.bot_data['db'].get_user_topic(user_id)
    if not topic_id:
        topic_id = await create_user_topic(context, user_id, user_name)
        if not topic_id:
            if update.message:
                await update.message.forward(Config.OWNER_ID)
            return
    try:
        if update.effective_chat and update.effective_chat.id is not None and update.message.message_id is not None:
            await context.bot.forward_message(
                chat_id=Config.GROUP_ID,
                message_thread_id=topic_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        else:
            if update.message:
                await update.message.forward(Config.OWNER_ID)
    except Exception as e:
        logger.error(f"转发消息到话题失败: {e}")
        if update.message:
            await update.message.forward(Config.OWNER_ID)

async def create_user_topic(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_name: str) -> Optional[int]:
    """为用户创建新话题"""
    try:
        topic_name = f"{user_name} ({user_id})"
        topic = await context.bot.create_forum_topic(
            chat_id=Config.GROUP_ID,
            name=topic_name
        )
        topic_id = topic.message_thread_id
        context.application.bot_data['db'].save_user_topic(user_id, topic_id, topic_name)
        logger.info(f"已为用户 {user_id} 创建话题: {topic_name}")
        return topic_id
    except BadRequest as e:
        error_msg = str(e).lower()
        if "chat not found" in error_msg:
            logger.error(f"为用户 {user_id} 创建话题失败: 找不到群组 {Config.GROUP_ID}")
        elif "not a forum" in error_msg:
            logger.error(f"为用户 {user_id} 创建话题失败: 群组 {Config.GROUP_ID} 不是论坛")
        elif "not enough rights" in error_msg:
            logger.error(f"为用户 {user_id} 创建话题失败: 机器人在群组 {Config.GROUP_ID} 中没有足够的权限")
        else:
            logger.error(f"为用户 {user_id} 创建话题失败: {e}")
        return None
    except Exception as e:
        logger.error(f"为用户 {user_id} 创建话题失败: {e}")
        return None

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理群组中的消息"""
    if not update.message or not update.effective_user:
        return
    if not hasattr(update.message, "is_topic_message") or not update.message.is_topic_message:
        return
    if update.effective_user.id != Config.OWNER_ID:
        return
    topic_id = getattr(update.message, "message_thread_id", None)
    if topic_id is None:
        return
    user_id = context.application.bot_data['db'].get_user_by_topic(topic_id)
    if not user_id:
        logger.warning(f"找不到话题 {topic_id} 对应的用户")
        return
    await forward_to_user(context, update, user_id)

def get_msg_caption(msg):
    return msg.caption if hasattr(msg, 'caption') and msg.caption else None

def get_last_name(contact):
    return contact.last_name if hasattr(contact, 'last_name') and contact.last_name else ""

async def send_any_message(context: ContextTypes.DEFAULT_TYPE, msg: Message, chat_id: int) -> None:
    """统一发送任意类型的Telegram消息到指定chat_id"""
    try:
        def get_caption():
            return msg.caption if hasattr(msg, 'caption') and msg.caption else None
        def get_last_name():
            return msg.contact.last_name if hasattr(msg, 'contact') and msg.contact and msg.contact.last_name else ""
        mapping = {
            'text': lambda: context.bot.send_message(chat_id=chat_id, text=msg.text if msg.text is not None else ""),
            'photo': lambda: context.bot.send_photo(chat_id=chat_id, photo=msg.photo[-1].file_id if msg.photo and msg.photo[-1] and hasattr(msg.photo[-1], 'file_id') else "", caption=get_caption()),
            'video': lambda: context.bot.send_video(chat_id=chat_id, video=msg.video.file_id if msg.video and hasattr(msg.video, 'file_id') else "", caption=get_caption()),
            'document': lambda: context.bot.send_document(chat_id=chat_id, document=msg.document.file_id if msg.document and hasattr(msg.document, 'file_id') else "", caption=get_caption()),
            'voice': lambda: context.bot.send_voice(chat_id=chat_id, voice=msg.voice.file_id if msg.voice and hasattr(msg.voice, 'file_id') else "", caption=get_caption()),
            'audio': lambda: context.bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id if msg.audio and hasattr(msg.audio, 'file_id') else "", caption=get_caption()),
            'sticker': lambda: context.bot.send_sticker(chat_id=chat_id, sticker=msg.sticker.file_id if msg.sticker and hasattr(msg.sticker, 'file_id') else ""),
            'video_note': lambda: context.bot.send_video_note(chat_id=chat_id, video_note=msg.video_note.file_id if msg.video_note and hasattr(msg.video_note, 'file_id') else "", length=msg.video_note.length if msg.video_note and hasattr(msg.video_note, 'length') else 0, duration=msg.video_note.duration if msg.video_note and hasattr(msg.video_note, 'duration') else 0),
            'animation': lambda: context.bot.send_animation(chat_id=chat_id, animation=msg.animation.file_id if msg.animation and hasattr(msg.animation, 'file_id') else "", caption=get_caption()),
            'contact': lambda: context.bot.send_contact(chat_id=chat_id, phone_number=msg.contact.phone_number if msg.contact and hasattr(msg.contact, 'phone_number') else "", first_name=msg.contact.first_name if msg.contact and hasattr(msg.contact, 'first_name') else "", last_name=get_last_name()),
            'location': lambda: context.bot.send_location(chat_id=chat_id, latitude=msg.location.latitude if msg.location and hasattr(msg.location, 'latitude') else 0.0, longitude=msg.location.longitude if msg.location and hasattr(msg.location, 'longitude') else 0.0),
            'venue': lambda: context.bot.send_venue(chat_id=chat_id, latitude=msg.venue.location.latitude if msg.venue and hasattr(msg.venue, 'location') and msg.venue.location and hasattr(msg.venue.location, 'latitude') else 0.0, longitude=msg.venue.location.longitude if msg.venue and hasattr(msg.venue, 'location') and msg.venue.location and hasattr(msg.venue.location, 'longitude') else 0.0, title=msg.venue.title if msg.venue and hasattr(msg.venue, 'title') else "", address=msg.venue.address if msg.venue and hasattr(msg.venue, 'address') else ""),
            'poll': lambda: context.bot.send_poll(chat_id=chat_id, question=msg.poll.question if msg.poll and hasattr(msg.poll, 'question') else "", options=[o.text for o in msg.poll.options] if msg.poll and hasattr(msg.poll, 'options') and msg.poll.options else [], is_anonymous=msg.poll.is_anonymous if msg.poll and hasattr(msg.poll, 'is_anonymous') else True, type=msg.poll.type if msg.poll and hasattr(msg.poll, 'type') else ""),
            'dice': lambda: context.bot.send_dice(chat_id=chat_id, emoji=msg.dice.emoji if msg.dice and hasattr(msg.dice, 'emoji') else None),
        }
        for key, func in mapping.items():
            if hasattr(msg, key) and getattr(msg, key):
                await func()
                break
        else:
            try:
                await msg.copy(chat_id=chat_id)
            except Exception as e:
                logger.error(f"消息copy失败: {e}, 类型: {type(msg)}")
                await context.bot.send_message(chat_id=chat_id, text=f"[不支持的消息类型] {type(msg)}")
    except (BadRequest, Forbidden, TelegramError) as e:
        logger.error(f"消息发送异常: {e}, 类型: {type(msg)}")
        await context.bot.send_message(chat_id=chat_id, text=f"[消息发送异常] {str(e)}")
    except Exception as e:
        logger.exception(f"未知异常: {e}, 类型: {type(msg)}")
        raise

async def forward_to_user(context: ContextTypes.DEFAULT_TYPE, update: Update, user_id: int) -> None:
    """将管理员消息转发给用户"""
    if not update.message:
        return
    try:
        await send_any_message(context, update.message, user_id)
        logger.info(f"已将主人的回复发送给用户 {user_id}")
    except Exception as e:
        logger.error(f"发送消息给用户 {user_id} 失败: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理管理员在私聊中的回复"""
    if not update.effective_user or not update.message or not update.message.reply_to_message:
        return
    if update.effective_user.id != Config.OWNER_ID:
        return
    user_id = get_reply_target_user(update, context)
    if not user_id:
        await update.message.reply_text("无法确定回复目标用户，请等待用户发送新消息后再回复")
        return
    try:
        await update.message.copy(chat_id=user_id)
    except Exception as e:
        logger.error(f"回复用户 {user_id} 失败: {e}")
        await update.message.reply_text(f"回复发送失败: {str(e)}")

def get_reply_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    if not update.message or not update.message.reply_to_message:
        return None
    replied_msg = update.message.reply_to_message
    user_id = None
    if hasattr(replied_msg, "forward_from") and replied_msg.forward_from:
        user_id = replied_msg.forward_from.id
    if not user_id:
        recent_users = context.application.bot_data['db'].get_recent_users()
        if recent_users:
            user_id = recent_users[0]
    return user_id

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理全体广播命令"""
    if not update.effective_user or not update.message:
        return
    if update.effective_user.id != Config.OWNER_ID:
        return
    if not hasattr(context, "user_data") or context.user_data is None:
        context.user_data = {}
    context.user_data["broadcast_step"] = "awaiting_content"
    sent_msg = await update.message.reply_text("请输入要广播的内容：")
    context.user_data["command_msg"] = update.message
    context.user_data["prompt_msg"] = sent_msg

async def handle_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理广播内容"""
    if not hasattr(context, "user_data") or context.user_data is None:
        context.user_data = {}
    if context.user_data.get("broadcast_step") != "awaiting_content":
        return
    if not update.message:
        return
    context.user_data["broadcast_content"] = update.message
    context.user_data["broadcast_step"] = "awaiting_confirm"
    keyboard = [
        [
            InlineKeyboardButton("确定", callback_data="confirm_broadcast"),
            InlineKeyboardButton("取消", callback_data="cancel_broadcast")
        ]
    ]
    sent_msg = await update.message.reply_text(
        "确认要发送广播吗？",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["confirm_msg"] = sent_msg

async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """执行广播操作"""
    if not hasattr(update, "callback_query") or not update.callback_query:
        return
    query = update.callback_query
    await query.answer()
    if not hasattr(context, "user_data") or context.user_data is None:
        context.user_data = {}
    if query.data == "cancel_broadcast":
        await clean_broadcast_messages(context)
        return
    await clean_broadcast_messages(context)
    users = context.application.bot_data['db'].get_verified_users()
    success = 0
    failed = 0
    broadcast_msg = context.user_data.get("broadcast_content")
    if not broadcast_msg:
        return
    for user_id in users:
        try:
            await send_broadcast_message(context, broadcast_msg, user_id)
            success += 1
        except Exception as e:
            logger.error(f"广播发送失败给用户 {user_id}: {e}")
            failed += 1
    await context.bot.send_message(
        chat_id=Config.OWNER_ID,
        text=f"广播完成\n成功: {success}人 | 失败: {failed}人"
    )

async def clean_broadcast_messages(context: ContextTypes.DEFAULT_TYPE) -> None:
    """清理广播相关消息"""
    if not hasattr(context, "user_data") or context.user_data is None:
        context.user_data = {}
    for key in ["command_msg", "prompt_msg", "broadcast_content", "confirm_msg"]:
        msg = context.user_data.get(key)
        if msg:
            try:
                await msg.delete()
            except Exception as e:
                logger.debug(f"清理广播消息失败: {e}")

async def send_broadcast_message(context: ContextTypes.DEFAULT_TYPE, broadcast_msg: Any, user_id: int) -> None:
    """发送广播消息给指定用户"""
    await send_any_message(context, broadcast_msg, user_id)

MAX_BROADCAST_DELETE = 250  # 广播相关消息最大删除数

