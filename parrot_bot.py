import logging
from datetime import datetime, timedelta
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.orm import sessionmaker, declarative_base

logging.basicConfig(level=logging.INFO)

# ==================== 数据库 ====================
Base = declarative_base()
engine = create_engine('sqlite:///parrot_bot.db', echo=False)
Session = sessionmaker(bind=engine)

class UserData(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    parrot_name = Column(String, default="小鹦鹉 🦜")
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    feed = Column(Integer, default=50)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    happiness = Column(Integer, default=80)
    hunger = Column(Integer, default=50)
    daily_feed_from_chat = Column(Integer, default=0)
    last_checkin = Column(DateTime, nullable=True)
    last_chat_activity = Column(DateTime, nullable=True)

Base.metadata.create_all(engine)

TOKEN = "8404875405:AAG9rnJWazgbwZnRgTOY58Jeyr0B29iPOx0"  

# ==================== 主菜单 ====================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user=None):
    if not user:
        session = Session()
        user = session.query(UserData).filter_by(user_id=update.effective_user.id).first()
        if not user:
            user = UserData(user_id=update.effective_user.id)
            session.add(user)
            session.commit()
        session.close()

    status = f"🐦 **{user.parrot_name}** 当前状态\n\n"
    status += f"等级：{user.level}/9　经验：{user.exp}　饲料：{user.feed}\n"
    status += f"战绩：{user.wins}胜 {user.losses}负\n"
    status += f"快乐度：{user.happiness}%　饥饿度：{user.hunger}%\n"
    status += f"今日群聊活跃：{user.daily_feed_from_chat}/50"

    keyboard = [
        [InlineKeyboardButton("📅 每日签到", callback_data="checkin")],
        [InlineKeyboardButton("🍎 喂养宠物", callback_data="feed")],
        [InlineKeyboardButton("⚔️ 宠物PK", callback_data="pk_menu")],
        [InlineKeyboardButton("👤 我的宠物", callback_data="my_pet")],
        [InlineKeyboardButton("🏆 排行榜", callback_data="ranking")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(status, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(status, reply_markup=reply_markup, parse_mode='Markdown')
    except:
        await update.message.reply_text(status, reply_markup=reply_markup, parse_mode='Markdown')

# ==================== 签到 ====================
async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = Session()
    user = session.query(UserData).filter_by(user_id=user_id).first()
    if not user:
        user = UserData(user_id=user_id)
        session.add(user)

    now = datetime.now()
    if user.last_checkin and user.last_checkin.date() == now.date():
        await query.message.reply_text("✅ 你今天已经签到过了，明天再来吧！")
    else:
        reward = 30 + user.level * 5
        user.feed += reward
        user.exp += reward // 2
        user.last_checkin = now
        user.happiness = min(100, user.happiness + 10)
        await query.message.reply_text(f"📅 签到成功！获得 {reward} 饲料 和 {reward//2} 经验 🦜")

    session.commit()
    await show_main_menu(update, context, user)
    session.close()

# ==================== 喂养 ====================
async def feed_pet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = Session()
    user = session.query(UserData).filter_by(user_id=user_id).first()
    if not user:
        user = UserData(user_id=user_id)
        session.add(user)

    if user.feed < 10:
        await query.message.reply_text("饲料不足！先去签到或在群里发言获得饲料吧～")
    else:
        user.feed -= 10
        user.exp += 15
        user.hunger = max(0, user.hunger - 20)
        user.happiness = min(100, user.happiness + 15)
        await query.message.reply_text("🍎 已成功喂养！鹦鹉很开心 (+15经验)")

        while user.exp >= user.level * 25 and user.level < 9:
            user.level += 1
            await query.message.reply_text(f"🎉 恭喜！你的鹦鹉升级到 **{user.level} 级** 了！")

    session.commit()
    await show_main_menu(update, context, user)
    session.close()

# ==================== PK 菜单 ====================
async def pk_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🎲 随机匹配PK", callback_data="pk_random")],
        [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="back_main")]
    ]
    await query.message.edit_text("⚔️ 选择PK模式：", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== 随机PK ====================
async def pk_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = Session()
    player = session.query(UserData).filter_by(user_id=user_id).first()
    if not player:
        player = UserData(user_id=user_id)
        session.add(player)

    opponent_level = max(1, player.level + random.randint(-2, 3))
    opponent_name = random.choice(["小绿鹦", "胖胖鸟", "聪明哥", "叫叫君", "闪闪"])

    player_power = player.level * 10 + player.happiness + random.randint(0, 30)
    opponent_power = opponent_level * 10 + random.randint(0, 40)

    if player_power > opponent_power:
        result = f"🎉 胜利！你的 {player.parrot_name} 打败了 {opponent_name}（{opponent_level}级）"
        player.wins += 1
        player.feed += 25
        player.exp += 20
    else:
        result = f"😔 惜败… {opponent_name}（{opponent_level}级）太强了"
        player.losses += 1
        player.feed += 8

    await query.message.reply_text(result)
    session.commit()
    await show_main_menu(update, context, player)
    session.close()

# ==================== 按钮总处理器 ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "checkin":
        await checkin(update, context)
    elif data == "feed":
        await feed_pet(update, context)
    elif data == "pk_menu":
        await pk_menu(update, context)
    elif data == "pk_random":
        await pk_random(update, context)
    elif data == "my_pet" or data == "ranking" or data == "back_main":
        await show_main_menu(update, context)

# ==================== 群内发言活跃奖励 ====================
async def group_chat_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or update.effective_user.is_bot:
        return

    user_id = update.effective_user.id
    now = datetime.now()

    session = Session()
    user = session.query(UserData).filter_by(user_id=user_id).first()
    if not user:
        user = UserData(user_id=user_id)
        session.add(user)

    if user.last_chat_activity and user.last_chat_activity.date() != now.date():
        user.daily_feed_from_chat = 0

    if (user.last_chat_activity and (now - user.last_chat_activity) < timedelta(seconds=60)) or user.daily_feed_from_chat >= 50:
        session.close()
        return

    reward = random.randint(1, 3)
    user.feed += reward
    user.daily_feed_from_chat += reward
    user.last_chat_activity = now
    user.happiness = min(100, user.happiness + 2)

    session.commit()
    session.close()

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🦜 群里发言活跃！获得 +{reward} 饲料（今日已获 {user.daily_feed_from_chat}/50）"
        )
    except:
        pass

# ==================== Start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

# ==================== 主程序 ====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkin", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group_chat_activity))

    print("🦜 鹦鹉喂养机器人已启动... 发送 /start 开始使用")
    app.run_polling()

if __name__ == "__main__":
    main()
