# VoiceBot WebSockets

Real-time voice assistant pipeline built with FastAPI, Twilio Media Streams, Deepgram STT, OpenAI chat completion streaming, and ElevenLabs TTS.

## Project Analysis

This project receives live call audio from Twilio over WebSocket, transcribes speech with Deepgram, generates a response using OpenAI, converts that response to speech via ElevenLabs, and streams audio back to the call.

### Current Architecture

1. Twilio call is initiated from `POST /call` in `application.py`.
2. Twilio streams call audio to `wss://<your-host>/audio`.
3. `Websocket()` in `utils/chatbot.py`:
   - Buffers incoming mu-law audio chunks from Twilio.
   - Sends chunks to Deepgram live transcription WebSocket.
   - On final transcript, writes user message to `responses.json`.
   - Optionally interrupts currently playing audio (`clear` event).
   - Sends transcript to OpenAI (`gpt-4o-mini`) with conversation history.
   - Streams model output to ElevenLabs TTS.
   - Sends generated audio back to Twilio as media frames.
4. Assistant/user messages are persisted by session ID in `responses.json`.

### Key Files

- `application.py`: FastAPI app, `/audio` WebSocket, `/call` trigger endpoint.
- `utils/chatbot.py`: Deepgram + OpenAI + ElevenLabs streaming pipeline.
- `utils/prompt.py`: System prompt used for assistant behavior.
- `responses.json`: Session conversation history store.

### Notes About Current Codebase

- `application.py` currently includes Twilio credentials and phone numbers directly in code. Move these to environment variables before production use.
- `spacy` is imported in `utils/chatbot.py` but not actively used.
- `responses.json` can grow over time; consider rotation/cleanup for long-term deployment.

## Setup Guide

### 1. Prerequisites

- Python 3.10+
- Twilio account with Voice enabled number
- Deepgram API key
- OpenAI API key
- ElevenLabs API key
- Public HTTPS/WSS URL for local testing (for example: ngrok)

### 2. Clone And Open

```powershell
git clone <your-repo-url>
cd Websockets
```

### 3. Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```powershell
pip install fastapi uvicorn python-dotenv websockets openai twilio spacy
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
API_KEY=your_elevenlabs_api_key
DEEPGRAM_KEY=your_deepgram_api_key

# Recommended additional vars (move hardcoded values from application.py)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_NUMBER=+1xxxxxxxxxx
TO_NUMBER=+xxxxxxxxxxx
PUBLIC_WSS_URL=wss://your-public-domain/audio
```

### 6. Start Server

```powershell
uvicorn application:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Expose Local Server (If Running Locally)

Example with ngrok:

```powershell
ngrok http 8000
```

Use the generated HTTPS/WSS host in your Twilio stream URL.

### 8. Trigger A Call

Send a request to initiate outbound call:

```powershell
curl -X POST http://127.0.0.1:8000/call
```

If everything is configured correctly, Twilio starts a call and streams audio to `/audio`.

## API Endpoints

- `POST /call`: Starts an outbound Twilio call.
- `WS /audio`: Handles real-time bidirectional audio stream.

## How Session Memory Works

- A `sessionid` is attached in Twilio `<Parameter>` during call creation.
- Conversation turns are appended to `responses.json` under that session ID.
- On each new user transcript, context is loaded and reused for model continuity.

## Troubleshooting

- No transcription:
  - Verify `DEEPGRAM_KEY`.
  - Ensure audio format is `mulaw`, 8000 Hz as expected by Deepgram URL.
- No model response:
  - Verify `OPENAI_API_KEY`.
  - Check network access to OpenAI API.
- No audio playback:
  - Verify `API_KEY` (ElevenLabs).
  - Confirm stream payloads are base64 encoded mu-law for Twilio media events.
- Twilio does not connect to WebSocket:
  - Ensure public WSS URL is reachable.
  - Confirm endpoint path is `/audio`.

## Recommended Next Improvements

- Move all secrets/config to `.env` and remove hardcoded credentials.
- Add `requirements.txt` for reproducible installs.
- Add logging and structured error handling for production.
- Add file locking or database persistence instead of plain `responses.json` for concurrency safety.
