import os
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import UserAlreadyParticipantError, SessionPasswordNeededError

# ================= الإعدادات =================
API_ID = 27726724  # يمكن تغييره إلى 20291893 من الكود الثاني إن أردت
API_HASH = 'ab0903d0498532e59b093d2f4abe310d'
BOT_TOKEN = "7684897790:AAG-iyfMteQfb0zgEahhuSyLOjdSii6_GMY"
SESSIONS_FOLDER = "sessions"
DEFAULT_DELAY = 5
DELAY_BETWEEN_VOTES = 3

# التأكد من وجود مجلد الجلسات
if not os.path.exists(SESSIONS_FOLDER):
    os.makedirs(SESSIONS_FOLDER)

# ================= المتغيرات المؤقتة =================
user_data = {}
active_roulettes = {}
temp_clients = {}  # لتخزين جلسات تسجيل الدخول المؤقتة

bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ================= القوائم =================
def main_menu():
    return [
        [Button.inline("➕ إضافة روليت جديد", data="new_draw"), Button.inline("📋 عرض الروليـتات", data="show_draws")],
        [Button.inline("➕ إضافة حساب", data="add_account"), Button.inline("📋 عرض الحسابات", data="list_accounts")],
        [Button.inline("❌ حذف حساب", data="delete_account")]
    ]

# ================= دوال إدارة الحسابات =================
def get_registered_accounts():
    return [f.replace('.session', '') for f in os.listdir(SESSIONS_FOLDER) if f.endswith('.session') and f != 'bot_session.session']

def delete_account_file(phone):
    path = os.path.join(SESSIONS_FOLDER, f"{phone}.session")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

# ================= دوال المشاركة والروليت =================
async def join_channel(client, channel):
    if channel:
        try:
            await client(JoinChannelRequest(channel))
            await asyncio.sleep(2)
        except UserAlreadyParticipantError:
            pass
        except Exception as e:
            print(f"⚠️ فشل الاشتراك في {channel}: {e}")

async def participate(client, channel, msg_id, cond1, cond2):
    try:
        await join_channel(client, channel)
        await join_channel(client, cond1)
        await join_channel(client, cond2)
        message = await client.get_messages(channel, ids=msg_id)
        if message and message.buttons:
            for row in message.buttons:
                for button in row:
                    if "مشاركة" in button.text:
                        await button.click()
                        await asyncio.sleep(DELAY_BETWEEN_VOTES)
                        return True
    except Exception as e:
        print(f"❌ خطأ أثناء المشاركة: {e}")
    return False

async def process_sessions(user_id, draw_id, draw_data):
    accounts = get_registered_accounts()
    if not accounts:
        return await bot.send_message(user_id, "⚠️ لا توجد حسابات (جلسات) متاحة! قم بإضافة حسابات أولاً.")
    
    active_roulettes[draw_id] = True
    success, fail = 0, 0
    delay = draw_data.get("delay", DEFAULT_DELAY)
    
    for phone in accounts:
        if not active_roulettes.get(draw_id, False):
            await bot.send_message(user_id, f"⏹️ تم إيقاف الروليت {draw_id}!")
            return
        
        session_path = os.path.join(SESSIONS_FOLDER, f"{phone}.session")
        try:
            async with TelegramClient(session_path, API_ID, API_HASH) as client:
                result = await participate(client, draw_data["channel"], draw_data["message_id"],
                                           draw_data.get("cond1"), draw_data.get("cond2"))
                if result:
                    success += 1
                    await bot.send_message(user_id, f"✅ الحساب [{phone}] شارك بنجاح!")
                else:
                    fail += 1
                    await bot.send_message(user_id, f"❌ الحساب [{phone}] فشل في العثور على زر المشاركة أو تنفيذه!")
                await asyncio.sleep(delay)
        except Exception as e:
            fail += 1
            print(f"❌ فشل في معالجة {phone}: {e}")
            await bot.send_message(user_id, f"❌ الحساب [{phone}] واجه خطأ: {e}")
            
    await bot.send_message(user_id, f"✅ تقرير الروليت {draw_id}:\n✔️ ناجحة: {success}\n❌ فاشلة: {fail}")

# ================= معالجة تفاعلات البوت =================
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_id = event.sender_id
    if user_id not in user_data:
        user_data[user_id] = {"draws": {}, "temp": {}}
    await event.respond("👋 مرحبًا بك في بوت الروليت وإدارة الحسابات.\nاختر خيارًا:", buttons=main_menu())

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data.decode("utf-8")
    
    if user_id not in user_data:
        user_data[user_id] = {"draws": {}, "temp": {}}

    # --- إدارة الروليت ---
    if data == "new_draw":
        user_data[user_id]["temp"] = {"state": "awaiting_link"}
        await event.edit("📝 الرجاء إرسال رابط الروليت (يجب أن يحتوي على https://t.me/.../123)")
    
    elif data == "show_draws":
        if not user_data[user_id]["draws"]:
            await event.edit("لا توجد روليـتات محفوظة.", buttons=[Button.inline("🔙 رجوع", data="back_main")])
        else:
            msg = "📋 روليـتاتك:\n"
            buttons = []
            for d_id, draw in user_data[user_id]["draws"].items():
                msg += f"روليت {d_id}: {draw.get('channel')}/{draw.get('message_id')}\n"
                buttons.append([Button.inline(f"🚀 بدء {d_id}", data=f"start_{d_id}"),
                                Button.inline(f"⏹️ إيقاف {d_id}", data=f"stop_{d_id}")])
            buttons.append([Button.inline("🔙 رجوع", data="back_main")])
            await event.edit(msg, buttons=buttons)

    elif data.startswith("start_"):
        draw_id = int(data.split("_")[-1])
        draw = user_data[user_id]["draws"].get(draw_id)
        if not draw:
            return await event.answer("❌ لا يوجد روليت بهذا المعرف!", alert=True)
        await event.edit(f"🔄 جاري بدء الروليت رقم {draw_id}...")
        asyncio.create_task(process_sessions(user_id, draw_id, draw))

    elif data.startswith("stop_"):
        draw_id = int(data.split("_")[-1])
        active_roulettes[draw_id] = False
        await event.edit(f"⏹️ تم إيقاف الروليت رقم {draw_id}!")

    # --- إدارة التأخير والشروط ---
    elif data == "skip_cond1":
        user_data[user_id]["temp"]["cond1"] = None
        user_data[user_id]["temp"]["state"] = "awaiting_cond2"
        await event.edit("✅ تم تخطي القناة الأولى.\nأرسل معرف القناة الثانية أو تخطى.", buttons=[Button.inline("تخطي", data="skip_cond2")])
        
    elif data == "skip_cond2":
        user_data[user_id]["temp"]["cond2"] = None
        user_data[user_id]["temp"]["state"] = "awaiting_delay_choice"
        await event.edit("✅ تم تخطي القناة الثانية.\nاختر وقت التأخير:", buttons=[
            [Button.inline("5s", data="set_delay_5"), Button.inline("10s", data="set_delay_10")],
            [Button.inline("15s", data="set_delay_15"), Button.inline("أدخل رقم", data="delay_custom")]
        ])

    elif data.startswith("set_delay_"):
        delay_value = int(data.split("_")[-1])
        user_data[user_id]["temp"]["delay"] = delay_value
        user_data[user_id]["temp"]["state"] = "ready"
        new_id = len(user_data[user_id]["draws"]) + 1
        user_data[user_id]["draws"][new_id] = user_data[user_id]["temp"]
        active_roulettes[new_id] = True
        await event.edit(f"✅ تم الحفظ. التأخير: {delay_value}ث.\nاضغط بدء للإطلاق.", buttons=[
            [Button.inline("🚀 بدء", data=f"start_{new_id}"), Button.inline("⏹️ إيقاف", data=f"stop_{new_id}")],
            [Button.inline("🔙 رجوع", data="back_main")]
        ])

    elif data == "delay_custom":
        user_data[user_id]["temp"]["state"] = "awaiting_custom_delay"
        await event.edit("📝 أرسل رقم التأخير (بالثواني):")

    # --- إدارة الحسابات ---
    elif data == "add_account":
        user_data[user_id]["temp"] = {"state": "awaiting_phone"}
        await event.edit("📩 أرسل رقم الهاتف مع الرمز الدولي (مثال: +9677... أو +201...):")
        
    elif data == "list_accounts":
        accs = get_registered_accounts()
        if not accs:
            await event.edit("⚠️ لا توجد حسابات مسجلة.", buttons=[Button.inline("🔙 رجوع", data="back_main")])
        else:
            msg = "📋 الحسابات المسجلة:\n\n" + "\n".join([f"👤 {acc}" for acc in accs])
            await event.edit(msg, buttons=[Button.inline("🔙 رجوع", data="back_main")])
            
    elif data == "delete_account":
        accs = get_registered_accounts()
        if not accs:
            await event.edit("⚠️ لا توجد حسابات للحذف.", buttons=[Button.inline("🔙 رجوع", data="back_main")])
        else:
            buttons = [[Button.inline(f"❌ {acc}", data=f"del_{acc}")] for acc in accs]
            buttons.append([Button.inline("🔙 رجوع", data="back_main")])
            await event.edit("اختر الحساب الذي تريد حذفه:", buttons=buttons)

    elif data.startswith("del_"):
        phone_to_delete = data.replace("del_", "")
        if delete_account_file(phone_to_delete):
            await event.edit(f"✅ تم حذف الحساب {phone_to_delete} بنجاح.", buttons=[Button.inline("🔙 رجوع", data="back_main")])
        else:
            await event.edit("❌ فشل في العثور على الحساب.", buttons=[Button.inline("🔙 رجوع", data="back_main")])

    elif data == "back_main":
        user_data[user_id]["temp"] = {}
        await event.edit("الرجاء اختيار خيار من القائمة:", buttons=main_menu())

@bot.on(events.NewMessage)
async def message_handler(event):
    if event.text.startswith('/'): return
    user_id = event.sender_id
    text = event.text.strip()
    
    if user_id in user_data and "temp" in user_data[user_id]:
        state = user_data[user_id]["temp"].get("state")
        
        # --- إضافة روليت ---
        if state == "awaiting_link":
            try:
                parts = text.split('/')
                user_data[user_id]["temp"]["channel"] = parts[-2]
                user_data[user_id]["temp"]["message_id"] = int(parts[-1].split('?')[0])
                user_data[user_id]["temp"]["state"] = "awaiting_cond1"
                await event.respond("✅ تم حفظ رابط الروليت.\nأرسل معرف قناة الشرط الأولى أو تخطى.", buttons=[Button.inline("تخطي", data="skip_cond1")])
            except Exception:
                await event.respond("❌ تأكد من إدخال رابط صحيح (يحتوي على المعرف ورقم الرسالة)!")
                
        elif state == "awaiting_cond1":
            user_data[user_id]["temp"]["cond1"] = None if text.lower() == "تخطي" else text
            user_data[user_id]["temp"]["state"] = "awaiting_cond2"
            await event.respond("✅ تم الحفظ.\nأرسل معرف قناة الشرط الثانية أو تخطى.", buttons=[Button.inline("تخطي", data="skip_cond2")])
            
        elif state == "awaiting_cond2":
            user_data[user_id]["temp"]["cond2"] = None if text.lower() == "تخطي" else text
            user_data[user_id]["temp"]["state"] = "awaiting_delay_choice"
            await event.respond("✅ تم الحفظ.\nاختر وقت التأخير:", buttons=[
                [Button.inline("5s", data="set_delay_5"), Button.inline("10s", data="set_delay_10")],
                [Button.inline("15s", data="set_delay_15"), Button.inline("أدخل رقم", data="delay_custom")]
            ])
            
        elif state == "awaiting_custom_delay":
            if text.isdigit():
                delay = int(text)
                user_data[user_id]["temp"]["delay"] = delay
                user_data[user_id]["temp"]["state"] = "ready"
                new_id = len(user_data[user_id]["draws"]) + 1
                user_data[user_id]["draws"][new_id] = user_data[user_id]["temp"]
                active_roulettes[new_id] = True
                await event.respond(f"✅ تم تعيين التأخير لـ {delay}ث.\nجاهز للبدء.", buttons=[
                    [Button.inline("🚀 بدء", data=f"start_{new_id}"), Button.inline("⏹️ إيقاف", data=f"stop_{new_id}")],
                    [Button.inline("🔙 رجوع", data="back_main")]
                ])
            else:
                await event.respond("❌ يرجى إدخال رقم صحيح!")

        # --- تسجيل الدخول لحساب جديد ---
        elif state == "awaiting_phone":
            phone = text
            if phone in get_registered_accounts():
                await event.respond("⚠️ هذا الحساب مسجل بالفعل!", buttons=[Button.inline("🔙 القائمة الرئيسية", data="back_main")])
                return
            
            client = TelegramClient(os.path.join(SESSIONS_FOLDER, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            try:
                if not await client.is_user_authorized():
                    await client.send_code_request(phone)
                    temp_clients[user_id] = {"client": client, "phone": phone}
                    user_data[user_id]["temp"]["state"] = "awaiting_code"
                    await event.respond(f"📩 تم إرسال الكود إلى {phone}.\nأرسل الكود هنا:")
                else:
                    await event.respond("✅ الحساب مسجل مسبقاً وصالح.", buttons=[Button.inline("🔙 رجوع", data="back_main")])
                    await client.disconnect()
            except Exception as e:
                await event.respond(f"❌ فشل إرسال الكود: {e}")
                await client.disconnect()
                
        elif state == "awaiting_code":
            code = text
            client_dict = temp_clients.get(user_id)
            if not client_dict:
                return await event.respond("❌ حدث خطأ، يرجى المحاولة من جديد.")
                
            client = client_dict["client"]
            phone = client_dict["phone"]
            try:
                await client.sign_in(phone, code)
                await event.respond("✅ تم تسجيل الدخول وحفظ الحساب بنجاح!", buttons=[Button.inline("🔙 القائمة الرئيسية", data="back_main")])
            except SessionPasswordNeededError:
                # إذا كان الحساب محمي بالتحقق بخطوتين
                user_data[user_id]["temp"]["state"] = "awaiting_password"
                await event.respond("🔒 الحساب محمي بكلمة مرور. يرجى إرسال كلمة المرور (التحقق بخطوتين):")
                return # تجنب إغلاق الاتصال الآن
            except Exception as e:
                await event.respond(f"❌ كود غير صحيح أو حدث خطأ: {e}")
                
            await client.disconnect()
            temp_clients.pop(user_id, None)
            user_data[user_id]["temp"] = {}
            
        elif state == "awaiting_password":
            password = text
            client_dict = temp_clients.get(user_id)
            client = client_dict["client"]
            try:
                await client.sign_in(password=password)
                await event.respond("✅ تم تسجيل الدخول وحفظ الحساب بنجاح!", buttons=[Button.inline("🔙 القائمة الرئيسية", data="back_main")])
            except Exception as e:
                await event.respond(f"❌ كلمة المرور غير صحيحة: {e}")
                
            await client.disconnect()
            temp_clients.pop(user_id, None)
            user_data[user_id]["temp"] = {}

print("✅ البوت يعمل بنظام إدارة الحسابات المدمج والروليت المتعدد!")
bot.run_until_disconnected()
