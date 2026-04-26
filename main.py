import logging
import os
import json
import random
from datetime import date, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue, ChatMemberHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"
GROUP_FILE = "groups.json"

user_data = {}
group_ids = set()

def load_data():
    global user_data, group_ids
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
        if os.path.exists(GROUP_FILE):
            with open(GROUP_FILE, "r", encoding="utf-8") as f:
                group_ids = set(json.load(f))
    except:
        pass

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        with open(GROUP_FILE, "w", encoding="utf-8") as f:
            json.dump(list(group_ids), f)
    except Exception as e:
        logger.error(f"保存失败: {e}")

def get_user_data(user_id: int):
    uid = str(user_id)
    today = str(date.today())
    if uid not in user_data:
        user_data[uid] = {
            "gold": 1000, "feed": 50, "birds": 0, "nests": 4,
            "level": 1, "exp": 0,
            "combat": 100, "stamina": 0, "strength": 0, "intelligence": 0, "agility": 0,
            "feed_count_today": 0, "last_feed_date": today, "last_checkin": "",
            "nickname": ""
        }
    return user_data[uid]

def add_exp(user_id: int, amount: int):
    user = get_user_data(user_id)
    user["exp"] += amount
    old_level = user["level"]
    LEVELS = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 999999]
    while user["level"] < 9 and user["exp"] >= LEVELS[user["level"]]:
        user["level"] += 1
        user["gold"] += 300
        user["combat"] *= 2
        user["stamina"] += 25
        user["strength"] += 15
        user["intelligence"] += 15
        user["agility"] += 15
    return user["level"] > old_level

def calculate_combat(user):
    if user["birds"] == 0:
        return 0
    per = {"stamina": 25, "strength": 18, "intelligence": 20, "agility": 15}
    base = user["combat"] + (per["strength"] * user["birds"]) * 1.2 + (per["agility"] * user["birds"]) * 0.8
    return int(base * (1 + (per["intelligence"] * user["birds"]) / 200))

# ================== 键盘 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥚 捡蛋", callback_data="pick_egg"), InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🌾 喂养", callback_data="feed_birds"), InlineKeyboardButton("🧹 清扫", callback_data="clean_dung")],
        [InlineKeyboardButton("💰 出售全部", callback_data="sell_all"), InlineKeyboardButton("🛒 购买🦜", callback_data="buy_bird")],
        [InlineKeyboardButton("⚔️ PK", callback_data="pk_menu"), InlineKeyboardButton("🦜 官网", callback_data="official_web")],
    ])

def pk_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 随机匹配", callback_data="pk_random")],
        [InlineKeyboardButton("👤 指定挑战", callback_data="pk_target")],
        [InlineKeyboardButton("← 返回", callback_data="back_to_main")]
    ])

async def send_panel(update: Update, edit: bool = False):
    user = get_user_data(update.effective_user.id)
    combat = calculate_combat(user)
    text = f"🦜 **飞鸟牧场**（{user['level']}级）\n💰 金币：{user['gold']} | 🌾 鸟粮：{user['feed']}\n🦜 鹦鹉：{user['birds']}/4 | ⚔️ 战斗力：{combat}\n⭐ 经验：{user['exp']}/1000+"
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

# ================== 按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_data(update.effective_user.id)
    data = query.data
    await query.answer("✅ 操作成功！")

    if data == "official_web":
        await query.message.reply_text("🦜 **飞鸟牧场官网**\nhttps://www.niaocoin.xyz/", parse_mode='Markdown')
        return

    elif data == "feed_birds":
        if user['feed'] >= 10 and user.get("feed_count_today", 0) < 5:
            user['feed'] -= 10
            user["feed_count_today"] = user.get("feed_count_today", 0) + 1
            exp_gain = random.randint(45, 65)
            leveled = add_exp(update.effective_user.id, exp_gain)
            await query.message.reply_text(f"🌾 喂养成功！+{exp_gain}经验")
            if leveled:
                await query.message.reply_text("🎉 升级！战斗力翻倍！")
        else:
            await query.message.reply_text("❌ 鸟粮不足或今日喂养次数已满")

    elif data == "buy_bird":
        if user['birds'] >= 4:
            await query.message.reply_text("❌ 最多4只🦜")
        elif user['gold'] >= 800:
            user['gold'] -= 800
            user['birds'] += 1
            await query.message.reply_text(f"✅ 购买成功！当前 {user['birds']} 只")
        else:
            await query.message.reply_text("❌ 金币不足")

    elif data == "pick_egg":
        reward = 60 + user['birds'] * 30 + user['level'] * 10
        user['gold'] += reward
        await query.message.reply_text(f"✅ 捡蛋成功！+{reward}金币")

    elif data == "rush_produce":
        user['feed'] = min(user['feed'] + 20, 300)
        await query.message.reply_text("✅ 赶产成功！")

    elif data == "clean_dung":
        add_exp(update.effective_user.id, 30)
        await query.message.reply_text("✅ 清扫成功！")

    elif data == "sell_all":
        earnings = user['birds'] * 120
        user['gold'] += earnings
        await query.message.reply_text(f"✅ 出售成功！+{earnings}金币")

    save_data()
    await send_panel(update, edit=True)

# ================== 命令 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！初始金币1000")
    await send_panel(update)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("🏆 暂无排行")
        return
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['gold'], reverse=True)[:10]
    text = "🏆 **全球排行榜** 🏆\n\n"
    for i, (uid, d) in enumerate(sorted_users, 1):
        text += f"{i}. 用户{uid[-4:]} — {d['gold']} 金币 ({d.get('level',1)}级)\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def checkin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    today = str(date.today())
    if user.get("last_checkin") == today:
        await update.message.reply_text("❌ 今天已签到")
        return
    user["gold"] += 10
    user["last_checkin"] = today
    add_exp(update.effective_user.id, 30)
    await update.message.reply_text("✅ 签到成功！+10金币 +30经验")
    save_data()

# ================== 主函数 ==================
def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    try:
        app.job_queue.run_daily(daily_checkin_notice, time=time(0, 0, 0))
    except:
        pass

    app.add_handler(ChatMemberHandler(track_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_farm))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", checkin_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 机器人启动成功")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
