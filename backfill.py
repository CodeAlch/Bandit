import discord
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()

    for guild in client.guilds:
        print(f"\n📌 Server: {guild.name}")
        for channel in guild.text_channels:
            try:
                count = 0
                async for msg in channel.history(limit=None, oldest_first=True):
                    if msg.author.bot:
                        continue
                    c.execute("""
                        INSERT OR IGNORE INTO messages 
                        (channel_name, author_name, content, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (
                        channel.name,
                        msg.author.display_name,
                        msg.content,
                        str(msg.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                    ))
                    count += 1
                conn.commit()
                print(f"  ✅ #{channel.name}: {count} messages imported")
            except discord.Forbidden:
                print(f"  ❌ #{channel.name}: No access")

    conn.close()
    print("\n🎉 Backfill complete!")
    await client.close()

client.run(TOKEN)
