from fastapi import FastAPI, WebSocket,Request
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from utils.chatbot import Websocket
import uuid
import asyncio
import websockets
import os
import json
import base64
###
# Twilio credentials
ACCOUNT_SID = "AC5af0bfd700ba5ea81b1756d0af4ac2bb"
AUTH_TOKEN = "14e4cdf0a537f28b982da8e66f84ce06"
TWILIO_NUMBER = "+16573771755"
TO_NUMBER = "+923456332300"
###

load_dotenv

DEEPGRAM_KEY=os.getenv('DEEPGRAM_KEY')

app = FastAPI()

# Enable CORS for all origins (*)###
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Change this for security)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)





@app.websocket('/audio')
async def websocket_endpont(websocket: WebSocket):
    await websocket.accept() #to accept the connection
    await Websocket(websocket)
    


@app.post('/call')
def call():
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    sessionid= str(uuid.uuid4())
    # url=f"wss://a865-2407-d000-1a-10fe-dcf6-e3a6-dcd3-7671.ngrok-free.app/audio?session_id={sessionid}"
    twiml_response = f"""<Response>\
<Connect>\
<Stream url='wss://89d8-103-137-24-30.ngrok-free.app/audio'>\
<Parameter name="sessionid" value="{sessionid}" />\
</Stream>\
</Connect>\
</Response>"""
    #####
    # response = VoiceResponse()
    # connect = response.connect()
    # connect.stream(url="wss://c912-2407-d000-1a-d22f-4497-cb3e-3653-bd04.ngrok-free.app/audio")

    call = client.calls.create(
        to=TO_NUMBER,
        from_=TWILIO_NUMBER,
        twiml=twiml_response
    )

    print(f"Call initiated: {call.sid}")
    return {"status": "Call initiated", "call_sid": call.sid}







