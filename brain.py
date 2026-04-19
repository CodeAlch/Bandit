#!/usr/bin/env python3
"""
Bot Brain — Memory, Audit Logs, Conversation History
"""

import json
import os
import discord
from datetime import datetime

MEMORY_FILE = "memory.json"
AUDIT_FILE = "audit_log.md"

class BotBrain:
    def __init__(self):
        self.memory = self._load_memory()
        self._ensure_audit_file()
        print("🧠 Brain loaded!")
        print(f"   📝 Conversations: {len(self.memory.get('conversations', {}))}")
        print(f"   📋 Audit entries: {self.memory.get('audit_count', 0)}")

    def _load_memory(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'conversations': {},
            'user_preferences': {},
            'error_history': [],
            'audit_count': 0,
            'server_notes': {},
            'created_at': datetime.now().isoformat(),
        }

    def _save_memory(self):
        try:
            with open(MEMORY_FILE, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Memory save error: {e}")

    def _ensure_audit_file(self):
        if not os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE, 'w') as f:
                f.write("# 🤖 Bot Audit Log\n\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")

    # ==========================================
    # CONVERSATION HISTORY
    # ==========================================

    def add_message(self, channel_id: str, role: str, content: str):
        channel_id = str(channel_id)
        if channel_id not in self.memory['conversations']:
            self.memory['conversations'][channel_id] = []
        self.memory['conversations'][channel_id].append({
            'role': role,
            'content': content,
            'time': datetime.now().strftime('%H:%M:%S'),
        })
        self.memory['conversations'][channel_id] = \
            self.memory['conversations'][channel_id][-20:]
        self._save_memory()

    def get_conversation(self, channel_id: str, last_n: int = 10) -> list:
        channel_id = str(channel_id)
        return self.memory['conversations'].get(channel_id, [])[-last_n:]

    def format_conversation_for_ai(self, channel_id: str) -> str:
        history = self.get_conversation(channel_id, last_n=10)
        if not history:
            return ""
        lines = ["RECENT CONVERSATION (for context):"]
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Bot"
            lines.append(f"  [{msg['time']}] {role}: {msg['content']}")
        return "\n".join(lines)

    # ==========================================
    # AUDIT LOG
    # ==========================================

    def log_action(self, guild_name: str, user_name: str, action: str,
                   details: str, success: bool):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "✅" if success else "❌"
        entry = (
            f"### {status} {action}\n"
            f"- **Time:** {timestamp}\n"
            f"- **Server:** {guild_name}\n"
            f"- **User:** {user_name}\n"
            f"- **Details:** {details}\n\n"
        )
        try:
            with open(AUDIT_FILE, 'a') as f:
                f.write(entry)
        except:
            pass
        self.memory['audit_count'] = self.memory.get('audit_count', 0) + 1
        self._save_memory()

    def get_recent_actions(self, n: int = 5) -> str:
        try:
            with open(AUDIT_FILE, 'r') as f:
                content = f.read()
            entries = content.split('### ')[1:]
            recent = entries[-n:] if len(entries) >= n else entries
            if not recent:
                return "No recent actions."
            result = "RECENT BOT ACTIONS:\n"
            for entry in recent:
                first_line = entry.split('\n')[0].strip()
                result += f"  - {first_line}\n"
            return result
        except:
            return "No audit history."

    # ==========================================
    # ERROR LEARNING
    # ==========================================

    def log_error(self, instruction: str, error: str):
        self.memory['error_history'].append({
            'instruction': instruction,
            'error': error,
            'time': datetime.now().isoformat(),
        })
        self.memory['error_history'] = self.memory['error_history'][-50:]
        self._save_memory()

    def get_error_lessons(self) -> str:
        if not self.memory['error_history']:
            return ""
        lessons = ["LESSONS FROM PAST ERRORS (avoid these):"]
        seen = set()
        for err in self.memory['error_history'][-10:]:
            key = err['error'][:50]
            if key not in seen:
                seen.add(key)
                lessons.append(f"  - '{err['instruction'][:60]}' → {err['error'][:80]}")
        return "\n".join(lessons)

    # ==========================================
    # SERVER SNAPSHOT (FIXED)
    # ==========================================

    def get_server_snapshot(self, guild) -> str:
        """Get detailed snapshot of current server structure"""
        lines = ["CURRENT SERVER STRUCTURE (exact, live data):"]
        lines.append(f"Server: {guild.name}")
        lines.append(f"Total: {len(guild.text_channels)} text, {len(guild.voice_channels)} voice, {len(guild.categories)} categories")
        lines.append("")

        # Categories with their channels
        for cat in sorted(guild.categories, key=lambda c: c.position):
            lines.append(f"  CATEGORY: \"{cat.name}\"")
            for ch in sorted(cat.channels, key=lambda c: c.position):
                if isinstance(ch, discord.TextChannel):
                    lines.append(f"    TEXT: \"{ch.name}\"")
                elif isinstance(ch, discord.VoiceChannel):
                    lines.append(f"    VOICE: \"{ch.name}\"")
                elif isinstance(ch, discord.StageChannel):
                    lines.append(f"    STAGE: \"{ch.name}\"")

        # Uncategorized channels
        uncategorized = [
            c for c in guild.channels
            if c.category is None and not isinstance(c, discord.CategoryChannel)
        ]
        if uncategorized:
            lines.append("  UNCATEGORIZED:")
            for ch in uncategorized:
                if isinstance(ch, discord.TextChannel):
                    lines.append(f"    TEXT: \"{ch.name}\"")
                elif isinstance(ch, discord.VoiceChannel):
                    lines.append(f"    VOICE: \"{ch.name}\"")
                elif isinstance(ch, discord.StageChannel):
                    lines.append(f"    STAGE: \"{ch.name}\"")

        # Roles
        role_names = [r.name for r in guild.roles if r.name != '@everyone'][:20]
        if role_names:
            lines.append(f"\n  EXISTING ROLES: {', '.join(role_names)}")

        return "\n".join(lines)

    # ==========================================
    # USER PREFERENCES
    # ==========================================

    def set_preference(self, user_id: str, key: str, value):
        user_id = str(user_id)
        if user_id not in self.memory['user_preferences']:
            self.memory['user_preferences'][user_id] = {}
        self.memory['user_preferences'][user_id][key] = value
        self._save_memory()

    def get_preferences(self, user_id: str) -> dict:
        return self.memory.get('user_preferences', {}).get(str(user_id), {})