from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils.prompt import prompt
import websockets
import json
import base64
import asyncio
import os
import spacy 


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("API_KEY")
print (ELEVENLABS_API_KEY)
DEEPGRAM_KEY=os.getenv('DEEPGRAM_KEY')
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
BUFFER_SIZE=4
VOICE_ID =  "EXAVITQu4vr4xnSDxMaL"


import json
import os

import json
import os

def append_response_to_json( key, response):
    data = {}

    # Create the file if it doesn't exist
    if not os.path.exists('responses.json'):
        with open('responses.json', 'w') as file:
            json.dump({}, file)

    # Load existing data
    with open('responses.json', 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            pass  # File is empty or not valid JSON

    # Initialize the list if the key doesn't exist
    if key not in data:
        data[key] = []

    # Append the response to the key's list
    data[key].append(response)

    # Write the updated data back to the file
    with open('responses.json', 'w') as file:
        json.dump(data, file, indent=4)

    print(f"Appended response to key '{key}' in responses.json")


#Interrupt handling 
async def interrupt_handler(websocket, streamsid):
    interrupt= { 
            "event": "clear",
            "streamSid": streamsid,
            }
    await websocket.send_text(json.dumps(interrupt))
    print("Interrupted the streamsid")



async def text_to_speech_input_streaming(
        stream_sid, voice_id, text_iterator, websocket1
        ):
    """Stream text to the Eleven Labs text-to-speech service."""
    # Define the URI for the websocket connection
    print("In the text to speech function")
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-\
input?model_id=eleven_turbo_v2&output_format=ulaw_8000"
    # Connect to the websocket
    async with websockets.connect(uri) as websocket:
        # Send initial configuration to the TTS service
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 1, "similarity_boost": 0.8},
            "xi_api_key": ELEVENLABS_API_KEY,
        }))
        # Define a function to listen for audio chunks from the TTS service
        async def listen():
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    # print(data)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        break
                except Exception as e:
                    print(f"Eleven labs listening error: {e}")
                    break
        # Iterate over text chunks and send to the TTS service
        async for chunk in text_chunker(text_iterator):
            await websocket.send(
                json.dumps(
                    {"text": chunk, "try_trigger_generation": True}
                )
            )
        # Signal the end of the text
        await websocket.send(json.dumps({"text": ""}))
        # Listen for audio chunks and send them to the WebSocket client
        async for chunk in listen():
            # Encode the audio chunk as base64
            base64_encoded = base64.b64encode(chunk).decode("utf-8")
            # Prepare the media data to send to the WebSocket client
            mediadata = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": base64_encoded}
            }
            # Send the media data to the WebSocket client
            await websocket1.send_text(json.dumps(mediadata))
            
            


async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""
    async for text in chunks:
        if not text:
            continue
        if buffer.endswith(splitters):
            yield buffer + " "
            buffer = text
        elif text.startswith(splitters):
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text
    if buffer:
        yield buffer + " "

async def chat_completion(query,stream_sid, websocket1, sessionid):
    """Retrieve text from OpenAI and pass it to the text-to-speech function."""
    print("In the chatbot function")
    # Read the JSON file
    with open('responses.json', 'r') as file:
        data = json.load(file)
    
    # Return the list of messages for the given sessionid or an empty list
    messages=data.get(sessionid, [])
    system_prompt={"role": "system", "content": prompt}
    
    messages.insert(0,system_prompt)
    messages.append({"role": "user", "content": query})
    response = await client.chat.completions.create(
        model='gpt-4o-mini', 
        messages=messages,
    temperature=1, stream=True)

    final_message=""

    async def text_iterator():
        # print("In the text iterator")
        buffer=[]
        nonlocal final_message
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                buffer.append(delta.content)
                
            if len(buffer)>=BUFFER_SIZE:
                final_message+= ''.join(buffer)
                yield ''.join(buffer)
                buffer=[]
            #print("in this loop")
        if buffer:
            final_message+= ''.join(buffer)
            
            append_response_to_json(sessionid, {"role": "assistant", "content": final_message})
            final_message=""
            print("Chat completion done from the text iterator") 
            yield ''.join(buffer)

        #if the buffer is an exact multiple of 4!
        
        elif response:
            final_message+= ''.join(buffer)
            append_response_to_json(sessionid, {"role": "assistant", "content": final_message})
            final_message=""
            print("Chat completion done from the text iterator") 
            yield final_message
            
        
    await text_to_speech_input_streaming(
                    stream_sid, VOICE_ID, text_iterator(), websocket1
                )
     # Pass text_iterator to text_chunker
    
   
    return 'Success'



buffer=[]

def deepgram_connect():
    print('Deepgram connection started')
    extra_headers = {
		'Authorization': f'Token {DEEPGRAM_KEY}'
	}
    print(extra_headers['Authorization'])
    deepgram_ws = websockets.connect('wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&model=nova-2-general&version=latest&language=en-US&punctuate=true&endpointing=1000&interim_results=true', extra_headers = extra_headers)

    return deepgram_ws


async def Websocket(websocket):
    # await websocket.accept() #to accept the connection
    print("Connection accepted")
    audio_queue = asyncio.Queue()
    streamsid=""
    sessionid=""

    try:
        async with deepgram_connect() as deepgram_ws:


            async def deepgram_sender(deepgram_ws):
                print('deepgram_sender started')
                try:
                    while True:
                        chunk = await audio_queue.get()
                        await deepgram_ws.send(chunk)
                except Exception as e:
                    print(f'Deepgram sender error occured {str(e)}')

            # async def deepgram_receiver(deepgram_ws):
            #     print('deepgram_receiver started')
            #     query=""
            #     last_transcript = ""
            #     async for message in deepgram_ws:
            #         data=json.loads(message)
            #         # print(data)
            #         ans=data['channel']['alternatives'][0]['transcript']
                    
            #         if ans!="" and ans!=last_transcript:
            #             query+=ans
            #             last_transcript=query
            #             if data['is_final'] :
            #                 print(f"Deepgram message received: {query}")
            #                 query=""

            async def deepgram_receiver(deepgram_ws):
                nonlocal streamsid
                print('deepgram_receiver started')
                query = ""
                last_transcript = ""

                async for message in deepgram_ws:
                    data = json.loads(message)

                    # Check if transcript is present
                    if 'channel' in data and 'alternatives' in data['channel']:
                        alternatives = data['channel']['alternatives']
                        if alternatives and 'transcript' in alternatives[0]:
                            transcript = alternatives[0]['transcript']

                            # Only process if it's final and not already processed
                            if data.get('is_final') and transcript and transcript != last_transcript:
                                query += " " + transcript
                                print(f"Deepgram message received: {query.strip()}")
                                last_transcript = transcript  # Update last transcript
                                #save our response in the json file
                                response={"role": "user", "content": query.strip()}
                                append_response_to_json(sessionid, response)
                                
                                text= query.strip()
                                text= text.split()
                                
                                print(text)
                                if len(text)>2:
                                    await interrupt_handler(websocket, streamsid)
                                #to send our query to openai
                                ans= await chat_completion(query.strip(), streamsid, websocket,sessionid)
                                print(ans)
                                
                                query = ""  # Reset after processing final result

                    

                    # print(f"Deepgram message received {ans}")

                
            async def client_reciever(client_ws):
                nonlocal streamsid
                nonlocal sessionid
                print('client_reciever started')
                try:
                    BUFFER_SIZE = 40 * 160
                    buffer=bytearray(b'')
                    async for message in client_ws.iter_text():
                        data=json.loads(message)
                        # print(data)
                        if data['event']=='connected':
                            print('Connection has started')
                            
                            continue
                        if data['event']=='start':
                            print(data)
                            streamsid=data['start']['streamSid']
                            if 'customParameters' in data['start']:
                                sessionid=data['start']['customParameters']['sessionid']
                            print("Data transfer has begun")

                        if data['event']=='media':
                            # print('i am in media')
                            # print(data)
                            media=data['media']
                            chunk = base64.b64decode(media['payload'])
                            # print('i have collected the chunk')
                            buffer.extend(chunk)
                        if data['event']=='stop':
                            print("Connection stopped")
                            break

                        if len(buffer)>=BUFFER_SIZE:
                            audio_queue.put_nowait(buffer)
                            buffer=bytearray(b'')
                    
                    #Signal deepgram to send reaming mssges incase of connection close
                    audio_queue.put_nowait(b'')
                    print("Connection has been closed ")
                except Exception as e:
                    print(f"Client Exception has Occured {str(e)}")

            await asyncio.wait([
			asyncio.ensure_future(deepgram_sender(deepgram_ws)),
			asyncio.ensure_future(deepgram_receiver(deepgram_ws)),
			asyncio.ensure_future(client_reciever(websocket))
		    ])
            await websocket.close()

		    

    
             
    except Exception as e:
        print(f'Connection Closed {e}')
    
    finally:
        await websocket.close()



