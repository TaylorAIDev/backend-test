from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form
from typing import List
import uvicorn
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import openai
from openai.error import OpenAIError
# local import
from makepdf import generate_pdf

load_dotenv()

openai.api_key = os.getenv("OPEN_AI_API_KEY")
app = FastAPI()
origins = [
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DataPayload(BaseModel):
    data: object


#generate streaming data from openai by stream
async def write_data_stream(payload: DataPayload):
    messages = payload.data
    try:
        out_prompt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            #max_tokens=1024,
            temperature= 0.7,
            stream= True
        )

        for chunk in out_prompt:
            content =chunk.choices[0]['delta'].get('content','')
            if content:
                yield content
    except OpenAIError as e:
       return
    
@app.post("/write", response_model_exclude_unset=True)
async def gpt_writer(payload: DataPayload):
    assistant_response = write_data_stream(payload)
    return StreamingResponse(assistant_response, media_type='text/event-stream')

@app.post('/getImage')
async def generate_image_from_prompt(data: DataPayload):
    #get summarize text from chatgpt
    messages = []
    messages.append({'role': 'assistant', 'content': data.data})
    messages.append({'role': 'user', 'content': 'Please Summarize your word less than 15 words'})
    print(messages)
    try:
        out_prompt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )
    except OpenAIError as e:
       return
    
    #request parameters
    prompt = str(out_prompt.choices[0].message["content"]).strip()
    # midjourney_api_key = os.getenv("MidJOURNEY_API_KEY")  # Replace with your Midjourney API key
    # url = "https://api.thenextleg.io/v2/imagine"
    # payload = json.dumps({
    #     "msg": prompt,
    #     "ref": "",
    #     "webhookOverride": "", 
    #     "ignorePrefilter": "false"
    # })
    # headers = {
    #     'Authorization': 'Bearer '+ midjourney_api_key,
    #     'Content-Type': 'application/json'
    # }

    # # return generated messageid from midjourney
    # response = requests.request("POST", url, headers=headers, data=payload)
    # messageId = json.loads(response.text)['messageId']

    # #get generated image url
    # getimage_url = 'https://api.thenextleg.io/v2/message/'+ messageId + '?expireMins=3'
    # getimage_headers = {
    #     'Authorization': 'Bearer '+ midjourney_api_key,    
    # }
    # getimage_response = requests.get(getimage_url, headers=getimage_headers)
    # getimage_response_obj = json.loads(getimage_response.text)
    # print(getimage_response_obj)
    # while getimage_response_obj['progress'] < 100:
    #     time.sleep(1)  # Wait for 1 second before checking again

    #     # Send another GET request to fetch the updated progress
    #     getimage_response = requests.get(getimage_url, headers=getimage_headers)
    #     getimage_response_obj = getimage_response.json()
    # if getimage_response_obj['progress'] == 100:
    #     return {
    #         'message': getimage_response_obj['response']['imageUrls'][0],
    #         'status': 'success'
    #     }
    
    # return generated messageid from dall-e
    try:
        imageFromDallE = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512",
        )
        print(imageFromDallE)
        return{
            'message': imageFromDallE["data"][0]["url"],
            'status': 'success'
        }
    except OpenAIError as e:
       return {
           'message': e,
           'status': 'error'
       }

@app.post('/savePdf')
async def save_to_pdf(data: DataPayload):
    generate_pdf(data.data)

if __name__ == "__main__":
    uvicorn.run('main:app', host='127.0.0.1')
