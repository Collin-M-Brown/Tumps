# %%

import os
from dotenv import load_dotenv
from TumpsTTS import TumpsTTS
import time
import threading

load_dotenv()
endpoint = os.environ.get('NAVI_BRAIN')
password = os.environ.get('NAVI_SERVER_PASSWORD')
tts = TumpsTTS(f"{endpoint}?server_password={password}")

# non threading start for if you want to use it manually
# tts.start() 
# tts.has_audio()
# tts.get_audio()

# auto runner, just need to put in audio and voice and it will play but if you are using audio to do lip sync then you might want to use the normal start and then use get audio
tts.start_runner() 
# tts.request_audio(text, voice) and it will play without blocking

while not tts.connected.is_set():
    time.sleep(0.01)

# %%

start_time = time.time()
tts.request_audio("This is a test message", "Navi") # Can  you Navi, Tatl
print(f"time taken to convert text to audio: {time.time() - start_time:.4f} ")

start_time = time.time()
tts.request_audio("Blazingly fast tumps tumps tatl", "Tatl")
print(f"time taken to convert text to audio: {time.time() - start_time:.4f} ")


# %%
