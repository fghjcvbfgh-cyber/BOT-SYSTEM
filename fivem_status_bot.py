import discord
from discord.ext import commands, tasks
import aiohttp
import datetime
import asyncio
from config import *

# ══════════════════════════════════════════
#   🎮 RAVEN — بوت ستاتس FiveM
#   Coded by RAVEN
# ══════════════════════════════════════════

# ─── إعدادات FiveM ────────────────────────
FIVEM_IP         = "194.56.226.159"        # ← IP سيرفر الفايف ام (مثال: 51.89.xx.xx)
FIVEM_PORT       = "30120"          # ← البورت (الافتراضي 30120)
FIVEM_MAX        = 100              # ← أقصى عدد لاعبين
F8_CONNECT       = "connect 194.56.226.159:30120"  # ← أمر الكونكت
SERVER_IMAGE_URL = "https://www.raed.net/img?id=1552371"  # ← صورة السيرفر
STATUS_CHANNEL_ID = 1512098723679703131    # ← ID القناة اللي يرسل فيها الستاتس
STATUS_MESSAGE_ID = None            # ← يتملأ تلقائياً (لا تعدله)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

saved_message_id = None
server_start_time = None


# ─── جلب بيانات FiveM ─────────────────────
async def fetch_fivem_data():
    base = f"http://{FIVEM_IP}:{FIVEM_PORT}"
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            # جلب عدد اللاعبين
            async with session.get(f"{base}/players.json") as r:
                players = await r.json() if r.status == 200 else []

            # جلب معلومات السيرفر
            async with session.get(f"{base}/info.json") as r:
                info = await r.json() if r.status == 200 else {}

        return {
            "online"  : True,
            "players" : len(players),
            "hostname": info.get("vars", {}).get("sv_projectName", SERVER_NAME),
            "txadmin" : info.get("vars", {}).get("txAdmin-version", "Unknown"),
        }
    except Exception:
        return {"online": False, "players": 0, "hostname": SERVER_NAME, "txadmin": "Unknown"}


# ─── بناء الـ Embed ────────────────────────
def build_embed(data: dict, uptime_str: str) -> discord.Embed:
    if data["online"]:
        status_text = "🟢  Online"
        color       = 0x2ecc71
    else:
        status_text = "🔴  Offline"
        color       = 0xe74c3c

    embed = discord.Embed(
        title=f"**{data['hostname']}**\n{SERVER_NAME}",
        color=color
    )

    # ── الحقول ──
    embed.add_field(
        name="STATUS",
        value=f"```{status_text}```",
        inline=True
    )
    embed.add_field(
        name="PLAYERS",
        value=f"```{data['players']}/{FIVEM_MAX}```",
        inline=True
    )
    embed.add_field(
        name="F8 CONNECT COMMAND",
        value=f"```{F8_CONNECT}```",
        inline=False
    )
    embed.add_field(
        name="UPTIME",
        value=f"```{uptime_str}```",
        inline=False
    )

    # ── الصورة ──
    if SERVER_IMAGE_URL and "YOUR_IMAGE" not in SERVER_IMAGE_URL:
        embed.set_image(url=SERVER_IMAGE_URL)

    embed.set_thumbnail(url="https://i.imgur.com/rXrBJuP.png")  # شعار FiveM
    embed.set_footer(
        text=f"txAdmin {data['txadmin']} • Updated every minute • Coded by RAVEN"
    )

    return embed


# ─── زر الكونكت ───────────────────────────
class ConnectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔗 Connect", style=discord.ButtonStyle.success,
                       custom_id="fivem_connect_btn")
    async def connect_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**F8 Command:**\n```{F8_CONNECT}```",
            ephemeral=True
        )


# ─── حساب الـ Uptime ──────────────────────
def get_uptime() -> str:
    if server_start_time is None:
        return "N/A"
    delta   = datetime.datetime.utcnow() - server_start_time
    hours   = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours} hrs, {minutes} mins"


# ─── تاسك التحديث كل دقيقة ────────────────
@tasks.loop(minutes=1)
async def update_status():
    global saved_message_id, server_start_time

    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        return

    data     = await fetch_fivem_data()
    uptime   = get_uptime()

    # إذا السيرفر أونلاين وأول مرة → سجّل وقت البداية
    if data["online"] and server_start_time is None:
        server_start_time = datetime.datetime.utcnow()
    elif not data["online"]:
        server_start_time = None

    embed = build_embed(data, uptime)
    view  = ConnectView()

    # تعديل الرسالة الموجودة أو إرسال جديدة
    if saved_message_id:
        try:
            msg = await channel.fetch_message(saved_message_id)
            await msg.edit(embed=embed, view=view)
            return
        except discord.NotFound:
            saved_message_id = None

    # إرسال رسالة جديدة
    msg = await channel.send(embed=embed, view=view)
    saved_message_id = msg.id


# ─── أمر يدوي للأدمن ──────────────────────
@bot.command(name="fivem_status")
@commands.has_permissions(administrator=True)
async def cmd_fivem(ctx):
    """إرسال/تحديث ستاتس السيرفر يدوياً"""
    global saved_message_id
    saved_message_id = None  # أعد الإرسال من جديد
    await update_status()
    await ctx.message.delete()

@bot.command(name="fivem_set_image")
@commands.has_permissions(administrator=True)
async def cmd_set_image(ctx, url: str):
    """تغيير صورة السيرفر: !fivem_set_image [رابط الصورة]"""
    global SERVER_IMAGE_URL
    SERVER_IMAGE_URL = url
    await ctx.send(f"✅ تم تغيير الصورة!", delete_after=5)
    await ctx.message.delete()


@bot.event
async def on_ready():
    print(f"✅  [{SERVER_NAME}] FiveM Status Bot شغّال: {bot.user}")
    update_status.start()


bot.run("MTUxNDk1NDY1NDI2ODY1MzY2OQ.G9GkpT.NEQNe2Ru2gmovkkqaLw9RMQ14pdOPlgtMJkALg")   # ← توكن بوت الستاتس