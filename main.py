import discord
from discord.ext import commands
from discord import app_commands
import aiohttp, io

# ===== CONFIG =====
TOKEN = "ใส่โทเคนบอทของคุณ"
REMOVE_BG_KEY = "ใส่คีย์จาก remove.bg ของคุณ"
# ==================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_settings = {}

# ================= VIEW ปุ่มหลัก =================
class RemoveBGView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ปุ่ม: ลบพื้นหลัง
    @discord.ui.button(label="🧽 ลบพื้นหลัง", style=discord.ButtonStyle.primary)
    async def remove_bg_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🖼️ ** กรุณาส่งรูปที่ต้องการลบมาภายใน 30 วินาทีค่ะ**",
            ephemeral=True
        )

        def check(msg):
            return msg.author == interaction.user and msg.attachments

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            attachment = msg.attachments[0]
            image_bytes = await attachment.read()
            await msg.delete()

            await interaction.followup.send("⏳ ฮานะกำลังทำงานได้โปรดรอสักครู่นะคะ", ephemeral=True)

            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field("image_file", image_bytes, filename="input.png", content_type="image/png")
                form.add_field("size", "auto")

                async with session.post(
                    "https://api.remove.bg/v1.0/removebg",
                    data=form,
                    headers={"X-Api-Key": REMOVE_BG_KEY},
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        await interaction.followup.send(f"❌ ลบพื้นหลังไม่สำเร็จ: {text}", ephemeral=True)
                        return

                    result = await resp.read()
                    file = discord.File(io.BytesIO(result), filename="removed_bg.png")

                    guild_id = interaction.guild.id
                    done_text = server_settings.get(guild_id, {}).get("done_text", "🧽 ฮานะมาส่งรูปค่ะ")

                    await interaction.user.send(done_text, file=file)
                    await interaction.followup.send("📁 ลบพื้นหลังสำเร็จส่งรูปให้ใน Dm แล้วค่ะ", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"⚠️ เกิดข้อผิดพลาด: {e}", ephemeral=True)

    # ปุ่ม: แปลงรูปเป็นลิงก์
    @discord.ui.button(label="🔗 แปลงรูป", style=discord.ButtonStyle.secondary)
    async def convert_image_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔗 กรุณาส่งรูปที่ต้องการแปลงมาภายใน 30 วินาทีค่ะ", ephemeral=True)

        def check(msg):
            return msg.author == interaction.user and msg.attachments

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            attachment = msg.attachments[0]
            image_url = attachment.url
            await msg.delete()

            await interaction.followup.send(f"🔗 ลิงก์ของคุณคือ:\n```{image_url}```", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ ไม่พบรูปหรือเกิดข้อผิดพลาดค่ะ: {e}", ephemeral=True)

# ================== 7 คำสั่งหลักทั้งหมด ==================

# 1. /ตกแต่ง_embed
@bot.tree.command(name="ตกแต่ง_embed", description="สร้าง Embed สำหรับปรับแต่งก่อนส่ง")
async def decorate_embed(interaction: discord.Interaction, title: str, description: str, color: str = "#00ffaa", image: str = ""):
    gid = interaction.guild.id
    server_settings[gid] = server_settings.get(gid, {})
    server_settings[gid]["embed"] = {
        "title": title,
        "desc": description,
        "color": color,
        "image": image if image.startswith(("http://", "https://")) else ""
    }
    await interaction.response.send_message("✅ บันทึก Embed เรียบร้อยแล้วค่ะใช้ /ตัวอย่าง เพื่อดูตัวอย่างEmbedได้เลยค่ะ", ephemeral=True)

# 2. /ตัวอย่าง_embed
@bot.tree.command(name="ตัวอย่าง_embed", description="ดูตัวอย่าง Embed ที่ตกแต่งไว้")
async def preview_embed(interaction: discord.Interaction):
    gid = interaction.guild.id
    data = server_settings.get(gid, {}).get("embed")

    if not data:
        await interaction.response.send_message("❌ ยังไม่ได้ตกแต่ง Embed!", ephemeral=True)
        return

    embed = discord.Embed(title=data["title"], description=data["desc"], color=int(data["color"].replace("#", ""), 16))
    if data["image"]:
        embed.set_image(url=data["image"])

    await interaction.response.send_message(embed=embed, view=RemoveBGView(), ephemeral=True)

# 3. /ตั้งค่าช่องที่ส่ง_embed
@bot.tree.command(name="ตั้งค่าช่องที่ส่ง_embed", description="ตั้งค่าช่องที่จะส่ง Embed จริง")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = interaction.guild.id
    server_settings[gid] = server_settings.get(gid, {})
    server_settings[gid]["send_channel"] = channel.id
    await interaction.response.send_message(f"✅ ตั้งค่าช่องส่ง Embed เป็น {channel.mention}", ephemeral=True)

# 4. /ตกแต่งข้อความลบเสร็จ
@bot.tree.command(name="ตกแต่งข้อความลบเสร็จ", description="ตั้งค่าข้อความตอนลบพื้นหลังเสร็จ")
async def set_done_text(interaction: discord.Interaction, message: str):
    gid = interaction.guild.id
    server_settings[gid] = server_settings.get(gid, {})
    server_settings[gid]["done_text"] = message
    await interaction.response.send_message("✅ ตั้งค่าข้อความเสร็จเรียบร้อย!", ephemeral=True)

# 5. /ตั้งค่ายศ
@bot.tree.command(name="ตั้งค่ายศ", description="ตั้งค่ายศที่ใช้คำสั่งได้")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    gid = interaction.guild.id
    server_settings[gid] = server_settings.get(gid, {})
    server_settings[gid]["role"] = role.id
    await interaction.response.send_message(f"✅ ตั้งค่ายศที่ใช้คำสั่งได้เป็น {role.mention}", ephemeral=True)

# 6. /ส่ง_embed
@bot.tree.command(name="ส่ง_embed", description="ส่ง Embed ไปยังช่องที่ตั้งไว้")
async def send_embed(interaction: discord.Interaction):
    gid = interaction.guild.id
    settings = server_settings.get(gid, {})

    # ตรวจสอบ role
    role_id = settings.get("role")
    if role_id and role_id not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("⛔ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
        return

    data = settings.get("embed")
    if not data:
        await interaction.response.send_message("❌ ยังไม่ได้ตั้งค่า Embed!", ephemeral=True)
        return

    channel_id = settings.get("send_channel")
    if not channel_id:
        await interaction.response.send_message("❌ ยังไม่ได้ตั้งค่าช่อง!", ephemeral=True)
        return

    channel = interaction.guild.get_channel(channel_id)
    embed = discord.Embed(title=data["title"], description=data["desc"], color=int(data["color"].replace("#", ""), 16))
    if data["image"]:
        embed.set_image(url=data["image"])

    await channel.send(embed=embed, view=RemoveBGView())
    await interaction.response.send_message(f"✅ ส่ง Embed ไปที่ {channel.mention} แล้ว!", ephemeral=True)

# 7. /เช็กเครดิต_removebg
@bot.tree.command(name="เช็กเครดิต_removebg", description="ดูจำนวนเครดิต remove.bg ที่เหลือ")
async def check_credits(interaction: discord.Interaction):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.remove.bg/v1.0/account",
                headers={"X-Api-Key": REMOVE_BG_KEY},
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    await interaction.response.send_message(f"❌ ตรวจสอบเครดิตไม่สำเร็จ: {text}", ephemeral=True)
                    return
                data = await resp.json()
                credits = data.get("data", {}).get("attributes", {}).get("credits", {}).get("total", 0)
                await interaction.response.send_message(f"💎 เครดิตที่เหลือของ RemoveBG: `{credits}`", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ ตรวจสอบเครดิตล้มเหลว: {e}", ephemeral=True)

# ================== Ready ==================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ บอทพร้อมใช้งาน ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"Sync Error: {e}")

bot.run(TOKEN)