#!/usr/bin/env python3
"""
Discord Automation Bot v6 — Conversational + Smart
"""

from turtle import pos

from operator import pos

import discord
from discord.ext import commands
import os
import sys
import asyncio
import re
import json
import traceback
from dotenv import load_dotenv
from channel_manager import ChannelManager
from command_parser import CommandParser
from voice_listener import VoiceListener
from brain import BotBrain

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ DISCORD_TOKEN not found!")
    sys.exit(1)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

channel_manager = None
command_parser = None
voice_listener = None
brain = None

DEFAULT_ROLE_MAP = {
    'gaming': ['Gamer'], 'minecraft': ['Gamer', 'Minecraft Player'],
    'valorant': ['Gamer', 'Valorant Player'],
    'music': ['Music Lover'], 'dj': ['Music Lover', 'DJ'],
    'coding': ['Developer'], 'programming': ['Developer'],
    'dev': ['Developer'], 'python': ['Developer', 'Python Dev'],
    'javascript': ['Developer', 'JS Dev'], 'web': ['Developer', 'Web Dev'],
    'tech': ['Tech Enthusiast'], 'ai': ['Developer', 'AI Enthusiast'],
    'art': ['Artist'], 'design': ['Artist', 'Designer'],
    'general': ['@everyone'], 'announcements': ['@everyone'],
    'rules': ['@everyone'], 'welcome': ['@everyone'],
    'off-topic': ['@everyone'], 'random': ['@everyone'],
    'admin': ['Admin'], 'moderator': ['Moderator'],
    'mod': ['Moderator'], 'staff': ['Staff'],
    'memes': ['Meme Lord'], 'owner': ['Owner'],
    'lounge': ['@everyone'], 'chat': ['@everyone'],
}


@bot.event
async def on_ready():
    global channel_manager, command_parser, voice_listener, brain
    channel_manager = ChannelManager(bot, DEFAULT_ROLE_MAP)
    command_parser = CommandParser()
    voice_listener = VoiceListener(bot)
    brain = BotBrain()
    print("=" * 60)
    print(f"✅ Bot ONLINE: {bot.user.name}")
    for g in bot.guilds:
        print(f"   📌 {g.name} ({g.member_count} members)")
    print(f"🧠 AI: {command_parser.get_provider_name()}")
    print("=" * 60)


async def execute_action(guild, action, channel_mgr, requested_by=None, skip_auto_roles=False):
    """Execute a single parsed action dict"""
    # Safety: make sure action is a dict
    if not isinstance(action, dict):
        return f"⚠️ Invalid action format"

    act = action.get('action', 'unknown')

    if act == 'create_channel':
        return await channel_mgr.create_channel(
            guild=guild, channel_name=action.get('channel_name', 'new-channel'),
            channel_type=action.get('channel_type', 'text'),
            requested_by=requested_by, custom_roles=action.get('roles'),
            assign_users=action.get('assign_users'),
            category_name=action.get('category'), skip_auto_roles=skip_auto_roles,
        )
    elif act == 'delete_channel':
        return await channel_mgr.delete_channel(guild, action.get('channel_name', ''))
    elif act == 'move_channel':
        return await channel_mgr.move_channel(guild, action.get('channel_name', ''), action.get('category_name', ''))
    elif act == 'rename_channel':
        return await channel_mgr.rename_channel(guild, action.get('old_name', ''), action.get('new_name', ''))
    elif act == 'create_category':
        return await channel_mgr.create_category(guild, action.get('category_name', ''))
    elif act == 'set_role':
        return await channel_mgr.set_channel_role(guild, action.get('channel_name', ''), action.get('role_name', ''))
    elif act == 'make_public':
        return await channel_mgr.make_channel_public(guild, action.get('channel_name', ''))
    elif act == 'make_private':
        return await channel_mgr.make_channel_private(guild, action.get('channel_name', ''), action.get('roles', []))
    elif act == 'assign_role_to_user':
        return await channel_mgr.assign_role_to_user(guild, action.get('role_name', ''), action.get('user_id'), action.get('user_name'))
    elif act == 'skip':
        return f"⏭️ `{action.get('channel_name', '?')}` — {action.get('reason', 'already fits')}"
    
    elif act == 'create_role':
        return await channel_mgr.create_role_with_color(
            guild,
            action.get('role_name', ''),
            action.get('color', '#5865F2'),
            permissions=action.get('permissions', [])
        )

    elif act == 'delete_role':
        return await channel_mgr.delete_role(guild, action.get('role_name', ''))

    elif act == 'assign_role_to_bot':
        return await channel_mgr.assign_role_to_bot(
            guild, action.get('role_name', '')
        )

    elif act == 'move_role':
        role = discord.utils.get(guild.roles, name=action.get('role_name', ''))
        if not role:
            return f"❌ Role `{action.get('role_name')}` not found!"
        if role >= guild.me.top_role:
            return f"❌ Can't move `{role.name}` — it's above my role!"
        pos = action.get('position', 1)
        await role.edit(position=pos)
        return f"✅ `{role.name}` moved to position {pos}!"

    elif act == 'remove_role_from_user':
        return await channel_mgr.remove_role_from_user(
            guild, action.get('role_name', ''), action.get('user_name', ''))

    elif act == 'create_stage':
        return await channel_mgr.create_stage_channel(
            guild, action.get('channel_name', ''), action.get('category'))

    elif act == 'create_forum':
        return await channel_mgr.create_forum_channel(
            guild, action.get('channel_name', ''), action.get('category'))

    elif act == 'set_topic':
        return await channel_mgr.set_channel_topic(
            guild, action.get('channel_name', ''), action.get('topic', ''))

    elif act == 'set_slowmode':
        return await channel_mgr.set_slowmode(
            guild, action.get('channel_name', ''), action.get('seconds', 0))

    elif act == 'set_voice_limit':
        return await channel_mgr.set_voice_limit(
            guild, action.get('channel_name', ''), action.get('limit', 0))

    elif act == 'create_event':
        return await channel_mgr.create_event(
            guild, action.get('event_name', 'Event'),
            action.get('description', ''),
            action.get('channel_name'),
            action.get('start_hours', 1),
            action.get('duration_hours', 1))

    elif act == 'cancel_event':
        return await channel_mgr.cancel_event(guild, action.get('event_name', ''))

    elif act == 'clone_channel':
        return await channel_mgr.clone_channel(guild, action.get('channel_name', ''))

    elif act == 'purge_messages':
        channel = None
        ch_name = action.get('channel_name', '')
        if ch_name:
            channel = channel_mgr._find_channel(guild, ch_name)
        if not channel and hasattr(guild, '_bot_ctx_channel'):
            channel = guild._bot_ctx_channel
        if channel:
            return await channel_mgr.purge_messages(channel, action.get('count', 10))
        return "❌ Channel not found for purge!"

    elif act == 'kick_user':
        return await channel_mgr.kick_member(
            guild, action.get('user_name', ''), action.get('reason', 'Kicked by AutoBot'))

    elif act == 'ban_user':
        return await channel_mgr.ban_member(
            guild, action.get('user_name', ''), action.get('reason', 'Banned by AutoBot'))

    elif act == 'timeout_user':
        return await channel_mgr.timeout_member(
            guild, action.get('user_name', ''),
            action.get('minutes', 5), action.get('reason', 'Timed out by AutoBot'))
    
    elif act == 'skip':
        return f"⏭️ `{action.get('channel_name', '?')}` — {action.get('reason', 'already fits')}"

    else:
        return f"🤔 Unknown action: `{act}`"


# ============================================
# BASIC COMMANDS (same as before)
# ============================================

@bot.command(name='create')
async def create_channel(ctx, channel_type: str = None, *, channel_name: str = None):
    if not ctx.author.guild_permissions.manage_channels:
        return await ctx.send("❌ No permission!")
    if not channel_type or not channel_name:
        return await ctx.send("📝 `!create text name` or `!create voice name`\n🧠 Or: `!do create a gaming channel`")
    channel_type = channel_type.lower()
    if channel_type not in ['text', 'voice']:
        return await ctx.send("❌ Type must be `text` or `voice`!")
    async with ctx.typing():
        result = await channel_manager.create_channel(guild=ctx.guild, channel_name=channel_name, channel_type=channel_type, requested_by=ctx.author)
    brain.log_action(ctx.guild.name, ctx.author.name, f"Create {channel_type}", channel_name, "✅" in result)
    await ctx.send(result)


@bot.command(name='delete')
async def delete_channel(ctx, *, channel_input: str = None):
    if not ctx.author.guild_permissions.manage_channels:
        return await ctx.send("❌ No permission!")
    if not channel_input:
        return await ctx.send("📝 `!delete channel-name`")
    mention_match = re.search(r'<#(\d+)>', channel_input)
    if mention_match:
        channel = ctx.guild.get_channel(int(mention_match.group(1)))
    else:
        clean = re.sub(r'^(text|voice)\s+', '', channel_input.strip(), flags=re.IGNORECASE).strip()
        channel = channel_manager._find_channel(ctx.guild, clean)
    if not channel:
        return await ctx.send(f"❌ `{channel_input}` not found!")
    if isinstance(channel, discord.CategoryChannel):
        return await ctx.send(f"⚠️ `{channel.name}` is a category. Use `!delcategory`")
    name = channel.name
    ct = "Text" if isinstance(channel, discord.TextChannel) else "Voice"
    await ctx.send(f"⚠️ Delete **{ct.lower()}** `{name}`? `yes`/`no`")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=15.0)
        if msg.content.lower() in ['yes', 'y']:
            await channel.delete(reason=f"By {ctx.author}")
            brain.log_action(ctx.guild.name, ctx.author.name, "Delete", name, True)
            await ctx.send(f"🗑️ `{name}` deleted!")
        else:
            await ctx.send("❌ Cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Timed out.")


@bot.command(name='delcategory')
async def delete_category(ctx, *, name: str = None):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ Admin only!")
    if not name:
        return await ctx.send("📝 `!delcategory Name`")
    cat = channel_manager._find_category(ctx.guild, name)
    if not cat:
        return await ctx.send(f"❌ Category `{name}` not found!")
    n = len(cat.channels)
    await ctx.send(f"⚠️ Delete **`{cat.name}`** ({n} channels)?\n`yes` = category only | `all` = category + channels | `no` = cancel")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=20.0)
        if msg.content.lower() == 'all':
            for ch in cat.channels:
                await ch.delete(); await asyncio.sleep(0.5)
            await cat.delete()
            await ctx.send(f"🗑️ `{cat.name}` + {n} channels gone!")
        elif msg.content.lower() in ['yes', 'y']:
            await cat.delete()
            await ctx.send(f"🗑️ Category `{cat.name}` deleted!")
        else:
            await ctx.send("❌ Cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("⏰")


@bot.command(name='move')
async def move_channel(ctx, channel_name: str = None, *, category_name: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not channel_name or not category_name: return await ctx.send("📝 `!move ch Category`")
    async with ctx.typing():
        r = await channel_manager.move_channel(ctx.guild, channel_name, category_name)
    await ctx.send(r)


@bot.command(name='category')
async def create_category(ctx, *, name: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not name: return await ctx.send("📝 `!category Name`")
    async with ctx.typing():
        r = await channel_manager.create_category(ctx.guild, name)
    await ctx.send(r)


@bot.command(name='setrole')
async def set_channel_role(ctx, ch: str = None, *, role: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not ch or not role: return await ctx.send("📝 `!setrole ch Role`")
    async with ctx.typing():
        r = await channel_manager.set_channel_role(ctx.guild, ch, role)
    await ctx.send(r)


@bot.command(name='rename')
async def rename_channel(ctx, old: str = None, *, new: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not old or not new: return await ctx.send("📝 `!rename old new`")
    async with ctx.typing():
        r = await channel_manager.rename_channel(ctx.guild, old, new)
    await ctx.send(r)


@bot.command(name='makepublic')
async def make_public(ctx, *, name: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not name: return await ctx.send("📝 `!makepublic ch`")
    r = await channel_manager.make_channel_public(ctx.guild, name)
    await ctx.send(r)


@bot.command(name='makeprivate')
async def make_private(ctx, ch: str = None, *, role: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not ch: return await ctx.send("📝 `!makeprivate ch [Role]`")
    r = await channel_manager.make_channel_private(ctx.guild, ch, [role] if role else [])
    await ctx.send(r)


@bot.command(name='listchannels')
async def list_channels(ctx):
    async with ctx.typing():
        r = await channel_manager.list_channels(ctx.guild)
    for i in range(0, len(r), 1900):
        await ctx.send(r[i:i+1900])


@bot.command(name='lockdown')
async def lockdown(ctx, *, name: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    t = ctx.channel
    if name:
        t = channel_manager._find_channel(ctx.guild, name)
        if not t: return await ctx.send(f"❌ `{name}` not found!")
    await t.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 `{t.name}` locked!")


@bot.command(name='unlock')
async def unlock(ctx, *, name: str = None):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    t = ctx.channel
    if name:
        t = channel_manager._find_channel(ctx.guild, name)
        if not t: return await ctx.send(f"❌ `{name}` not found!")
    await t.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 `{t.name}` unlocked!")


# ============================================
# !do — SMART COMMAND (FIXED)
# ============================================

@bot.command(name='do')
async def smart_command(ctx, *, instruction: str = None):
    if not ctx.author.guild_permissions.manage_channels:
        return await ctx.send("❌ No permission!")

    if not instruction:
        embed = discord.Embed(title="🧠 Smart Commands", description=(
            "**Talk to me naturally!**\n\n"
            "💬 **Chat:**\n```\n!do hello\n!do who are you?\n!do tell me a joke\n```\n"
            "🔧 **Commands:**\n```\n!do create gaming channel\n!do make it public\n!do delete that\n!do what did you last do?\n```"
        ), color=discord.Color.purple())
        return await ctx.send(embed=embed)

    # Save user message to brain
    brain.add_message(str(ctx.channel.id), 'user', instruction)

    # Build context
    server_snapshot = brain.get_server_snapshot(ctx.guild)
    conversation = brain.format_conversation_for_ai(str(ctx.channel.id))
    error_lessons = brain.get_error_lessons()
    recent_actions = brain.get_recent_actions(5)

    async with ctx.typing():
        try:
            result = await command_parser.parse(
                instruction,
                server_snapshot=server_snapshot,
                conversation_history=conversation,
                error_lessons=error_lessons,
                recent_actions=recent_actions,
                guild_id=str(ctx.guild.id),
                requester_name=ctx.author.name,
                requester_nick=ctx.author.display_name,
            )
        except Exception as e:
            print(f"❌ Parser error: {e}")
            traceback.print_exc()
            brain.log_error(instruction, str(e))
            return await ctx.send(f"❌ Brain glitch: {str(e)[:100]}\nTry again!")

    # Safety checks
    if isinstance(result, str):
        brain.add_message(str(ctx.channel.id), 'bot', result)
        return await ctx.send(f"💬 *{result}*")

    if isinstance(result, list):
        result = {"message": "", "actions": result}

    if not isinstance(result, dict):
        return await ctx.send("🤔 Something went wrong. Try again!")

    ai_message = str(result.get('message', '') or '')
    actions = result.get('actions', []) or []
    if not isinstance(actions, list):
        actions = []
    actions = [a for a in actions if isinstance(a, dict)]

    # Show AI message
    if ai_message:
        # Handle long messages (Discord limit: 2000 chars)
        full_msg = f"💬 *{ai_message}*"
        if len(full_msg) > 1900:
            # Split into multiple messages
            chunks = []
            current = "💬 *"
            sentences = ai_message.replace('\\n', '\n').split('\n')
            for sentence in sentences:
                if len(current) + len(sentence) + 5 > 1900:
                    current += "*"
                    chunks.append(current)
                    current = "*" + sentence + "\n"
                else:
                    current += sentence + "\n"
            if current.strip('* \n'):
                current += "*"
                chunks.append(current)
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(full_msg)

    # No actions = pure conversation
    if not actions:
        if not ai_message:
            await ctx.send("💬 *Hey! I heard you but I'm not sure what server action you need. Just chat with me or try `!bothelp`!* 😊")
        brain.add_message(str(ctx.channel.id), 'bot', ai_message or "chatted")
        return

    # Execute actions
    all_results = []
    for action in actions:
        try:
            r = await execute_action(ctx.guild, action, channel_manager, requested_by=ctx.author)
            all_results.append(r)
            action_name = action.get('action', '?')
            action_target = action.get('channel_name', action.get('category_name', '?'))
            brain.log_action(ctx.guild.name, ctx.author.name, action_name, str(action_target)[:100], "❌" not in r)
            if "❌" in r:
                brain.log_error(instruction, r)
        except Exception as e:
            all_results.append(f"❌ {str(e)}")
            brain.log_error(instruction, str(e))

        

    final = "\n\n".join(all_results)
    brain.add_message(str(ctx.channel.id), 'bot', final[:200])

    for i in range(0, len(final), 1900):
        await ctx.send(final[i:i+1900])


# ============================================
# REVAMP
# ============================================

@bot.command(name='revamp')
async def revamp_server(ctx, *, theme: str = None):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ Admin only!")
    if not theme:
        embed = discord.Embed(title="🎨 Server Revamp", description=(
            "`!revamp <theme>`\n```\n!revamp valentine's day\n!revamp gaming community\n!revamp anime\n!revamp christmas\n```"
        ), color=discord.Color.magenta())
        return await ctx.send(embed=embed)

    server_snapshot = brain.get_server_snapshot(ctx.guild)

    async with ctx.typing():
        try:
            result = await command_parser.parse_revamp(theme, server_snapshot, ctx.guild.name)
        except Exception as e:
            return await ctx.send(f"❌ Revamp planning failed: {str(e)[:100]}")

    # Safely extract
    if isinstance(result, list):
        result = {"message": "", "actions": result}
    if not isinstance(result, dict):
        return await ctx.send("🤔 Couldn't generate plan.")

    actions = result.get('actions', []) or []
    if not isinstance(actions, list):
        actions = []
    actions = [a for a in actions if isinstance(a, dict)]
    ai_message = result.get('message', '') or ''

    if not actions:
        return await ctx.send("🤔 Couldn't generate plan. Try different theme!")

    # Show plan
    plan = f"🎨 **Revamp: {theme}**\n"
    if ai_message:
        plan += f"💬 *{ai_message}*\n\n"
    for i, a in enumerate(actions, 1):
        act = a.get('action', '?')
        if act == 'create_category': plan += f"  {i}. 📁 Category: **{a.get('category_name', '?')}**\n"
        elif act == 'create_channel':
            icon = "💬" if a.get('channel_type') == 'text' else "🔊"
            cat = f" → {a.get('category')}" if a.get('category') else ""
            plan += f"  {i}. {icon} Create: **{a.get('channel_name', '?')}**{cat}\n"
        elif act == 'rename_channel': plan += f"  {i}. ✏️ Rename: `{a.get('old_name', '?')}` → `{a.get('new_name', '?')}`\n"
        elif act == 'move_channel': plan += f"  {i}. 📦 Move: `{a.get('channel_name', '?')}` → `{a.get('category_name', '?')}`\n"
        elif act == 'delete_channel': plan += f"  {i}. 🗑️ Delete: `{a.get('channel_name', '?')}`\n"
        elif act == 'skip': plan += f"  {i}. ⏭️ Keep: `{a.get('channel_name', '?')}` ({a.get('reason', '')})\n"
    plan += f"\n📊 {len(actions)} actions | `yes` to apply / `no` to cancel"

    for i in range(0, len(plan), 1900):
        await ctx.send(plan[i:i+1900])

    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        if msg.content.lower() not in ['yes', 'y']:
            return await ctx.send("❌ Cancelled.")
    except asyncio.TimeoutError:
        return await ctx.send("⏰")

    await ctx.send("🚀 **Applying...**")
    ok = skip = err = 0
    results = []
    for i, a in enumerate(actions, 1):
        try:
            async with ctx.typing():
                r = await execute_action(ctx.guild, a, channel_manager, requested_by=ctx.author, skip_auto_roles=True)
                results.append(f"{i}. {r}")
                if any(x in r for x in ["✅", "📁", "✏️", "📦"]): ok += 1
                elif "⏭️" in r: skip += 1
                else: err += 1
                await asyncio.sleep(1.2)
        except Exception as e:
            results.append(f"{i}. ❌ {e}")
            err += 1

    summary = f"\n\n🎨 **Done!** ✅{ok} ⏭️{skip} ❌{err}"
    brain.log_action(ctx.guild.name, ctx.author.name, "Revamp", theme, err == 0)
    rt = "\n".join(results) + summary
    for i in range(0, len(rt), 1900):
        await ctx.send(rt[i:i+1900])


# ============================================
# VOICE
# ============================================

@bot.command(name='listen')
async def start_listening(ctx):
    if not ctx.author.guild_permissions.manage_channels: return await ctx.send("❌")
    if not ctx.author.voice: return await ctx.send("❌ Join VC first!")
    async with ctx.typing():
        r = await voice_listener.start_listening(ctx.author.voice.channel, ctx.channel, ctx.guild, channel_manager, command_parser)
    await ctx.send(r)

@bot.command(name='stoplisten')
async def stop_listening(ctx):
    r = await voice_listener.stop_listening(ctx.guild)
    await ctx.send(r)


# ============================================
# HELP & STATUS
# ============================================

@bot.command(name='bothelp')
async def bot_help(ctx):
    embed = discord.Embed(title="🤖 AutoBot — Help", color=discord.Color.blue())
    embed.add_field(name="📝 Basics", value=(
        "`!create text/voice name`\n`!delete name` or `!delete #channel`\n"
        "`!move ch category` | `!rename old new`\n"
        "`!category name` | `!delcategory name`\n"
        "`!setrole ch role` | `!makepublic ch` | `!makeprivate ch role`\n"
        "`!lockdown` / `!unlock` | `!listchannels`"
    ), inline=False)
    embed.add_field(name="🧠 Smart (AI + Memory)", value=(
        "`!do <anything>` — I understand natural language!\n"
        "```\n!do who are you?\n!do create 👑-owners channel\n"
        "!do make it public\n!do tell me a joke\n"
        "!do create gaming and move to Fun\n```"
    ), inline=False)
    embed.add_field(name="🎨 Revamp", value="`!revamp <theme>` — Redesign your whole server!", inline=False)
    embed.add_field(name="🎤 Voice", value="`!listen` / `!stoplisten`", inline=False)
    embed.set_footer(text="🧠 I remember our conversations! | Built by Ayush")
    await ctx.send(embed=embed)

@bot.command(name='botstatus')
async def status(ctx):
    if not ctx.author.guild_permissions.administrator: return await ctx.send("❌")
    embed = discord.Embed(title="📊 Status", color=discord.Color.green())
    embed.add_field(name="Bot", value=bot.user.name, inline=True)
    embed.add_field(name="AI", value=command_parser.get_provider_name(), inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency*1000)}ms", inline=True)
    embed.add_field(name="Memory", value=f"{brain.memory.get('audit_count', 0)} actions logged", inline=True)
    embed.add_field(name="Channels", value=len(ctx.guild.channels), inline=True)
    embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❓ Try `!bothelp`")
    elif isinstance(error, commands.CommandInvokeError):
        original = getattr(error, 'original', error)
        print(f"❌ Command error: {type(original).__name__}: {original}")
        traceback.print_exc()
        await ctx.send(f"❌ Something broke: {str(original)[:150]}\nTry again or use `!bothelp`")
    else:
        print(f"❌ {type(error).__name__}: {error}")
        await ctx.send(f"❌ {str(error)[:150]}")


@bot.listen("on_message")
async def handle_plain_message(message):
    if message.author.bot:
        return
    if not message.guild:
        return
    if message.content.startswith('!'):
        return

    user_input = message.content.strip()
    if not user_input:
        return

    guild = message.guild
    channel_id = str(message.channel.id)
    username = message.author.name
    nickname = message.author.display_name

    try:
        async with message.channel.typing():
            snapshot = brain.get_server_snapshot(guild) if brain else ""
            conv_history = brain.format_conversation_for_ai(channel_id) if brain else ""
            cross_channel = brain.search_all_channels(user_input) if brain else ""
            if cross_channel:
                conv_history = conv_history + "\n\n" + cross_channel
            recent_actions = brain.get_recent_actions(10) if brain else ""
            audit_search = brain.search_audit_log(user_input) if brain else ""
            if audit_search:
                conv_history = conv_history + "\n\n" + audit_search
            if brain:
                brain.add_message(channel_id, "user", user_input)
            result = await command_parser.parse(
                instruction=user_input,
                server_snapshot=snapshot,
                conversation_history=conv_history,
                guild_id=str(guild.id),
                requester_name=username,
                requester_nick=nickname,
                recent_actions=recent_actions
            )
            reply = result.get("message", "")
            actions = result.get("actions", [])

            # Execute actions (channel create/delete etc)
            action_results = []
            for action in actions:
                try:
                    action_result = await execute_action(
                        guild, action, channel_manager,
                        requested_by=nickname
                    )
                    if action_result:
                        action_results.append(str(action_result))
                    if brain:
                        brain.log_action(
                            guild.name, nickname,
                            action.get("action", "?"),
                            str(action),
                            True
                        )
                except Exception as ae:
                    print(f"❌ Action error: {ae}")
                    action_results.append(f"❌ {str(ae)[:80]}")

            # Send reply
            if reply:
                await message.channel.send(reply)
            if action_results:
                await message.channel.send("\n".join(action_results))
            if brain:
                summary = reply or ", ".join(
                    a.get("action","?") for a in actions
                )
                brain.add_message(channel_id, "assistant", summary[:200])
    except Exception as e:
        print(f"❌ Plain message error: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    print("🚀 Bot v6")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Bad token!")
    except Exception as e:
        print(f"❌ {e}")