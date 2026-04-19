#!/usr/bin/env python3
"""
Command Parser v13 — Adaptive language, nickname support, multi-message
"""

import re
import os
from dotenv import load_dotenv
load_dotenv()
import json
import traceback
import asyncio
import time
# ==================== NVIDIA NEMOTRON 3 SUPER ====================
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

MODEL_NAME = "nvidia/nemotron-3-super-120b-a12b"
# ============================================================


BOT_SYSTEM = """You are "AutoBot" — a smart, funny Discord server manager bot.

ABOUT YOU:
- Created by Ayush, a developer from Jamia Millia Islamia university, New Delhi
- Built with Python, Discord.py, and NVIDIA Nemotron
- You have knowledge about technology, programming, APIs, and general topics
- You can have detailed conversations about any topic
- You're helpful, witty, and knowledgeable

LANGUAGE RULES:
- MATCH the user's language. If they write in English, reply in English.
- If they write in Hindi/Hinglish, reply in Hinglish.
- If they ask you to speak in a specific language, SWITCH and STAY in that language.
- Default: English with light humor.

PERSONALITY:
- Smart and knowledgeable — you can explain technical concepts clearly
- Funny but not overdoing it — natural humor
- Helpful — always answer the question fully
- If a topic needs a long explanation, give a COMPLETE answer, don't cut off

RESPONSE FORMAT:
ALWAYS respond with ONLY a JSON object. No markdown code blocks.
{"message": "your full response here", "actions": []}

For conversations/questions: {"message": "your complete answer — can be multiple paragraphs", "actions": []}
For server commands: {"message": "short acknowledgment", "actions": [{"action":"..."}]}

IMPORTANT:
- "message" can be LONG — up to 1500 characters for detailed answers
- "actions" is [] for pure conversation
- No ``` blocks. No text before {.
- For technical questions, give a REAL detailed answer, not just "let me explain"

AVAILABLE ACTIONS:
create_channel: {"action":"create_channel","channel_type":"text"/"voice","channel_name":"name","roles":["Role"],"category":"Cat"}
delete_channel: {"action":"delete_channel","channel_name":"exact-name"}
move_channel: {"action":"move_channel","channel_name":"exact-name","category_name":"Category"}
rename_channel: {"action":"rename_channel","old_name":"current","new_name":"new"}
create_category: {"action":"create_category","category_name":"Name"}
make_public: {"action":"make_public","channel_name":"exact-name"}
make_private: {"action":"make_private","channel_name":"exact-name","roles":["Role"]}
set_role: {"action":"set_role","channel_name":"name","role_name":"Role"}
create_role: {"action":"create_role","role_name":"Name","color":"#HEX"}
assign_role_to_user: {"action":"assign_role_to_user","role_name":"Role","user_name":"nickname_or_username"}
assign_role_to_bot: {"action":"assign_role_to_bot","role_name":"Role"}
delete_role: {"action":"delete_role","role_name":"Name"}
remove_role_from_user: {"action":"remove_role_from_user","role_name":"Role","user_name":"nickname"}
create_stage: {"action":"create_stage","channel_name":"name","category":"Cat"}
create_forum: {"action":"create_forum","channel_name":"name","category":"Cat"}
set_topic: {"action":"set_topic","channel_name":"name","topic":"description text"}
set_slowmode: {"action":"set_slowmode","channel_name":"name","seconds":5}
set_voice_limit: {"action":"set_voice_limit","channel_name":"name","limit":10}
create_event: {"action":"create_event","event_name":"Name","description":"desc","channel_name":"vc-name","start_hours":1,"duration_hours":2}
cancel_event: {"action":"cancel_event","event_name":"Name"}
clone_channel: {"action":"clone_channel","channel_name":"name"}
purge_messages: {"action":"purge_messages","channel_name":"name","count":10}
kick_user: {"action":"kick_user","user_name":"nickname","reason":"reason"}
ban_user: {"action":"ban_user","user_name":"nickname","reason":"reason"}
timeout_user: {"action":"timeout_user","user_name":"nickname","minutes":5,"reason":"reason"}

ACTION RULES:
- Channel names: SHORT (1-50 chars), hyphens for text
- NEVER use instruction as channel name
- Split "and"/"then"/"also" into MULTIPLE actions
- Default: text channel
- CHECK server structure — don't recreate existing
- FUZZY MATCH existing names
- "it"/"that" = check conversation history
- "me"/"myself" = use the USER_NICKNAME provided
- "yourself"/"you"/"bot" = use assign_role_to_bot
- For colors: use proper hex codes. aqua=#00FFFF, aqua green=#00CED1, red=#FF0000, blue=#0000FF, green=#00FF00, purple=#800080, pink=#FF69B4, gold=#FFD700, white=#FFFFFF, teal=#008080, cyan=#00FFFF, orange=#FFA500, yellow=#FFFF00, sky blue=#87CEEB, lime=#00FF00, navy=#000080, coral=#FF7F50, mint=#98FF98, lavender=#E6E6FA, blurple=#5865F2

EXAMPLES:

User (English): "hello"
→ {"message": "Hey! 👋 What's up? Need something built or just hanging out?", "actions": []}

User: "who are you?"
→ {"message": "I'm AutoBot! 🤖 A Discord server manager built by Ayush — a developer from Jamia Millia Islamia, New Delhi. I can create channels, manage roles, organize your server, and even have conversations like this one. Built with Python and NVIDIA Nemotron AI. What can I do for you?", "actions": []}

User: "explain API rate limits"
→ {"message": "Sure! API rate limits control how many requests you can make to an API in a given time period.\\n\\n**How it works:**\\n- Free tier: Usually 15 requests/minute, 1500/day\\n- Paid tier: Much higher limits\\n- If you exceed: You get a 429 error (Too Many Requests)\\n\\n**For Google Gemini:**\\n- Free: 15 RPM, 1M tokens/day\\n- With $10 credit: Same free tier, credits cover overages\\n- Pro plan: Higher limits\\n\\nThe key thing: Your $10 monthly credit covers any usage beyond the free tier. At your usage level, you'll likely stay within free limits!", "actions": []}

User: "create role Azure White with aqua green color, give to me and yourself"
(User nickname: Ayush, username: ayu5h)
→ {"message": "Creating Azure White role with aqua green color! Giving it to you (Ayush) and myself 🎨", "actions": [{"action":"create_role","role_name":"Azure White","color":"#00CED1"},{"action":"assign_role_to_user","role_name":"Azure White","user_name":"Ayush"},{"action":"assign_role_to_bot","role_name":"Azure White"}]}
NOTE: Used nickname "Ayush" not username "ayu5h" for user search!

User: "make sentinals private with Sentinel Guard role"
→ {"message": "Locking down sentinals with Sentinel Guard role! 🔒", "actions": [{"action":"create_role","role_name":"Sentinel Guard","color":"#5865F2"},{"action":"make_private","channel_name":"sentinals","roles":["Sentinel Guard"]}]}"""


class CommandParser:
    def __init__(self):
        self.has_nvidia = True  # Ab hum NVIDIA use kar rahe hain
        self.histories = {}
        self.last_req = 0

        # Test call
        try:
            test = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "Reply only: ready"}],
                temperature=0,
                max_tokens=20
            )
            print(f"✅ NVIDIA Test OK: {test.choices[0].message.content.strip()[:40]}")
            print(f"🧠 Parser: Nemotron-3-Super ✓")
        except Exception as e:
            print(f"⚠️ NVIDIA Test Failed: {e}")
            print(f"🧠 Parser: Nemotron-3-Super (will try anyway)")

    def get_provider_name(self):
        return "🔵 Nemotron-3-Super (NVIDIA)"

    async def _wait(self):
        """Rate limit control"""
        elapsed = time.time() - self.last_req
        if elapsed < 3:  # NVIDIA ke liye thoda tight rakhte hain
            await asyncio.sleep(3 - elapsed)
        self.last_req = time.time()

    async def _call(self, prompt, use_system=True):
        await self._wait()
        
        messages = []
        if use_system:
            messages.append({"role": "system", "content": BOT_SYSTEM})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.6,
                max_tokens=2000,
                top_p=0.95
            )
            if resp.choices and resp.choices[0].message.content:
                return resp.choices[0].message.content.strip()
            return ""
            
        except Exception as e:
            err = str(e).lower()
            print(f"❌ NVIDIA API Error: {e}")
            
            # Rate limit handling
            if '429' in err or 'rate limit' in err or 'quota' in err:
                print("⏳ Rate limit hit, waiting 12 seconds...")
                await asyncio.sleep(12)
                try:
                    # Retry once
                    resp = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=0.6,
                        max_tokens=1500
                    )
                    if resp.choices and resp.choices[0].message.content:
                        return resp.choices[0].message.content.strip()
                except:
                    pass
            return ""

    def _json(self, text):
        if not text: return {"message":"","actions":[]}
        clean = text.strip().replace('```json','').replace('```','').strip()
        try:
            r = json.loads(clean)
            if isinstance(r, dict):
                return {"message":str(r.get('message','')),"actions":list(r.get('actions',[]))}
            if isinstance(r, list):
                return {"message":"","actions":r}
        except: pass
        s = clean.find('{')
        if s >= 0:
            d = 0
            for i in range(s, len(clean)):
                if clean[i]=='{': d+=1
                elif clean[i]=='}':
                    d-=1
                    if d==0:
                        try:
                            r = json.loads(clean[s:i+1])
                            if isinstance(r,dict):
                                return {"message":str(r.get('message','')),"actions":list(r.get('actions',[]))}
                        except: pass
                        break
        if '{' not in text: return {"message":text.strip()[:1500],"actions":[]}
        return {"message":text.strip()[:500],"actions":[]}

    def _hist(self, gid):
        gid=str(gid)
        if gid not in self.histories: self.histories[gid]=[]
        return self.histories[gid]

    def _save(self, gid, role, msg):
        h=self._hist(gid)
        h.append({"role":role,"content":msg[:200]})
        self.histories[str(gid)]=h[-20:]

    async def parse(self, instruction, server_snapshot="", conversation_history="",
                    error_lessons="", recent_actions="", guild_id="0",
                    requester_name="", requester_nick="") -> dict:
        # FIX: Store brain's conversation history so _ai() can use it
        self._last_conversation_history = conversation_history or ""

        if self.has_nvidia:
            try:
                return await self._ai(instruction, server_snapshot, error_lessons,
                                      recent_actions, guild_id, requester_name, requester_nick)
            except Exception as e:
                print(f"  ❌ AI: {e}")
                traceback.print_exc()
        actions = self._regex(instruction)
        if actions: return {"message":"","actions":actions}
        return {"message":"AI offline. Use `!bothelp`","actions":[]}

    async def _ai(self, instruction, snapshot, errors, recent, gid, username, nickname):
        # Still update in-memory history for same-session context
        h = self._hist(gid)

        # =============================================
        # FIX: Use brain's conversation history from memory.json
        # instead of ONLY using self._hist() which is RAM-only
        # =============================================
        hist = ""

        # Priority 1: Brain's history from memory.json (PERSISTENT!)
        brain_hist = getattr(self, '_last_conversation_history', '')

        if brain_hist:
            hist = "\n" + brain_hist
        elif h:
            # Fallback: use in-memory history (same session only)
            hist = "\nRecent conversation:\n"
            for m in h[-8:]:
                hist += f"  {'User' if m['role']=='user' else 'Bot'}: {m['content']}\n"

        parts = []
        cmd_words = ['create','delete','move','rename','make','channel','category','role',
                     'public','private','assign','give','color','apply','set']
        is_cmd = any(w in instruction.lower() for w in cmd_words)

        if is_cmd and snapshot:
            parts.append('\n'.join(snapshot.split('\n')[:20]))

        # ADD CONVERSATION HISTORY — THIS IS THE KEY FIX!
        if hist:
            parts.append(hist)

        if errors:
            parts.append(errors[:200])

        # User identity
        nick_display = nickname or username or "User"
        parts.append(f'\nUSER_NICKNAME: {nick_display}')
        parts.append(f'USER_USERNAME: {username}')
        parts.append(f'When user says "me"/"myself"/"to me", use "{nick_display}" as user_name in actions.')
        parts.append(f'Address the user as "{nick_display}" in your message.')

        parts.append(f'\nUser: "{instruction}"')
        parts.append('\nJSON only (no code blocks):')

        prompt = '\n'.join(parts)
        print(f"\n  🧠 [{nick_display}]: '{instruction}' (cmd={is_cmd}, hist={'YES' if hist else 'NO'}, {len(prompt)}ch)")

        raw = await self._call(prompt)
        if not raw:
            self._save(gid,'user',instruction)
            self._save(gid,'bot','[empty]')
            actions = self._regex(instruction)
            if actions: return {"message":"","actions":actions}
            return {"message":"Brain freeze! Try again in a few seconds 🥶","actions":[]}

        print(f"  🧠 ← ({len(raw)}ch): {raw[:300]}")
        self._save(gid,'user',instruction)
        result = self._json(raw)

        if not isinstance(result.get('actions'),list): result['actions']=[]
        result['actions']=[a for a in result['actions'] if isinstance(a,dict)]

        # Replace placeholders
        for a in result['actions']:
            un = a.get('user_name','')
            if un and un.upper() in ('USER','ME','MYSELF'):
                a['user_name'] = nick_display
            for k in ['channel_name','category_name','old_name','new_name','category','role_name']:
                if k in a and a[k]: a[k]=str(a[k])[:100].strip()

        summary = result.get('message','')[:100]
        if result['actions']:
            summary += f" [{','.join(a.get('action','?') for a in result['actions'])}]"
        self._save(gid,'bot',summary)
        print(f"  🧠 ✅ msg='{result.get('message','')[:60]}' actions={len(result['actions'])}")
        return result

    async def parse_revamp(self, theme, snapshot, server_name):
        if not self.has_gemini:
            return {"message":f"Basic {theme} plan!","actions":self._basic_revamp(theme)}
        try:
            prompt = (f"Redesign '{server_name}' with '{theme}' theme.\n"
                      f"JSON: {{\"message\":\"response\",\"actions\":[...]}}\n"
                      f"Reuse channels. Categories first. 15-20 actions. Emojis.\n\n"
                      f"{snapshot}\n\nJSON:")
            raw = await self._call(prompt)
            r = self._json(raw)
            for a in r.get('actions',[]):
                if isinstance(a,dict):
                    for k in ['channel_name','category_name','old_name','new_name','category']:
                        if k in a and a[k]: a[k]=str(a[k])[:100].strip()
            return r
        except: return {"message":f"Basic {theme} plan!","actions":self._basic_revamp(theme)}

    def _regex(self, text_raw):
        text = text_raw.lower().strip()
        pub = re.search(r'make\s+(.+?)\s+public', text)
        if pub: return [{'action':'make_public','channel_name':pub.group(1).strip()}]
        priv = re.search(r'make\s+(.+?)\s+private(?:\s+(?:with|for)\s+(.+))?', text)
        if priv:
            roles=[priv.group(2).strip()] if priv.group(2) else []
            return [{'action':'make_private','channel_name':priv.group(1).strip(),'roles':roles}]
        cm = re.search(r'(?:create|make)\s+(.+?)\s+(?:and|then)\s+move\s+(?:it\s+)?to\s+(.+)', text)
        if cm:
            n=re.sub(r'\b(text|voice|channel|called|named|a|an|the|new)\b','',cm.group(1)).strip(' -_')
            ct='voice' if 'voice' in cm.group(1) else 'text'
            cat=re.sub(r'\b(category|the)\b','',cm.group(2)).strip()
            if n and cat: return [{'action':'create_channel','channel_type':ct,'channel_name':n},{'action':'move_channel','channel_name':n,'category_name':cat}]
        for p in [r'(?:create|make|add)\s+(?:a\s+)?(?:new\s+)?(text|voice)\s+(?:channel\s+)?(?:called|named)?\s*(.+?)(?:\s*[,.]|$)',r'(?:create|make|add)\s+(?:a\s+)?(text|voice)\s+(.+?)(?:\s*[,.]|$)']:
            m=re.search(p,text)
            if m:
                n=re.sub(r'\b(channel|called|named|the|a|an)\b','',m.group(2)).strip(' -_')
                if n: return [{'action':'create_channel','channel_type':m.group(1),'channel_name':n}]
        s=re.search(r'(?:create|make|add)\s+(.+?)(?:\s*[,.]|$)',text)
        if s and 'category' not in text:
            n=re.sub(r'\b(text|voice|channel|called|named|the|a|an|new)\b','',s.group(1)).strip(' -_')
            if n: return [{'action':'create_channel','channel_type':'voice' if 'voice' in text else 'text','channel_name':n}]
        d=re.search(r'(?:delete|remove)\s+(?:the\s+)?(.+)',text)
        if d: return [{'action':'delete_channel','channel_name':re.sub(r'\b(channel|the)\b','',d.group(1)).strip()}]
        m=re.search(r'move\s+(.+?)\s+to\s+(.+)',text)
        if m: return [{'action':'move_channel','channel_name':m.group(1).strip(),'category_name':m.group(2).strip()}]
        r=re.search(r'rename\s+(.+?)\s+to\s+(.+)',text)
        if r: return [{'action':'rename_channel','old_name':r.group(1).strip(),'new_name':r.group(2).strip()}]
        c=re.search(r'(?:create|make)\s+(?:a\s+)?category\s+(.+)',text)
        if c: return [{'action':'create_category','category_name':c.group(1).strip()}]
        return []

    def _basic_revamp(self, theme):
        t=theme.lower()
        if 'valentine' in t:
            return [{"action":"create_category","category_name":"💕 Love Zone"},{"action":"create_channel","channel_type":"text","channel_name":"💌-love-letters","category":"💕 Love Zone"},{"action":"create_channel","channel_type":"voice","channel_name":"💕 Love Talk","category":"💕 Love Zone"}]
        return [{"action":"create_category","category_name":f"✨ {theme.title()}"},{"action":"create_channel","channel_type":"text","channel_name":"💬-chat","category":f"✨ {theme.title()}"},{"action":"create_channel","channel_type":"voice","channel_name":"🔊 Hangout","category":f"✨ {theme.title()}"}]