import os
import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import datetime, asyncio
from config import *

# ══════════════════════════════════════════
#   🎫 RAVEN — بوت التيكت + نظام الرتب
#   Coded by RAVEN
# ══════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── الرتب المتاحة للطلب (أضف/عدّل كما تريد) ───
REQUESTABLE_ROLES = {
    "VIP"      : 1486489133072252999,   # ← ID رول VIP
    "Member+"  : 1486489136436346970,   # ← ID رول Member+
    "Verified" : 1486489136436346970,   # ← ID رول Verified
}

# ─── قناة مراجعة طلبات الرتب ────────────
ROLE_REQUEST_CHANNEL_ID = 1514953616937455696   # ← ID القناة اللي تصلها الطلبات
ALLOWED_ROLE_ID         = 1486489125514252440   # ← ID الرول اللي يقدر يطلب رتبة (0 = الكل)

open_tickets = {}   # {user_id: channel_id}


# ══ نظام طلب الرتب ══════════════════════

class RoleRequestView(View):
    """الأزرار الرئيسية: طلب اعطاء رتبة | طلب سحب رتبة"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="طلب اعطاء رتبة", style=discord.ButtonStyle.success,
                       custom_id="give_role_btn", emoji="✅")
    async def give_role(self, interaction: discord.Interaction, button: Button):
        allowed_role = interaction.guild.get_role(ALLOWED_ROLE_ID)
        if allowed_role and allowed_role not in interaction.user.roles:
            return await interaction.response.send_message(
                f"❌ هذه الخدمة متاحة فقط لأصحاب رول **{allowed_role.name}**!",
                ephemeral=True
            )
        await interaction.response.send_modal(RoleRequestModal(action="give"))

    @discord.ui.button(label="طلب سحب رتبة", style=discord.ButtonStyle.danger,
                       custom_id="remove_role_btn", emoji="❌")
    async def remove_role(self, interaction: discord.Interaction, button: Button):
        allowed_role = interaction.guild.get_role(ALLOWED_ROLE_ID)
        if allowed_role and allowed_role not in interaction.user.roles:
            return await interaction.response.send_message(
                f"❌ هذه الخدمة متاحة فقط لأصحاب رول **{allowed_role.name}**!",
                ephemeral=True
            )
        await interaction.response.send_modal(RoleRequestModal(action="remove"))


class RoleRequestModal(Modal):
    def __init__(self, action: str):
        super().__init__(title="طلب اعطاء رتبة" if action == "give" else "طلب سحب رتبة")
        self.action = action

        self.role_name = TextInput(
            label="اسم الرتبة المطلوبة | Role Name",
            placeholder="مثال: VIP / Member+",
            required=True, max_length=50
        )
        self.reason = TextInput(
            label="السبب | Reason",
            placeholder="اكتب سببك هنا...",
            style=discord.TextStyle.paragraph,
            required=True, max_length=500
        )
        self.add_item(self.role_name)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(ROLE_REQUEST_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(
                "❌ قناة الطلبات غير موجودة!", ephemeral=True
            )

        color  = 0x2ecc71 if self.action == "give" else 0xe74c3c
        action_ar = "اعطاء رتبة ✅" if self.action == "give" else "سحب رتبة ❌"

        embed = discord.Embed(
            title=f"🎭  طلب {action_ar}",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="العضو | Member",   value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="الرتبة | Role",    value=self.role_name.value, inline=True)
        embed.add_field(name="النوع | Type",     value=action_ar, inline=True)
        embed.add_field(name="السبب | Reason",   value=self.reason.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=CODED_BY)

        await channel.send(
            embed=embed,
            view=AdminRoleDecisionView(
                user_id=interaction.user.id,
                role_name=self.role_name.value,
                action=self.action
            )
        )

        await interaction.response.send_message(
            f"✅ تم إرسال طلبك بنجاح!\n"
            f"*Your request has been sent successfully!*\n\n"
            f"الرتبة: **{self.role_name.value}**\nانتظر رد الإدارة ⏳",
            ephemeral=True
        )


class AdminRoleDecisionView(View):
    """أزرار القبول/الرفض للأدمن"""
    def __init__(self, user_id: int, role_name: str, action: str):
        super().__init__(timeout=None)
        self.user_id   = user_id
        self.role_name = role_name
        self.action    = action

    @discord.ui.button(label="✅ قبول | Accept", style=discord.ButtonStyle.success,
                       custom_id="admin_accept_role")
    async def accept(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ ليس لديك صلاحية!", ephemeral=True)

        member = interaction.guild.get_member(self.user_id)
        if not member:
            return await interaction.response.send_message("❌ العضو غادر السيرفر!", ephemeral=True)

        # البحث عن الرول بالاسم أو الـ ID من القاموس
        role = None
        for name, rid in REQUESTABLE_ROLES.items():
            if name.lower() == self.role_name.lower():
                role = interaction.guild.get_role(rid)
                break
        if not role:
            role = discord.utils.get(interaction.guild.roles, name=self.role_name)

        if role:
            if self.action == "give":
                await member.add_roles(role)
            else:
                await member.remove_roles(role)

        action_done = "اعطيت" if self.action == "give" else "سُحبت منه"
        await interaction.response.send_message(
            f"✅ تم! تم {action_done} الرتبة **{self.role_name}** للعضو {member.mention}",
            ephemeral=True
        )

        # إشعار العضو
        try:
            dm_embed = discord.Embed(
                title=f"🎭  طلب الرتبة — {'مقبول ✅' if self.action == 'give' else 'مقبول ✅'}",
                description=(
                    f"طلبك للرتبة **{self.role_name}** تم **قبوله** من الإدارة! 🎉\n"
                    f"*Your role request for **{self.role_name}** was **accepted**!*"
                ),
                color=0x2ecc71
            )
            dm_embed.set_footer(text=CODED_BY)
            await member.send(embed=dm_embed)
        except:
            pass

        # تعطيل الأزرار
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="❌ رفض | Reject", style=discord.ButtonStyle.danger,
                       custom_id="admin_reject_role")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ ليس لديك صلاحية!", ephemeral=True)

        member = interaction.guild.get_member(self.user_id)

        try:
            dm_embed = discord.Embed(
                title="🎭  طلب الرتبة — مرفوض ❌",
                description=(
                    f"طلبك للرتبة **{self.role_name}** تم **رفضه** من الإدارة.\n"
                    f"*Your role request for **{self.role_name}** was **rejected**.*"
                ),
                color=0xe74c3c
            )
            dm_embed.set_footer(text=CODED_BY)
            if member:
                await member.send(embed=dm_embed)
        except:
            pass

        await interaction.response.send_message("❌ تم رفض الطلب.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)


# ══ نظام التيكت ══════════════════════════

class TicketMainView(View):
    """الزر الرئيسي لفتح تيكت"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫  افتح تيكت | Open Ticket", style=discord.ButtonStyle.primary,
                       custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild  = interaction.guild
        member = interaction.user

        if member.id in open_tickets:
            ch = guild.get_channel(open_tickets[member.id])
            if ch:
                return await interaction.response.send_message(
                    f"❌ لديك تيكت مفتوح بالفعل! | You already have an open ticket: {ch.mention}",
                    ephemeral=True
                )

        # إنشاء قناة التيكت
        support_role = guild.get_role(SUPPORT_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member:             discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        category = discord.utils.get(guild.categories, name="🎫 Tickets")
        channel  = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            overwrites=overwrites,
            category=category,
            topic=f"Ticket by {member} ({member.id})"
        )

        open_tickets[member.id] = channel.id

        embed = discord.Embed(
            title=f"🎫  تيكت جديد | New Ticket",
            description=(
                f"أهلاً {member.mention}!\n"
                f"شرح مشكلتك وسيتم الرد عليك قريباً.\n\n"
                f"*Hello {member.mention}! Describe your issue and support will assist you shortly.*"
            ),
            color=0x1a1a2e,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=CODED_BY)
        await channel.send(
            content=f"{member.mention} {support_role.mention if support_role else ''}",
            embed=embed,
            view=TicketControlView(member.id)
        )

        await interaction.response.send_message(
            f"✅ تم فتح تيكتك: {channel.mention}\n*Your ticket has been opened: {channel.mention}*",
            ephemeral=True
        )


class TicketControlView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="🔒  إغلاق | Close", style=discord.ButtonStyle.danger,
                       custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if (interaction.user.id != self.owner_id and
                not interaction.user.guild_permissions.manage_channels):
            return await interaction.response.send_message("❌ ليس لديك صلاحية!", ephemeral=True)

        await interaction.response.send_message("🔒 سيتم إغلاق التيكت خلال 5 ثواني... | Closing in 5s...")
        await asyncio.sleep(5)

        # إزالة من القاموس
        open_tickets.pop(self.owner_id, None)

        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            embed = discord.Embed(
                title="🎫  تيكت مغلق | Ticket Closed",
                description=f"القناة: {interaction.channel.name}\nالمغلق: {interaction.user}",
                color=0xe74c3c,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text=CODED_BY)
            await log_ch.send(embed=embed)

        await interaction.channel.delete()


# ══ أوامر الأدمن ══════════════════════════

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def cmd_setup_roles(ctx):
    """إرسال رسالة طلب الرتب"""
    embed = discord.Embed(
        title=f"🎭  {SERVER_NAME} — نظام الرتب | Role System",
        description=(
            "اضغط على الزر المناسب لطلب رتبة أو سحبها.\n"
            "*Press the appropriate button to request or remove a role.*"
        ),
        color=0x1a1a2e,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text=CODED_BY)
    await ctx.send(embed=embed, view=RoleRequestView())
    await ctx.message.delete()


@bot.command(name="setup_ticket")
@commands.has_permissions(administrator=True)
async def cmd_setup_ticket(ctx):
    """إرسال رسالة فتح التيكت"""
    embed = discord.Embed(
        title=f"🎫  {SERVER_NAME} — الدعم الفني | Support",
        description=(
            "لفتح تيكت اضغط على الزر أدناه.\n"
            "*Click the button below to open a support ticket.*"
        ),
        color=0x1a1a2e,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text=CODED_BY)
    await ctx.send(embed=embed, view=TicketMainView())
    await ctx.message.delete()


@bot.event
async def on_ready():
    print(f"✅  [{SERVER_NAME}] Ticket & Roles Bot شغّال: {bot.user}")
    bot.add_view(RoleRequestView())
    bot.add_view(TicketMainView())

bot.run(TICKET_TOKEN)
