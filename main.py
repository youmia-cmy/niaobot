import logging
import os
import json
import random
import base64
from datetime import date, time

# ====================== Telegram 导入 ======================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ChatMemberHandler, MessageHandler, filters
)

# ====================== Gemini AI ======================
try:
    import google.generativeai as genai
except ImportError:
    genai = None
    print("⚠️ 请确保已安装 google-generativeai")

# ====================== Key 配置 =======================
def get_gemini_key():
    encoded = "Z2VuLWxhbmctY2xpZW50LTAxNjAyOTM4ODg="
    return base64.b64decode(encoded).decode('utf-8')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or get_gemini_key()

if GEMINI_API_KEY and genai:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
else:
    model = None
    logging.warning("⚠️ Gemini AI 未启用")

# ====================== 机器人配置 ======================
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
            "feed": 50, "birds": 1, "nests": 4,
            "level": 1, "exp": 0, "last_active": 0,
            "combat": 100, "stamina": 0, "strength": 0,
            "intelligence": 0, "agility": 0,
            "feed_count_today": 0,
            "pick_egg_today": 0,
            "rush_today": 0,
            "clean_today": 0,
            "chat_exp_today": 0,
            "last_date": today,
            "last_checkin": "",
            "nickname": ""
        }
    if user_data[uid].get("last_date") != today:
        user_data[uid]["feed_count_today"] = 0
        user_data[uid]["pick_egg_today"] = 0
        user_data[uid]["rush_today"] = 0
        user_data[uid]["clean_today"] = 0
        user_data[uid]["chat_exp_today"] = 0
        user_data[uid]["last_date"] = today
    if effective_user:
        name = effective_user.full_name or effective_user.first_name or f"用户{uid[-4:]}"
        user_data[uid]["nickname"] = name
    return user_data[uid]

def add_exp(user_id: int, amount: int):
    user = get_user_data(user_id)
    user["exp"] += amount
    old_level = user["level"]
    LEVELS = [0]
    for i in range(1, 100):
        exp_needed = int(100 * (i ** 1.6))
        LEVELS.append(exp_needed)
    
    while user["level"] < 99 and user["exp"] >= LEVELS[user["level"]]:
        user["level"] += 1
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
        [InlineKeyboardButton("⚔️ PK", callback_data="pk_menu"), InlineKeyboardButton("💬 NIAO~AI🦜", callback_data="ai_chat")],
        [InlineKeyboardButton("🦜 官网", callback_data="official_web")],
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
        f"🌾 鸟粮：{user['feed']}\n"
        f"🦜 鹦鹉：{user['birds']} 只  |  ⚔️ 战斗力：{combat}\n"
        f"⭐ 经验：{user['exp']}"
    )
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"面板错误: {e}")

# ================== 群组跟踪 & 每日签到 ==================
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
                text="🌅 **新的一天开始了！**\n\n签到可获得 **50 经验**\n每天仅限1次～",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except:
            pass

# ================== 群聊经验 ==================
async def group_chat_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    user = get_user_data(update.effective_user.id)
    if user.get("chat_exp_today", 0) >= 30:
        return
    exp_gain = random.randint(1, 3)
    user["chat_exp_today"] = user.get("chat_exp_today", 0) + exp_gain
    leveled = add_exp(update.effective_user.id, exp_gain)
    if leveled:
        try:
            await update.message.reply_text(f"🎉 聊天获得经验！升级到 {user['level']} 级！", quote=True)
        except:
            pass
    save_data()

# ================== NIAO AI ==================
async def ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not model:
        await update.message.reply_text("❌ NIAO 暂未启用")
        return
    user_input = update.message.text.strip()
    if not user_input:
        return
    await update.message.chat.send_action("typing")
    try:
        prompt = f"""你叫 NIAO，是飞鸟牧场可爱幽默的专属AI助手。
只回复纯文字。
用活泼语气，经常自称“NIAO”。
用户说：{user_input}"""
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text.strip()[:4000])
    except Exception as e:
        logger.error(f"Gemini 错误: {e}")
        await update.message.reply_text("❌ NIAO 走神了～")

async def ai_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "💬 **NIAO 聊天已开启**\n\n直接发消息🦜我就行～\n输入 /back 返回牧场",
        parse_mode='Markdown'
    )

# ================== 按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_data(update.effective_user.id, update.effective_user)
    data = query.data
    await query.answer("✅ 操作成功！")

    reply = None

    if data == "ai_chat":
        await ai_button(update, context)
        return
    elif data == "pick_egg":
        if user.get("pick_egg_today", 0) >= 10:
            reply = await query.message.reply_text("❌ 今日捡蛋已达上限（10次）")
        else:
            user["pick_egg_today"] = user.get("pick_egg_today", 0) + 1
            reward = 60 + user['birds'] * 30 + user['level'] * 10
            leveled = add_exp(update.effective_user.id, reward)
            reply = await query.message.reply_text(f"✅ 捡蛋成功！+{reward}经验（今日{user['pick_egg_today']}/10）")
            if leveled:
                await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级")
    elif data == "rush_produce":
        if user.get("rush_today", 0) >= 10:
            reply = await query.message.reply_text("❌ 今日赶产已达上限（10次）")
        else:
            user["rush_today"] = user.get("rush_today", 0) + 1
            user['feed'] = min(user['feed'] + 20, 300)
            reply = await query.message.reply_text(f"✅ 赶产成功！+20鸟粮（今日{user['rush_today']}/10）")
    elif data == "feed_birds":
        if user.get("feed_count_today", 0) >= 15:
            reply = await query.message.reply_text("❌ 今日喂养已达上限（15次）")
        elif user['feed'] >= 10:
            user['feed'] -= 10
            user["feed_count_today"] += 1
            exp_gain = random.randint(45, 65)
            leveled = add_exp(update.effective_user.id, exp_gain)
            reply = await query.message.reply_text(f"🌾 喂养成功！+{exp_gain}经验（今日{user['feed_count_today']}/15）")
            if leveled:
                await query.message.reply_text(f"🎉 升级！当前 {user['level']} 级")
        else:
            reply = await query.message.reply_text("❌ 鸟粮不足")
    elif data == "clean_dung":
        if user.get("clean_today", 0) >= 15:
            reply = await query.message.reply_text("❌ 今日清扫已达上限（15次）")
        else:
            user["clean_today"] = user.get("clean_today", 0) + 1
            leveled = add_exp(update.effective_user.id, 30)
            reply = await query.message.reply_text(f"✅ 清扫成功！+30经验（今日{user['clean_today']}/15）")
            if leveled:
                await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级")
    elif data == "official_web":
        reply = await query.message.reply_text("🦜 **NIAO官网**\nhttps://www.niaocoin.xyz/", parse_mode='Markdown')
    elif data == "daily_checkin":
        today_str = str(date.today())
        if user.get("last_checkin") == today_str:
            reply = await query.message.reply_text("❌ 你今天已经签到过了")
        else:
            user["last_checkin"] = today_str
            leveled = add_exp(update.effective_user.id, 50)
            reply = await query.message.reply_text("✅ 签到成功！\n+50 经验")
            if leveled:
                await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级")
    elif data == "pk_menu":
        await query.edit_message_text("⚔️ **请选择PK模式**", reply_markup=pk_keyboard(), parse_mode='Markdown')
        return
    elif data == "pk_random":
        power1 = calculate_combat(user)
        power2 = random.randint(max(30, power1 - 120), power1 + 200)
        if power1 > power2:
            result = "🎉 你赢了！+80 经验"
            add_exp(update.effective_user.id, 80)
        else:
            result = "😔 你输了"
        reply = await query.message.reply_text(f"⚔️ **随机PK**\n你的战力：**{power1}**\n对手战力：**{power2}**\n\n{result}", parse_mode='Markdown')
    elif data == "back_to_main":
        await send_panel(update, edit=True)
        return

    if reply:
        context.job_queue.run_once(delete_later, 2, data={'chat_id': reply.chat_id, 'message_id': reply.message_id})

    save_data()
    if data not in ["pk_menu", "pk_random", "pk_target", "daily_checkin", "ai_chat"]:
        await send_panel(update, edit=True)

async def delete_later(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(context.job.data['chat_id'], context.job.data['message_id'])
    except:
        pass

# ================== 命令 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user_data(update.effective_user.id, update.effective_user)
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！\n我是 **NIAO**，支持聊天喔～")
    await send_panel(update)

async def back_to_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("🏆 目前还没有玩家上榜")
        return
    sorted_users = sorted(user_data.items(), key=lambda x: calculate_combat(x[1]), reverse=True)[:10]
    text = "🏆 **飞鸟牧场战斗力排行榜** 🏆\n\n"
    for i, (uid, d) in enumerate(sorted_users, 1):
        nickname = d.get("nickname", f"用户{uid[-4:]}")
        combat = calculate_combat(d)
        text += f"{i}. **{nickname}** — ⚔️ {combat} 战斗力（{d.get('level',1)}级）\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def checkin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id, update.effective_user)
    today = str(date.today())
    if user.get("last_checkin") == today:
        await update.message.reply_text("❌ 你今天已经签到过了")
        return
    user["last_checkin"] = today
    leveled = add_exp(update.effective_user.id, 50)
    await update.message.reply_text("✅ 签到成功！\n+50 经验")
    if leveled:
        await update.message.reply_text(f"🎉 升级了！当前 {user['level']} 级")
    save_data()

async def pk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id, update.effective_user)
    power1 = calculate_combat(user)
    power2 = random.randint(max(30, power1 - 120), power1 + 200)
    if power1 > power2:
        result = "🎉 你赢了！+80 经验"
        add_exp(update.effective_user.id, 80)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group_chat_exp))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", send_panel))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", checkin_cmd))
    app.add_handler(CommandHandler("pk", pk_command))
    app.add_handler(CommandHandler("ai", ai_response))
    app.add_handler(CommandHandler("back", back_to_farm))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, ai_response))

    logger.info("🚀 飞鸟牧场 + NIAO (gemini-3-flash-preview) 启动成功！")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
