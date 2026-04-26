import logging
import os
import json
import random
from datetime import date, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, JobQueue, 
    ChatMemberHandler
)

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

def get_user_data(user_id: int, effective_user=None):
    uid = str(user_id)
    today = str(date.today())
    if uid not in user_data:
        user_data[uid] = {
            "gold": 1000, "feed": 50, "birds": 0, "nests": 4,
            "level": 1, "exp": 0, "last_active": 0,
            "combat": 100, "stamina": 0, "strength": 0, "intelligence": 0, "agility": 0,
            "feed_count_today": 0, "last_feed_date": today, "last_checkin": "",
            "nickname": ""
        }
    # 优先更新昵称
    if effective_user:
        full_name = effective_user.full_name or effective_user.first_name or ""
        username = f"@{effective_user.username}" if effective_user.username else ""
        nickname = full_name if full_name else username
        user_data[uid]["nickname"] = nickname or f"用户{uid[-4:]}"
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
    user = get_user_data(update.effective_user.id, update.effective_user)
    combat = calculate_combat(user)
    text = (
        f"🦜 **飞鸟牧场**（{user['level']}级）\n"
        f"💰 金币：{user['gold']}  |  🌾 鸟粮：{user['feed']}\n"
        f"🦜 鹦鹉：{user['birds']}/4  |  ⚔️ 战斗力：{combat}\n"
        f"⭐ 经验：{user['exp']}/1000+"
    )
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"面板错误: {e}")

# ================== 群ID记录 & 每日签到 ==================
async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.my_chat_member and update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
        chat_id = update.effective_chat.id
        if chat_id not in group_ids:
            group_ids.add(chat_id)
            save_data()
            await context.bot.send_message(chat_id, "✅ 机器人已加入群组！每日签到通知已开启。")

async def daily_checkin_notice(context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📅 立即签到", callback_data="daily_checkin")]])
    for gid in list(group_ids):
        try:
            await context.bot.send_message(
                chat_id=gid,
                text="🌅 **新的一天开始了！**\n\n签到可获得 **10 金币 + 30 经验**\n每天仅限1次～",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except:
            pass

# ================== 完整按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_data(update.effective_user.id, update.effective_user)
    data = query.data
    await query.answer("✅ 操作成功！")

    if data == "official_web":
        await query.message.reply_text("🦜 **飞鸟牧场官网**\nhttps://www.niaocoin.xyz/", parse_mode='Markdown')
        return

    if data == "daily_checkin":
        today = str(date.today())
        if user.get("last_checkin") == today:
            await query.message.reply_text("❌ 你今天已经签到过了")
            return
        user["gold"] += 10
        user["last_checkin"] = today
        leveled = add_exp(update.effective_user.id, 30)
        await query.message.reply_text("✅ 签到成功！\n+10 金币\n+30 经验")
        if leveled:
            await query.message.reply_text("🎉 升级了！")
        save_data()
        return

    if data == "pk_menu":
        await query.edit_message_text("⚔️ **请选择PK模式**", reply_markup=pk_keyboard(), parse_mode='Markdown')
        return

    elif data == "pk_random":
        power1 = calculate_combat(user)
        power2 = random.randint(max(30, power1 - 120), power1 + 200)
        if power1 > power2:
            result = "🎉 你赢了！+150 金币"
            user["gold"] += 150
        else:
            result = "😔 你输了"
        await query.message.reply_text(f"⚔️ **随机PK**\n你的战力：**{power1}**\n对手战力：**{power2}**\n\n{result}", parse_mode='Markdown')

    elif data == "pk_target":
        await query.message.reply_text("👤 使用 `/pk @用户名` 发起挑战")

    elif data == "back_to_main":
        await send_panel(update, edit=True)
        return

    elif data == "feed_birds":
        today = str(date.today())
        if user.get("feed_count_today", 0) >= 5:
            await query.message.reply_text("❌ 今日喂养已达上限（5次）")
            return
        if user['feed'] >= 10:
            user['feed'] -= 10
            user["feed_count_today"] += 1
            exp_gain = random.randint(45, 65)
            leveled = add_exp(update.effective_user.id, exp_gain)
            await query.message.reply_text(f"🌾 喂养成功！+{exp_gain}经验（今日{user['feed_count_today']}/5）")
            if leveled:
                await query.message.reply_text("🎉 升级！战斗力翻倍！")
        else:
            await query.message.reply_text("❌ 鸟粮不足")

    elif data == "buy_bird":
        if user['birds'] >= 4:
            await query.message.reply_text("❌ 最多只能拥有4只🦜")
        elif user['gold'] >= 800:
            user['gold'] -= 800
            user['birds'] += 1
            await query.message.reply_text(f"✅ 购买成功！当前拥有 {user['birds']} 只🦜")
        else:
            await query.message.reply_text("❌ 金币不足（需要800）")

    elif data == "pick_egg":
        reward = 60 + user['birds'] * 30 + user['level'] * 10
        user['gold'] += reward
        await query.message.reply_text(f"✅ 捡蛋成功！获得 {reward} 金币")

    elif data == "rush_produce":
        user['feed'] = min(user['feed'] + 20, 300)
        await query.message.reply_text("✅ 赶产成功！")

    elif data == "clean_dung":
        add_exp(update.effective_user.id, 30)
        await query.message.reply_text("✅ 清扫成功！+30经验")

    elif data == "sell_all":
        earnings = user['birds'] * (100 + user['level'] * 25)
        user['gold'] += earnings
        await query.message.reply_text(f"✅ 出售成功！获得 {earnings} 金币")

    save_data()
    if data not in ["pk_menu", "pk_random", "pk_target", "daily_checkin"]:
        await send_panel(update, edit=True)

# ================== 命令 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user_data(update.effective_user.id, update.effective_user)
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！初始金币 **1000**")
    await send_panel(update)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("🏆 目前还没有玩家上榜")
        return
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['gold'], reverse=True)[:10]
    text = "🏆 **飞鸟牧场全球排行榜** 🏆\n\n"
    for i, (uid, d) in enumerate(sorted_users, 1):
        nickname = d.get("nickname", f"用户{uid[-4:]}")
        text += f"{i}. **{nickname}** — 💰 {d['gold']} 金币（{d.get('level',1)}级）\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def checkin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id, update.effective_user)
    today = str(date.today())
    if user.get("last_checkin") == today:
        await update.message.reply_text("❌ 你今天已经签到过了")
        return
    user["gold"] += 10
    user["last_checkin"] = today
    leveled = add_exp(update.effective_user.id, 30)
    await update.message.reply_text("✅ 签到成功！\n+10 金币\n+30 经验")
    if leveled:
        await update.message.reply_text("🎉 升级了！")
    save_data()

async def pk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id, update.effective_user)
    power1 = calculate_combat(user)
    power2 = random.randint(max(30, power1 - 120), power1 + 200)
    if power1 > power2:
        result = "🎉 你赢了！+150 金币"
        user["gold"] += 150
    else:
        result = "😔 你输了"
    await update.message.reply_text(f"⚔️ **随机PK**\n你的战力：**{power1}**\n对手战力：**{power2}**\n\n{result}", parse_mode='Markdown')
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
    app.add_handler(CommandHandler("pk", pk_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 机器人启动成功！排行榜已优先显示真实昵称")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
