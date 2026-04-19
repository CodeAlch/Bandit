#!/usr/bin/env python3
"""
Voice Listener
==============
Handles voice channel operations:
- Join voice channel
- Record audio from users
- Convert speech to text (using Google Speech Recognition - FREE)
- Execute parsed voice commands

Speech-to-Text Options:
1. Google Speech Recognition (FREE, no API key needed)
2. Google Gemini (if available, for better accuracy)

# =============================================
# OPENAI WHISPER (COMMENTED OUT)
# If buyer has OpenAI key, they can uncomment
# the Whisper sections for best accuracy
# =============================================
"""

import discord
import asyncio
import os
import io
import tempfile

# Google Speech Recognition (FREE - no API key)
try:
    import speech_recognition as sr
    HAS_SPEECH = True
except ImportError:
    HAS_SPEECH = False
    print("⚠️ SpeechRecognition not installed. Run: pip install SpeechRecognition")

# =============================================
# OPENAI WHISPER (COMMENTED OUT)
# =============================================
# try:
#     from openai import OpenAI
#     OPENAI_KEY = os.getenv('OPENAI_API_KEY')
#     HAS_WHISPER = bool(OPENAI_KEY)
# except ImportError:
#     HAS_WHISPER = False
HAS_WHISPER = False  # Remove this line if uncommenting above


class VoiceListener:
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # guild_id -> session dict
        self._last_audio = {}  # guild_id -> audio bytes

        # =============================================
        # OPENAI WHISPER (COMMENTED OUT)
        # =============================================
        # if HAS_WHISPER:
        #     self.openai_client = OpenAI(api_key=OPENAI_KEY)
        #     self.stt_provider = 'whisper'
        #     print("🎤 Voice STT: OpenAI Whisper")
        if HAS_SPEECH:
            self.recognizer = sr.Recognizer()
            self.stt_provider = 'google'
            print("🎤 Voice STT: Google Speech Recognition (FREE)")
        else:
            self.stt_provider = None
            print("⚠️ Voice STT: Not available")

    def is_available(self) -> bool:
        """Check if voice listening is available"""
        return self.stt_provider is not None

    async def start_listening(self, voice_channel, text_channel, guild,
                              channel_manager, command_parser):
        """Join voice channel and start listening for commands"""

        if not self.is_available():
            return (
                "❌ **Voice commands not available!**\n"
                "Install speech recognition: `pip install SpeechRecognition`"
            )

        # Check if already listening
        if guild.id in self.active_sessions:
            return "⚠️ Already listening! Use `!stoplisten` first."

        try:
            # Connect to voice channel
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                await asyncio.sleep(1)

            voice_client = await voice_channel.connect()

            # Store session info
            self.active_sessions[guild.id] = {
                'voice_client': voice_client,
                'text_channel': text_channel,
                'channel_manager': channel_manager,
                'command_parser': command_parser,
                'listening': True,
                'voice_channel_name': voice_channel.name,
            }

            # Start listening loop in background
            asyncio.create_task(self._listening_loop(guild))

            return (
                f"🎤 **Joined `{voice_channel.name}` — Listening for commands!**\n\n"
                f"🗣️ **How to give voice commands:**\n"
                f"Start with **\"Bot\"** followed by your command:\n"
                f"```\n"
                f"\"Bot, create a text channel called gaming\"\n"
                f"\"Bot, make a voice channel named Music Room\"\n"
                f"\"Bot, delete the old-chat channel\"\n"
                f"\"Bot, move gaming to Fun category\"\n"
                f"\"Bot, rename test to production\"\n"
                f"```\n"
                f"🛑 Type `!stoplisten` to disconnect.\n\n"
                f"⚡ **STT Provider:** {self.stt_provider.upper()}\n"
                f"📝 Commands will appear in this text channel."
            )

        except discord.ClientException as e:
            return f"❌ Voice connection error: {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    async def _listening_loop(self, guild):
        """
        Main listening loop.

        NOTE: discord.py has limited voice receiving support.
        This implementation uses two approaches:

        1. discord.py sinks (if available in your version)
        2. System microphone fallback (if bot runs on your local machine)

        For production deployment, consider using:
        - py-cord (has better voice receiving with Sinks)
        - A dedicated voice processing service
        """
        session = self.active_sessions.get(guild.id)
        if not session:
            return

        text_channel = session['text_channel']

        await text_channel.send(
            "👂 **Now listening...** Speak clearly!\n"
            "💡 Recording in 6-second intervals. Speak during recording."
        )

        while session.get('listening', False):
            try:
                if not session['voice_client'].is_connected():
                    break

                # Record audio
                audio_data = await self._record_audio(session, duration=6)

                if audio_data:
                    # Convert to text
                    text = await self._speech_to_text(audio_data)

                    if text and len(text.strip()) > 2:
                        text_lower = text.lower().strip()

                        # Check for trigger words
                        triggers = [
                            'bot', 'hey bot', 'okay bot', 'ok bot',
                            'discord bot', 'automation',
                            'create', 'make', 'delete', 'remove',
                            'move', 'rename', 'change'
                        ]

                        is_command = any(text_lower.startswith(t) for t in triggers)

                        if is_command:
                            # Remove trigger word from beginning
                            clean_text = text
                            for trigger in ['hey bot', 'okay bot', 'ok bot',
                                          'discord bot', 'bot', 'automation']:
                                if text_lower.startswith(trigger):
                                    clean_text = text[len(trigger):].strip()
                                    clean_text = clean_text.lstrip(',').lstrip('.').strip()
                                    break

                            if clean_text and len(clean_text) > 2:
                                await text_channel.send(
                                    f"🎤 **Heard:** *\"{clean_text}\"*\n⏳ Processing..."
                                )

                                # Parse and execute
                                try:
                                    parsed = await session['command_parser'].parse(clean_text)

                                    result = await self._execute_parsed(
                                        parsed, guild, session
                                    )
                                    await text_channel.send(result)

                                except Exception as e:
                                    await text_channel.send(
                                        f"❌ Error processing command: {str(e)}"
                                    )

                # Brief pause between recordings
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Voice loop error: {e}")
                await asyncio.sleep(3)

        # Cleanup
        if guild.id in self.active_sessions:
            await self.stop_listening(guild)

    async def _execute_parsed(self, parsed: dict, guild, session) -> str:
        """Execute a parsed voice command"""
        cm = session['channel_manager']

        if parsed['action'] == 'create':
            return await cm.create_channel(
                guild=guild,
                channel_name=parsed.get('channel_name', 'new-channel'),
                channel_type=parsed.get('channel_type', 'text'),
                requested_by='🎤 Voice Command'
            )
        elif parsed['action'] == 'delete':
            return await cm.delete_channel(
                guild, parsed.get('channel_name', '')
            )
        elif parsed['action'] == 'move':
            return await cm.move_channel(
                guild,
                parsed.get('channel_name', ''),
                parsed.get('category_name', '')
            )
        elif parsed['action'] == 'rename':
            return await cm.rename_channel(
                guild,
                parsed.get('old_name', ''),
                parsed.get('new_name', '')
            )
        elif parsed['action'] == 'category':
            return await cm.create_category(
                guild, parsed.get('category_name', '')
            )
        elif parsed['action'] == 'setrole':
            return await cm.set_channel_role(
                guild,
                parsed.get('channel_name', ''),
                parsed.get('role_name', '')
            )
        else:
            return "🤔 Couldn't understand that voice command. Try again?"

    async def _record_audio(self, session, duration=6):
        """
        Record audio from voice channel.

        Method 1: discord.py voice receiving (limited support)
        Method 2: System microphone (works when bot runs locally)
        """

        # Method 1: Try discord.py Sink-based recording
        try:
            vc = session['voice_client']
            if hasattr(vc, 'start_recording') and hasattr(discord, 'sinks'):
                return await self._record_with_sink(vc, duration)
        except (AttributeError, NotImplementedError):
            pass

        # Method 2: System microphone (for local development)
        if HAS_SPEECH:
            return await self._record_with_microphone(duration)

        return None

    async def _record_with_sink(self, voice_client, duration):
        """Record using discord.py sinks (py-cord compatible)"""
        try:
            sink = discord.sinks.WaveSink()
            voice_client.start_recording(
                sink,
                self._sink_callback,
                voice_client.guild.id
            )

            await asyncio.sleep(duration)

            voice_client.stop_recording()
            await asyncio.sleep(0.5)

            # Get recorded audio
            audio = self._last_audio.get(voice_client.guild.id)
            self._last_audio[voice_client.guild.id] = None
            return audio

        except Exception as e:
            print(f"Sink recording error: {e}")
            return None

    async def _sink_callback(self, sink, guild_id):
        """Callback when sink recording finishes"""
        try:
            for user_id, audio_data in sink.audio_data.items():
                self._last_audio[guild_id] = audio_data.file.read()
                break
        except Exception as e:
            print(f"Sink callback error: {e}")

    async def _record_with_microphone(self, duration):
        """
        Record using system microphone.

        This works when:
        - Bot runs on YOUR computer (not a remote server)
        - You have a microphone connected
        - You're speaking near the microphone

        For remote server deployment, use sink-based recording
        or a dedicated voice service.
        """
        try:
            recognizer = sr.Recognizer()

            with sr.Microphone() as source:
                # Adjust for background noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)

                try:
                    audio = recognizer.listen(
                        source,
                        timeout=duration,
                        phrase_time_limit=duration
                    )
                    return audio.get_wav_data()
                except sr.WaitTimeoutError:
                    return None

        except OSError as e:
            # No microphone available - this is normal on servers
            if 'No Default Input Device' in str(e) or 'Invalid input' in str(e):
                pass  # Silent fail - expected on servers without mic
            else:
                print(f"Microphone error: {e}")
            return None
        except Exception as e:
            print(f"Recording error: {e}")
            return None

    async def _speech_to_text(self, audio_data) -> str:
        """Convert audio data to text"""
        if not audio_data:
            return None

        # =============================================
        # OPENAI WHISPER (COMMENTED OUT)
        # Best accuracy but costs $0.006/minute
        # =============================================
        # if HAS_WHISPER and self.stt_provider == 'whisper':
        #     try:
        #         return await self._whisper_transcribe(audio_data)
        #     except Exception as e:
        #         print(f"Whisper error: {e}")

        # Google Speech Recognition (FREE)
        if HAS_SPEECH:
            try:
                return await self._google_transcribe(audio_data)
            except Exception as e:
                print(f"Google STT error: {e}")

        return None

    # =============================================
    # OPENAI WHISPER TRANSCRIPTION (COMMENTED OUT)
    # =============================================
    # async def _whisper_transcribe(self, audio_data) -> str:
    #     """Use OpenAI Whisper for speech-to-text"""
    #     try:
    #         # Save to temp file
    #         with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    #             f.write(audio_data)
    #             temp_path = f.name
    #
    #         with open(temp_path, 'rb') as audio_file:
    #             transcript = self.openai_client.audio.transcriptions.create(
    #                 model="whisper-1",
    #                 file=audio_file
    #             )
    #
    #         # Cleanup
    #         os.unlink(temp_path)
    #
    #         text = transcript.text.strip()
    #         return text if text else None
    #
    #     except Exception as e:
    #         print(f"Whisper error: {e}")
    #         if os.path.exists(temp_path):
    #             os.unlink(temp_path)
    #         return None

    async def _google_transcribe(self, audio_data) -> str:
        """
        Use Google Speech Recognition (FREE).
        No API key needed!
        """
        try:
            recognizer = sr.Recognizer()

            # Convert raw bytes to AudioData
            audio = sr.AudioData(audio_data, sample_rate=48000, sample_width=2)

            # Recognize using Google (free)
            text = recognizer.recognize_google(audio, language='en-US')
            return text.strip() if text else None

        except sr.UnknownValueError:
            # Could not understand audio
            return None
        except sr.RequestError as e:
            print(f"Google Speech API error: {e}")
            return None

    async def stop_listening(self, guild) -> str:
        """Stop listening and disconnect from voice"""
        try:
            session = self.active_sessions.get(guild.id)

            if not session:
                return "⚠️ I'm not listening in any voice channel!"

            session['listening'] = False

            vc = session['voice_client']
            vc_name = session.get('voice_channel_name', 'Unknown')

            if vc.is_connected():
                try:
                    vc.stop_recording()
                except:
                    pass
                await vc.disconnect(force=True)

            del self.active_sessions[guild.id]

            return f"🛑 **Stopped listening** and left `{vc_name}`."

        except Exception as e:
            if guild.id in self.active_sessions:
                del self.active_sessions[guild.id]
            return f"🛑 Disconnected. (Cleanup note: {str(e)})"