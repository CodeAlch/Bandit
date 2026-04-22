import discord
import sqlite3
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

AUDIT_CHANNELS = [
    "role-delete", "role-create", "role-update", "member-ban",
    "member-unban", "member-join", "member-leave", "message-delete",
    "message-edit", "nickname-ch", "member-role", "log-invites",
    "default-logs", "carl-bot-logs", "moderator-c", "image-delete"
]

intents = discord.Intents.all()
client = discord.Client(intents=intents)

def init_db():
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        guild_id TEXT,
        channel_name TEXT,
        author_name TEXT,
        author_id TEXT,
        content TEXT,
        timestamp TEXT
    )""")
    conn.commit()
    conn.close()

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    init_db()
    
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    total = 0

    for guild in client.guilds:
        print(f"\n📌 Server: {guild.name}")
        for channel in guild.text_channels:
            # Audit channels skip karo
            if channel.name in AUDIT_CHANNELS:
                print(f"   ⏭️ Skipping audit: #{channel.name}")
                continue
            try:
                count = 0
                async for message in channel.history(limit=None):  # limit=None = saari history
                    if message.author.bot:
                        continue
                    if not message.content.strip():
                        continue
                    try:
                        c.execute("""INSERT OR IGNORE INTO messages
                            (message_id, guild_id, channel_name, author_name, author_id, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (str(message.id), str(guild.id), channel.name,
                             message.author.name, str(message.author.id),
                             message.content,
                             message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
                        count += 1
                    except:
                        pass
                conn.commit()
                total += count
                print(f"   ✅ #{channel.name} — {count} messages saved")
            except Exception as e:
                print(f"   ❌ #{channel.name} — Error: {e}")

    conn.close()
    print(f"\n🎉 Done! Total {total} messages saved to messages.db")
    await client.close()

client.run(TOKEN)
EOF