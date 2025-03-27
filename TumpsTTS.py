import asyncio
import json
import threading
import queue
import websockets
import io

try:
    import pygame
except ImportError:
    print("pygame not installed. Audio playback will not be available.")
    pygame = None

class TumpsTTS:
    def __init__(self, server_url):
        self.server_url = server_url
        self.websocket = None
        self.audio_queue = queue.Queue()
        self.client_thread = None
        self.client_running = False
        self.loop = None
        self.connected = threading.Event()
        
    def start(self):
        if self.client_running:
            print("Client is already running.")
            return
            
        self.client_running = True
        self.client_thread = threading.Thread(target=self._run_client)
        self.client_thread.daemon = True
        self.client_thread.start()
        print(f"Client started, connecting to {self.server_url}")
    
    def start_runner(self):
        if self.client_running:
            print("Client is already running.")
            return
            
        self.client_running = True
        self.client_thread = threading.Thread(target=self._run_client)
        self.client_thread.daemon = True
        self.client_thread.start()
        print(f"Client started, connecting to {self.server_url}")
        threading.Thread(target=self._run_audio, daemon=True).start()
        
    def _run_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.loop.run_until_complete(self._connect())
        self.loop.run_forever()
        
    async def _connect(self):
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"Connected to {self.server_url}")
            self.connected.set()
            
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.connected.clear()
            await asyncio.sleep(5)
            asyncio.create_task(self._connect())
            
    async def _listen_for_messages(self):
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except Exception as e:
            print(f"Error in message listener: {e}")
            self.connected.clear()
            await self._connect()
            
    async def _process_message(self, message):
        try:
            if isinstance(message, str):
                data = json.loads(message)
                if 'audio' in data:
                    audio_data = data['audio']
                    if isinstance(audio_data, str):
                        import base64
                        audio_data = base64.b64decode(audio_data)
                    self.audio_queue.put(audio_data)
                    print(f"Received audio for {data.get('character_name', 'unknown')}, sequence: {data.get('sequence_id', 'unknown')}")
            else:
                self.audio_queue.put(message)
                    
        except json.JSONDecodeError:
            self.audio_queue.put(message)
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def request_audio(self, text, voice, name="user"):
        if not self.connected.is_set():
            print("Not connected to server. Call start() and wait for connection.")
            return False
            
        message = {
            "type": "audio_only",
            "text": text,
            "voice": voice,
            "name": name
        }
        def send_in_loop():
            asyncio.create_task(self._send_message(json.dumps(message)))
        self.loop.call_soon_threadsafe(send_in_loop)
        return True
    
    async def _send_message(self, message):
        if self.websocket:
            try:
                message_bytes = message.encode('utf-8')
                await self.websocket.send(message_bytes)
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            print("WebSocket does not exist. Cannot send message.")
    
    def has_audio(self):
        return not self.audio_queue.empty()
    
    def get_audio(self):
        if self.has_audio():
            return self.audio_queue.get()
        return None
    
    # blocking play
    def play_audio(self):
        if pygame is None:
            print("pygame is not installed. Cannot play audio.")
            return
            
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        while self.has_audio():
            audio_data = self.get_audio()
            
            try:
                audio_stream = io.BytesIO(audio_data)
                pygame.mixer.music.load(audio_stream)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            except Exception as e:
                print(f"Error playing audio: {e}")
    
    # continous play just need to queue
    def _run_audio(self):
        if pygame is None:
            print("pygame is not installed. Cannot play audio.")
            return
            
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        while self.client_running:
            try:
                audio_data = self.audio_queue.get(timeout=1.0)
                try:
                    audio_stream = io.BytesIO(audio_data)
                    pygame.mixer.music.load(audio_stream)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                except Exception as e:
                    print(f"Error playing audio: {e}")
                self.audio_queue.task_done()
            except queue.Empty:
                pass
    
    def stop(self):
        if not self.client_running:
            print("Client is not running.")
            return
            
        self.client_running = False
        
        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(), 
                self.loop
            )
            
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.client_thread:
            self.client_thread.join(timeout=1.0)
            print("Client stopped.")