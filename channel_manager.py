#!/usr/bin/env python3
"""
Channel Manager v4
- Added make_public / make_private
- Added category placement during creation
- Added skip_auto_roles flag for revamp
- Better channel finding (handles spaces, emojis, voice names)
"""

import discord
import random
import re
import traceback


class ChannelManager:
    def __init__(self, bot, role_map):
        self.bot = bot
        self.role_map = role_map
        self.role_colors = [
            discord.Color.red(), discord.Color.blue(), discord.Color.green(),
            discord.Color.purple(), discord.Color.orange(), discord.Color.gold(),
            discord.Color.teal(), discord.Color.magenta(), discord.Color.dark_blue(),
            discord.Color.dark_green(), discord.Color.dark_purple(),
            discord.Color.dark_red(), discord.Color.blurple(), discord.Color.greyple(),
        ]

    def _match_roles(self, channel_name):
        name_clean = channel_name.lower().replace('-', ' ').replace('_', ' ')
        name_clean = re.sub(r'[^\w\s]', '', name_clean).strip()
        matched = []
        for kw, roles in self.role_map.items():
            if kw in name_clean:
                matched.extend(roles)
        seen = set()
        return [r for r in matched if not (r in seen or seen.add(r))]

    async def _get_or_create_role(self, guild, role_name):
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
        if not role:
            try:
                role = await guild.create_role(
                    name=role_name, color=random.choice(self.role_colors),
                    mentionable=True, reason="Auto-created by Bot"
                )
                print(f"  🏷️ Created role: {role_name}")
            except Exception as e:
                print(f"  ❌ Role error: {e}")
                return None
        return role

    def _find_channel(self, guild, channel_name):
        """Find channel — handles names with spaces, emojis, mentions, IDs"""
        if not channel_name:
            return None

        name = channel_name.strip()

        # Try channel ID
        id_match = re.search(r'(\d{17,20})', name)
        if id_match:
            ch = guild.get_channel(int(id_match.group(1)))
            if ch:
                return ch

        # Try exact match (text channels use hyphens)
        clean = name.lower().replace(' ', '-')
        ch = discord.utils.get(guild.channels, name=clean)
        if ch:
            return ch

        # Try exact match with original spacing (voice channels keep spaces)
        ch = discord.utils.find(
            lambda c: c.name.lower() == name.lower(),
            guild.channels
        )
        if ch:
            return ch

        # Try without emojis
        name_no_emoji = re.sub(r'[^\w\s-]', '', name).strip().lower().replace(' ', '-')
        if name_no_emoji:
            ch = discord.utils.find(
                lambda c: re.sub(r'[^\w\s-]', '', c.name).strip().lower().replace(' ', '-') == name_no_emoji,
                guild.channels
            )
            if ch:
                return ch

        # Try partial/contains match
        ch = discord.utils.find(
            lambda c: (clean in c.name.lower().replace(' ', '-') or
                      c.name.lower().replace(' ', '-') in clean or
                      name.lower() in c.name.lower() or
                      c.name.lower() in name.lower()),
            guild.channels
        )
        if ch:
            return ch

        # Try matching without any special characters
        name_alpha = re.sub(r'[^a-z0-9]', '', name.lower())
        if len(name_alpha) >= 3:
            ch = discord.utils.find(
                lambda c: re.sub(r'[^a-z0-9]', '', c.name.lower()) == name_alpha,
                guild.channels
            )
            if ch:
                return ch

        return None

    def _find_category(self, guild, category_name):
        """Find category by name (flexible)"""
        if not category_name:
            return None

        # Exact
        cat = discord.utils.find(
            lambda c: c.name.lower() == category_name.lower() and isinstance(c, discord.CategoryChannel),
            guild.channels
        )
        if cat:
            return cat

        # Contains
        cat = discord.utils.find(
            lambda c: (category_name.lower() in c.name.lower() or c.name.lower() in category_name.lower())
                      and isinstance(c, discord.CategoryChannel),
            guild.channels
        )
        if cat:
            return cat

        # Without emojis
        clean = re.sub(r'[^\w\s]', '', category_name).strip().lower()
        if clean:
            cat = discord.utils.find(
                lambda c: re.sub(r'[^\w\s]', '', c.name).strip().lower() == clean
                          and isinstance(c, discord.CategoryChannel),
                guild.channels
            )
        return cat

    async def _find_member(self, guild, user_identifier):
        """Find member by ID, username, nickname, or display name"""
        if not user_identifier:
            return None
        
        identifier = str(user_identifier).strip().lstrip('@')
        
        # Try as user ID
        id_match = re.search(r'(\d{17,20})', identifier)
        if id_match:
            member = guild.get_member(int(id_match.group(1)))
            if member:
                return member
        
        # Try exact username match
        lower = identifier.lower()
        member = discord.utils.find(
            lambda m: m.name.lower() == lower,
            guild.members
        )
        if member:
            return member
        
        # Try display name (nickname) match
        member = discord.utils.find(
            lambda m: m.display_name.lower() == lower,
            guild.members
        )
        if member:
            return member
        
        # Try global name match
        member = discord.utils.find(
            lambda m: (m.global_name or '').lower() == lower,
            guild.members
        )
        if member:
            return member
        
        # Try partial match on any name
        member = discord.utils.find(
            lambda m: (lower in m.name.lower() or 
                      lower in m.display_name.lower() or
                      lower in (m.global_name or '').lower()),
            guild.members
        )
        if member:
            return member
        
        return None

    # ==================================================

    async def create_channel(self, guild, channel_name, channel_type,
                             requested_by=None, custom_roles=None,
                             assign_users=None, category_name=None,
                             skip_auto_roles=False) -> str:
        try:
            clean_name = channel_name.strip()[:100]
            if not clean_name:
                clean_name = "new-channel"

            print(f"\n--- Create: {clean_name} ({channel_type}) ---")

            existing = self._find_channel(guild, clean_name)
            if existing:
                return f"⚠️ Channel `{existing.name}` already exists!"

            # Determine roles
            role_names = []
            if custom_roles:
                role_names = [r for r in custom_roles if r != '@everyone']
                print(f"  Custom roles: {role_names}")
            elif not skip_auto_roles:
                auto = self._match_roles(clean_name)
                role_names = [r for r in auto if r != '@everyone']
                is_everyone = '@everyone' in auto
                if is_everyone:
                    print(f"  Auto: @everyone")
                elif role_names:
                    print(f"  Auto roles: {role_names}")

            # Overwrites
            use_ow = False
            ow = {}
            created_roles = []

            if role_names:
                ow[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                for rn in role_names:
                    role = await self._get_or_create_role(guild, rn)
                    if role:
                        ow[role] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=True,
                            read_message_history=True, connect=True,
                            speak=True, stream=True, attach_files=True,
                            embed_links=True, add_reactions=True,
                        )
                        created_roles.append(role)
                if guild.me:
                    ow[guild.me] = discord.PermissionOverwrite(
                        view_channel=True, manage_channels=True,
                        manage_permissions=True, send_messages=True,
                    )
                if created_roles:
                    use_ow = True

            # Find/create category to place channel in
            category = None
            if category_name:
                category = self._find_category(guild, category_name)
                if not category:
                    try:
                        category = await guild.create_category(name=category_name, reason="Auto-created")
                        print(f"  📁 Created category: {category_name}")
                    except:
                        pass

            # Create
            reason = f"Created by {requested_by or 'Bot'}"
            kwargs = {'name': clean_name, 'reason': reason}
            if use_ow:
                kwargs['overwrites'] = ow
            if category:
                kwargs['category'] = category

            if channel_type == 'text':
                channel = await guild.create_text_channel(**kwargs)
                icon = "💬"
            elif channel_type == 'voice':
                channel = await guild.create_voice_channel(**kwargs)
                icon = "🔊"
            else:
                return "❌ Invalid type."

            # Assign roles to users
            assigned = []
            if assign_users and created_roles:
                for uref in assign_users:
                    member = await self._find_member(guild, str(uref))
                    if member:
                        for role in created_roles:
                            try:
                                await member.add_roles(role, reason="Bot assignment")
                                assigned.append(f"{member.display_name} → `{role.name}`")
                            except:
                                pass
                    else:
                        assigned.append(f"❌ `{uref}` not found")

            # Auto-assign creator
            if requested_by and isinstance(requested_by, discord.Member) and created_roles:
                for role in created_roles:
                    if role not in requested_by.roles:
                        try:
                            await requested_by.add_roles(role, reason="Creator")
                            assigned.append(f"{requested_by.display_name} → `{role.name}` (creator)")
                        except:
                            pass

            # Response
            resp = f"✅ {icon} **{channel_type.capitalize()}** created: `{channel.name}`"
            if category:
                resp += f"\n📁 In category: **{category.name}**"
            if created_roles:
                resp += f"\n🏷️ Roles: {', '.join(f'`{r.name}`' for r in created_roles)}"
                resp += "\n🔒 **Private**"
            else:
                resp += "\n🌐 **Public**"
            if assigned:
                resp += "\n👤 " + " | ".join(assigned)
            if hasattr(requested_by, 'mention'):
                resp += f"\n📋 By: {requested_by.mention}"

            print(f"  ✅ {channel.name}")
            return resp

        except discord.Forbidden:
            return "❌ No permission!"
        except discord.HTTPException as e:
            return f"❌ Discord error: {str(e)}"
        except Exception as e:
            traceback.print_exc()
            return f"❌ Error: {str(e)}"

    async def make_channel_public(self, guild, channel_name) -> str:
        """Remove all permission overwrites — make visible to @everyone"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"

            # Reset all overwrites
            for target in list(channel.overwrites.keys()):
                await channel.set_permissions(target, overwrite=None)

            return f"🌐 `{channel.name}` is now **public** — visible to everyone!"

        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def make_channel_private(self, guild, channel_name, role_names=None) -> str:
        """Make channel private — only specific roles can see it"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"

            # Deny @everyone
            await channel.set_permissions(guild.default_role, view_channel=False)

            # Allow bot
            if guild.me:
                await channel.set_permissions(guild.me, view_channel=True,
                    manage_channels=True, send_messages=True)

            created_roles = []
            if role_names:
                for rn in role_names:
                    role = await self._get_or_create_role(guild, rn)
                    if role:
                        await channel.set_permissions(role,
                            view_channel=True, send_messages=True,
                            read_message_history=True, connect=True, speak=True)
                        created_roles.append(role.name)

            resp = f"🔒 `{channel.name}` is now **private**!"
            if created_roles:
                resp += f"\n🏷️ Access: {', '.join(f'`{r}`' for r in created_roles)}"
            else:
                resp += "\n⚠️ No roles specified — only admins and the bot can see it."
                resp += "\n💡 Use `!setrole channel-name RoleName` to grant access."
            return resp

        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def assign_role_to_user(self, guild, role_name, user_id=None, user_name=None) -> str:
        try:
            role = await self._get_or_create_role(guild, role_name)
            if not role:
                return f"❌ Can't find/create role `{role_name}`"
            member = await self._find_member(guild, str(user_id or user_name or ''))
            if not member:
                return f"❌ User `{user_id or user_name}` not found"
            await member.add_roles(role, reason="Bot assignment")
            return f"👤 `{role.name}` → **{member.display_name}**"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def delete_channel(self, guild, channel_name) -> str:
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            if isinstance(channel, discord.CategoryChannel):
                return f"⚠️ `{channel.name}` is a category. Use `!delcategory`."
            name = channel.name
            ct = "Text" if isinstance(channel, discord.TextChannel) else "Voice"
            await channel.delete(reason="Deleted by Bot")
            return f"🗑️ **{ct}** `{name}` deleted!"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def move_channel(self, guild, channel_name, category_name) -> str:
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            if isinstance(channel, discord.CategoryChannel):
                return "❌ Can't move a category!"

            cat = self._find_category(guild, category_name)
            cat_msg = ""
            if not cat:
                cat = await guild.create_category(name=category_name, reason="Auto-created")
                cat_msg = f"📁 Created: **{cat.name}**\n"

            old = channel.category.name if channel.category else "None"
            await channel.edit(category=cat, reason="Moved by Bot")
            return f"{cat_msg}📦 `{channel.name}`: **{old}** → **{cat.name}**"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def create_category(self, guild, category_name) -> str:
        try:
            existing = self._find_category(guild, category_name)
            if existing and existing.name.lower() == category_name.lower():
                return f"⏭️ Category `{category_name}` already exists!"
            cat = await guild.create_category(name=category_name, reason="Created by Bot")
            return f"📁 Category **{cat.name}** created!"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def set_channel_role(self, guild, channel_name, role_name) -> str:
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            role = await self._get_or_create_role(guild, role_name)
            if not role:
                return f"❌ Can't create role `{role_name}`!"
            await channel.set_permissions(role,
                view_channel=True, send_messages=True,
                read_message_history=True, connect=True, speak=True)
            return f"🏷️ `{role.name}` → access to `{channel.name}`!"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def rename_channel(self, guild, old_name, new_name) -> str:
        try:
            channel = self._find_channel(guild, old_name)
            if not channel:
                return f"❌ Channel `{old_name}` not found!"
            old = channel.name
            await channel.edit(name=new_name, reason="Renamed by Bot")
            return f"✏️ `{old}` → `{channel.name}`"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def list_channels(self, guild) -> str:
        try:
            lines = [f"📋 **{guild.name}**\n"]
            uncat = [c for c in guild.channels
                    if c.category is None and not isinstance(c, discord.CategoryChannel)]
            if uncat:
                lines.append("**📌 Uncategorized:**")
                for ch in sorted(uncat, key=lambda c: c.position):
                    icon = "💬" if isinstance(ch, discord.TextChannel) else "🔊" if isinstance(ch, discord.VoiceChannel) else "📢"
                    lines.append(f"  {icon} {ch.name}")
                lines.append("")
            for cat in sorted(guild.categories, key=lambda c: c.position):
                lines.append(f"**📁 {cat.name}:**")
                for ch in sorted(cat.channels, key=lambda c: c.position):
                    icon = "💬" if isinstance(ch, discord.TextChannel) else "🔊" if isinstance(ch, discord.VoiceChannel) else "📢"
                    lines.append(f"  {icon} {ch.name}")
                lines.append("")
            result = '\n'.join(lines)
            result += f"\n📊 {len(guild.text_channels)}T {len(guild.voice_channels)}V {len(guild.categories)}C"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
        
    async def create_role_with_color(self, guild, role_name, color_hex="#5865F2") -> str:
        """Create a role with a specific color"""
        try:
            existing = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
            if existing:
                return f"⏭️ Role `{role_name}` already exists!"
            
            # Color name to hex mapping
            color_map = {
                'red': '#FF0000', 'blue': '#0000FF', 'green': '#00FF00',
                'yellow': '#FFFF00', 'purple': '#800080', 'pink': '#FF69B4',
                'orange': '#FFA500', 'white': '#FFFFFF', 'black': '#000000',
                'aqua': '#00FFFF', 'aqua green': '#00CED1', 'teal': '#008080',
                'cyan': '#00FFFF', 'gold': '#FFD700', 'silver': '#C0C0C0',
                'crimson': '#DC143C', 'lime': '#00FF00', 'navy': '#000080',
                'magenta': '#FF00FF', 'coral': '#FF7F50', 'salmon': '#FA8072',
                'turquoise': '#40E0D0', 'indigo': '#4B0082', 'violet': '#EE82EE',
                'maroon': '#800000', 'olive': '#808000', 'blurple': '#5865F2',
                'discord blue': '#5865F2', 'mint': '#98FF98', 'lavender': '#E6E6FA',
                'sky blue': '#87CEEB', 'rose': '#FF007F', 'peach': '#FFCBA4',
            }
            
            # Check if it's a color name instead of hex
            color_input = str(color_hex).strip().lower()
            if color_input in color_map:
                color_hex = color_map[color_input]
            elif not color_input.startswith('#'):
                # Try partial match
                for name, hex_val in color_map.items():
                    if name in color_input or color_input in name:
                        color_hex = hex_val
                        break
            
            # Parse hex
            hex_clean = str(color_hex).strip().lstrip('#')
            try:
                color_int = int(hex_clean, 16)
                color = discord.Color(color_int)
            except:
                color = discord.Color.blurple()
                hex_clean = "5865F2"
            
            role = await guild.create_role(
                name=role_name, color=color, mentionable=True,
                reason="Created by AutoBot"
            )
            return f"🏷️ Role `{role.name}` created with color #{hex_clean}!"
        except discord.Forbidden:
            return "❌ No permission to create roles!"
        except Exception as e:
            return f"❌ Role error: {str(e)}"

    async def delete_role(self, guild, role_name) -> str:
        """Delete a role by name"""
        try:
            role = discord.utils.find(lambda r: r.name.lower() == role_name.lower().strip(), guild.roles)
            if not role:
                # Partial match
                role = discord.utils.find(lambda r: role_name.lower().strip() in r.name.lower(), guild.roles)
            if not role:
                return f"❌ Role `{role_name}` not found!"
            if role >= guild.me.top_role:
                return f"❌ Can't delete `{role.name}` — it's higher than my role!"
            if role.is_default():
                return f"❌ Can't delete @everyone!"
            name = role.name
            await role.delete(reason="Deleted by AutoBot")
            return f"🗑️ Role `{name}` deleted!"
        except discord.Forbidden:
            return "❌ No permission to delete roles!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def remove_role_from_user(self, guild, role_name, user_identifier) -> str:
        """Remove a role from a user"""
        try:
            role = discord.utils.find(lambda r: r.name.lower() == role_name.lower().strip(), guild.roles)
            if not role:
                return f"❌ Role `{role_name}` not found!"
            member = await self._find_member(guild, user_identifier)
            if not member:
                return f"❌ User `{user_identifier}` not found!"
            if role not in member.roles:
                return f"⚠️ {member.display_name} doesn't have `{role.name}`"
            await member.remove_roles(role, reason="Removed by AutoBot")
            return f"🏷️ Removed `{role.name}` from **{member.display_name}**"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def create_stage_channel(self, guild, channel_name, category_name=None) -> str:
        """Create a stage channel"""
        try:
            category = self._find_category(guild, category_name) if category_name else None
            kwargs = {'name': channel_name, 'reason': 'Created by AutoBot'}
            if category:
                kwargs['category'] = category
            channel = await guild.create_stage_channel(**kwargs)
            resp = f"✅ 📢 Stage channel created: `{channel.name}`"
            if category:
                resp += f"\n📁 In: **{category.name}**"
            return resp
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def create_forum_channel(self, guild, channel_name, category_name=None) -> str:
        """Create a forum channel"""
        try:
            category = self._find_category(guild, category_name) if category_name else None
            kwargs = {'name': channel_name, 'reason': 'Created by AutoBot'}
            if category:
                kwargs['category'] = category
            channel = await guild.create_forum(**kwargs)
            resp = f"✅ 📋 Forum channel created: `{channel.name}`"
            if category:
                resp += f"\n📁 In: **{category.name}**"
            return resp
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def set_channel_topic(self, guild, channel_name, topic) -> str:
        """Set a channel's topic/description"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            if not isinstance(channel, discord.TextChannel):
                return f"❌ `{channel.name}` is not a text channel!"
            await channel.edit(topic=topic, reason="Set by AutoBot")
            return f"📝 Topic set for `{channel.name}`: *{topic[:100]}*"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def set_slowmode(self, guild, channel_name, seconds) -> str:
        """Set slowmode delay for a channel"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            if not isinstance(channel, discord.TextChannel):
                return f"❌ Only text channels support slowmode!"
            seconds = max(0, min(21600, int(seconds)))  # 0 to 6 hours
            await channel.edit(slowmode_delay=seconds, reason="Set by AutoBot")
            if seconds == 0:
                return f"⚡ Slowmode **disabled** for `{channel.name}`"
            return f"🐌 Slowmode set to **{seconds}s** for `{channel.name}`"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def set_voice_limit(self, guild, channel_name, limit) -> str:
        """Set user limit for a voice channel"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            if not isinstance(channel, discord.VoiceChannel):
                return f"❌ `{channel.name}` is not a voice channel!"
            limit = max(0, min(99, int(limit)))  # 0 = unlimited
            await channel.edit(user_limit=limit, reason="Set by AutoBot")
            if limit == 0:
                return f"🔊 User limit **removed** for `{channel.name}`"
            return f"🔊 User limit set to **{limit}** for `{channel.name}`"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def create_event(self, guild, name, description="", channel_name=None, start_hours_from_now=1, duration_hours=1) -> str:
        """Create a scheduled event"""
        try:
            from datetime import datetime, timedelta, timezone
            start = datetime.now(timezone.utc) + timedelta(hours=float(start_hours_from_now))
            end = start + timedelta(hours=float(duration_hours))

            kwargs = {
                'name': name,
                'description': description or f"Event: {name}",
                'start_time': start,
                'end_time': end,
                'privacy_level': discord.PrivacyLevel.guild_only,
                'reason': 'Created by AutoBot',
            }

            # If voice/stage channel specified
            if channel_name:
                channel = self._find_channel(guild, channel_name)
                if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    kwargs['channel'] = channel
                    kwargs['entity_type'] = discord.EntityType.voice if isinstance(channel, discord.VoiceChannel) else discord.EntityType.stage_instance
                else:
                    kwargs['entity_type'] = discord.EntityType.external
                    kwargs['location'] = channel_name
            else:
                kwargs['entity_type'] = discord.EntityType.external
                kwargs['location'] = 'Discord Server'

            event = await guild.create_scheduled_event(**kwargs)
            return (f"🎉 Event **{event.name}** created!\n"
                    f"📅 Starts: <t:{int(start.timestamp())}:F>\n"
                    f"⏰ Duration: {duration_hours}h")
        except discord.Forbidden:
            return "❌ No permission to create events!"
        except Exception as e:
            return f"❌ Event error: {str(e)}"

    async def cancel_event(self, guild, event_name) -> str:
        """Cancel/delete a scheduled event"""
        try:
            events = await guild.fetch_scheduled_events()
            event = None
            for e in events:
                if event_name.lower() in e.name.lower():
                    event = e
                    break
            if not event:
                return f"❌ Event `{event_name}` not found!"
            name = event.name
            await event.cancel()
            return f"🗑️ Event **{name}** cancelled!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def clone_channel(self, guild, channel_name) -> str:
        """Clone/duplicate a channel"""
        try:
            channel = self._find_channel(guild, channel_name)
            if not channel:
                return f"❌ Channel `{channel_name}` not found!"
            new_channel = await channel.clone(reason="Cloned by AutoBot")
            return f"📋 Cloned `{channel.name}` → `{new_channel.name}`"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def purge_messages(self, channel, count) -> str:
        """Delete messages in bulk"""
        try:
            count = max(1, min(100, int(count)))
            deleted = await channel.purge(limit=count, reason="Purged by AutoBot")
            return f"🧹 Deleted **{len(deleted)}** messages!"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def kick_member(self, guild, user_identifier, reason="Kicked by AutoBot") -> str:
        try:
            member = await self._find_member(guild, user_identifier)
            if not member:
                return f"❌ User `{user_identifier}` not found!"
            if member == guild.me:
                return "❌ I can't kick myself!"
            if member == guild.owner:
                return "❌ Can't kick the server owner!"
            name = member.display_name
            await member.kick(reason=reason)
            return f"👢 **{name}** has been kicked! Reason: {reason}"
        except discord.Forbidden:
            return "❌ No permission to kick!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def ban_member(self, guild, user_identifier, reason="Banned by AutoBot") -> str:
        try:
            member = await self._find_member(guild, user_identifier)
            if not member:
                return f"❌ User `{user_identifier}` not found!"
            if member == guild.me:
                return "❌ I can't ban myself!"
            if member == guild.owner:
                return "❌ Can't ban the server owner!"
            name = member.display_name
            await member.ban(reason=reason)
            return f"🔨 **{name}** has been banned! Reason: {reason}"
        except discord.Forbidden:
            return "❌ No permission to ban!"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def timeout_member(self, guild, user_identifier, minutes=5, reason="Timed out by AutoBot") -> str:
        try:
            from datetime import timedelta
            member = await self._find_member(guild, user_identifier)
            if not member:
                return f"❌ User `{user_identifier}` not found!"
            minutes = max(1, min(40320, int(minutes)))  # 1 min to 28 days
            duration = timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            return f"⏰ **{member.display_name}** timed out for **{minutes} minutes**!"
        except discord.Forbidden:
            return "❌ No permission!"
        except Exception as e:
            return f"❌ Error: {str(e)}"