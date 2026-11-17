import asyncio
import base64
import datetime
import re
import time
import requests
import io
from PyQt6.QtCore import QThread, pyqtSignal
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus
from winsdk.windows.storage.streams import DataReader
from winsdk.windows.security.cryptography import CryptographicBuffer
from PIL import Image
from media_seek import TrackTimeline

class MediaMonitor(QThread):
    media_updated = pyqtSignal(str, str, str, str)                                     
    artwork_updated = pyqtSignal(bytes)
    timeline_updated = pyqtSignal(object)
    seek_completed = pyqtSignal(int, bool)
    source_updated = pyqtSignal(str)
    lyrics_updated = pyqtSignal(str)                     

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.loop = None
        self.manager = None
        self.current_session = None
        self.lyrics = []                                
        self.last_lyric_sent = ""
        self.current_title = ""
        self.current_artist = ""
        self.last_state = ""
        self.priority = 'Auto'
        self.lyrics_enabled = True
        self.source_id = ''
        self.lyric_track = None
        self.track_id = 0
        self.published_timeline = None
        self.artwork = b''
        self.album_accent = '#000000'

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.monitor_media())
        except Exception as e:
            print("MediaMonitor error:", e)

    async def monitor_media(self):
        self.manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        
        next_refresh = 0
        while self._is_running:
            if time.monotonic() >= next_refresh:
                self.select_session()
                await self.update_media_info()
                self.ensure_lyrics()
                self.publish_timeline()
                next_refresh = time.monotonic() + 1
            await self.check_lyric_sync()
            await asyncio.sleep(0.08 if self.lyrics else 0.25)

    async def check_lyric_sync(self):
        if not self.lyrics_enabled:
            if self.lyrics:
                self.lyrics = []
                self.lyrics_updated.emit("")
            return
        if not self.current_session or not self.lyrics:
            return
        
        try:
                                                    
            timeline = await self.loop.run_in_executor(None, self.get_safe_timeline)
            if not timeline:
                return
            
                                          
            now = datetime.datetime.now(datetime.timezone.utc)
            
                                           
            try:
                last_updated = timeline.last_updated_time
                pos_base = timeline.position.total_seconds()
            except:
                return

            delta = (now - last_updated).total_seconds()
            
                                                                            
            pos_sec = pos_base + (max(0, delta) if self.last_state == "Playing" else 0)
            
                                   
            current_line = ""
            for ts, text in self.lyrics:
                if pos_sec >= ts:
                    current_line = text
                else:
                    break
            
            if current_line != self.last_lyric_sent:
                self.last_lyric_sent = current_line
                self.lyrics_updated.emit(current_line)
        except:
            pass

    def get_safe_timeline(self):
        try:
            if self.current_session:
                return self.current_session.get_timeline_properties()
        except:
            pass
        return None

    def select_session(self):
        try:
            current = self.manager.get_current_session()
            current_id = current.source_app_user_model_id if current else ""
            candidates = []
            for session in self.manager.get_sessions():
                try:
                    source = session.source_app_user_model_id
                    status = session.get_playback_info().playback_status
                    if status.name not in ("PLAYING", "PAUSED"):
                        continue
                    preferred = self.priority == "Spotify first" and "spotify" in source.lower()
                    candidates.append(((preferred, status.name == "PLAYING", source == current_id), session, source))
                except Exception:
                    continue
            _, self.current_session, source = max(candidates, key=lambda item: item[0], default=(None, None, ""))
        except Exception:
            self.current_session, source = None, ""
        if source != self.source_id:
            self.source_id = source
            self.reset_timeline()
            self.last_state = ""
            self.current_title = ""
            self.current_artist = ""
            self.lyric_track = None
            self.source_updated.emit(source)

    async def update_media_info(self):
        try:
            if not self.current_session:
                if self.last_state != "Idle":
                    self.last_state = "Idle"
                    self.lyrics = []
                    self.lyrics_updated.emit("")
                    self.media_updated.emit("Idle", "", "", "#000000")
                return

            try:
                                                     
                info = await self.loop.run_in_executor(None, self.get_safe_playback_info)
            except Exception as e:
                                                                                
                self.current_session = None
                self.media_updated.emit("Idle", "", "", "#000000")
                return

            if not info:
                self.current_session = None
                self.media_updated.emit("Idle", "", "", "#000000")
                return

            status = info.playback_status
            
            state_str = "Idle"
            if status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                state_str = "Playing"
            elif status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
                state_str = "Paused"

            if state_str in ("Playing", "Paused"):
                try:
                    props = await self.current_session.try_get_media_properties_async()
                except Exception:
                    return
                title = (props.title if props else "") or "Unknown Title"
                artist = (props.artist if props else "") or ""
                changed = (title, artist) != (self.current_title, self.current_artist)
                if changed:
                    self.current_title, self.current_artist = title, artist
                    self.reset_timeline()
                    self.artwork, self.album_accent = b"", "#000000"
                    self.lyrics = []
                    self.last_lyric_sent = ""
                    self.lyrics_updated.emit("")
                if changed or state_str != self.last_state:
                    self.last_state = state_str
                    self.media_updated.emit(state_str, title, artist, self.album_accent)
                if changed or (not self.artwork and title != "Unknown Title"):
                    await self.update_artwork(props)
            else:
                if self.last_state != "Idle":
                    self.current_title = ""
                    self.current_artist = ""
                    self.last_state = "Idle"
                    self.lyrics = []
                    self.media_updated.emit("Idle", "", "", "#000000")
        except Exception as e:
            if "remote procedure call failed" in str(e).lower() or "0x800706be" in str(e).lower():
                self.current_session = None
            else:
                print(f"Update media info error: {e}")

    def reset_timeline(self):
        self.track_id += 1
        if self.published_timeline is not None:
            self.published_timeline = None
            self.timeline_updated.emit(None)

    def get_timeline(self, session):
        if session is None or self.last_state not in ("Playing", "Paused"):
            return None
        try:
            info = session.get_playback_info()
            timeline = session.get_timeline_properties()
            start = round(timeline.start_time.total_seconds() * 1000)
            end = round(timeline.end_time.total_seconds() * 1000)
            if not 0 <= start < end <= 2147483647:
                return None
            earliest = max(start, round(timeline.min_seek_time.total_seconds() * 1000))
            latest = min(end, round(timeline.max_seek_time.total_seconds() * 1000))
            position = timeline.position.total_seconds()
            if info.playback_status.name == "PLAYING":
                age = datetime.datetime.now(datetime.timezone.utc) - timeline.last_updated_time
                rate = info.playback_rate if info.playback_rate is not None else 1.0
                position += max(0.0, age.total_seconds()) * rate
            position = max(start, min(end, round(position * 1000)))
            return TrackTimeline(self.track_id, start, end, position, earliest, latest,
                                 info.controls.is_playback_position_enabled and earliest < latest)
        except Exception:
            return None

    def publish_timeline(self):
        snapshot = self.get_timeline(self.current_session)
        if snapshot != self.published_timeline:
            self.published_timeline = snapshot
            self.timeline_updated.emit(snapshot)

    def seek(self, track_id, position_ms):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.seek_to(track_id, position_ms), self.loop)
        else:
            self.seek_completed.emit(track_id, False)

    async def seek_to(self, track_id, position_ms):
        success = False
        session = self.current_session
        try:
            if session is None or track_id != self.track_id:
                return
            properties = await session.try_get_media_properties_async()
            if (track_id != self.track_id or not properties
                    or (properties.title or "Unknown Title", properties.artist or "") !=
                       (self.current_title, self.current_artist)):
                return
            timeline = self.get_timeline(session)
            if timeline and timeline.seek_enabled:
                target_ms = min(timeline.seek_to_ms, max(timeline.seek_from_ms, position_ms))
                success = await session.try_change_playback_position_async(target_ms * 10_000)
        except Exception as error:
            print(f"Seek unavailable: {error}")
        finally:
            self.seek_completed.emit(track_id, success)

    def get_safe_playback_info(self):
        try:
            if self.current_session:
                return self.current_session.get_playback_info()
        except:
            pass
        return None

    async def update_artwork(self, props):
        if not props or not props.thumbnail:
            return
        try:
            stream = await props.thumbnail.open_read_async()
            if not 0 < stream.size <= 8 * 1024 * 1024:
                return
            reader = DataReader(stream.get_input_stream_at(0))
            try:
                size = await reader.load_async(stream.size)
                raw = base64.b64decode(CryptographicBuffer.encode_to_base64_string(reader.read_buffer(size)))
                with Image.open(io.BytesIO(raw)) as image:
                    cover = image.convert("RGB")
                    cover.thumbnail((160, 160))
                    output = io.BytesIO()
                    cover.save(output, format="PNG")
                    rgb = cover.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
                self.artwork = output.getvalue()
                self.album_accent = "#{:02x}{:02x}{:02x}".format(*rgb)
                self.artwork_updated.emit(self.artwork)
                self.media_updated.emit(self.last_state, self.current_title, self.current_artist, self.album_accent)
            finally:
                reader.close()
                stream.close()
        except Exception as error:
            print(f"Artwork unavailable: {error}")

    def ensure_lyrics(self):
        if not self.lyrics_enabled:
            self.lyric_track = None
            self.last_lyric_sent = ""
            return
        if self.last_state not in ("Playing", "Paused") or self.current_title == "Unknown Title":
            self.lyric_track = None
            return
        track = (self.source_id, self.current_artist, self.current_title)
        if track != self.lyric_track:
            self.lyric_track = track
            asyncio.create_task(self.fetch_lyrics(track))

    async def fetch_lyrics(self, track):
        _, artist, title = track
        if not artist or not title:
            return
            
        def do_fetch():
            try:
                url = "https://lrclib.net/api/get"
                params = {"artist_name": artist, "track_name": title}
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    lrc = data.get("syncedLyrics")
                    if lrc:
                        return self.parse_lrc(lrc)
                return []
            except Exception as e:
                print(f"Lyric fetch error: {e}")
                return []

        lyrics = await asyncio.get_event_loop().run_in_executor(None, do_fetch)
        if lyrics and self.lyrics_enabled and self.lyric_track == track:
            self.lyrics = lyrics
            await self.check_lyric_sync()

    def parse_lrc(self, lrc_text):
        lyrics = []
        for line in lrc_text.splitlines():
                                                      
            match = re.search(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)', line)
            if match:
                m, s, text = match.groups()
                timestamp = int(m) * 60 + float(s)
                lyrics.append((timestamp, text.strip()))
        return sorted(lyrics, key=lambda x: x[0])

                     
    def toggle_play_pause(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_toggle(), self.loop)

    async def _do_toggle(self):
        await self.current_session.try_toggle_play_pause_async()

    def next_track(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_next(), self.loop)

    async def _do_next(self):
        await self.current_session.try_skip_next_async()

    def prev_track(self):
        if self.current_session and self.loop:
            asyncio.run_coroutine_threadsafe(self._do_prev(), self.loop)

    async def _do_prev(self):
        await self.current_session.try_skip_previous_async()

    def stop(self):
        self._is_running = False
        self.wait()
