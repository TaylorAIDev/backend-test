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
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import openai
from openai.error import OpenAIError
import io
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import Image
from  reportlab.platypus.tableofcontents import TableOfContents
from  reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from  reportlab.platypus.frames import Frame


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

class MyDocTemplate(BaseDocTemplate):
     def __init__(self, filename, **kw):
         self.allowSplitting = 0
         super().__init__(filename, **kw)
         template = PageTemplate('normal', [Frame(0.75*inch, 1*inch, letter[0]-1.5*inch, letter[1]-2*inch, id='F1')], pagesize=letter)
         self.addPageTemplates(template)

     def afterFlowable(self, flowable):
         "Registers TOC entries."
         if flowable.__class__.__name__ == 'Paragraph':
             text = flowable.getPlainText()
             style = flowable.style.name
            #  if style == 'Heading1':
            #      self.notify('TOCEntry', (0, text, self.page))
             if style == 'Heading2':
                 self.notify('TOCEntry', (1, text, self.page))


centered = ParagraphStyle(
    name = 'centered',
    fontSize = 16,
    leading = 26,
    alignment = 1,
    spaceAfter = 20,
    leftIndent = 0.75*inch,
    rightIndent = 0.75*inch
    )
h1 = ParagraphStyle(
    name = 'Heading1',
    fontSize = 20,
    leading = 30,
    spaceBefore = 30,
    alignment = 1,
    leftIndent = 0.75*inch,
    rightIndent = 0.75*inch
    )
h2 = ParagraphStyle(
    name = 'Heading2',
    fontSize = 16,
    leading = 26,
    alignment = 1,
    spaceBefore = 20,
    spaceAfter = 15,
    leftIndent = 0.75*inch,
    rightIndent = 0.75*inch
)
para_style = ParagraphStyle(
    name = 'Para_Style', 
    alignment = TA_JUSTIFY, 
    fontSize = 14,
    leading = 24,
)

#generate streaming data from openai by stream
@app.post('/getBook')
def write_data_stream(payload: DataPayload):#
    topic = payload.data['topic']
    format = payload.data['format']
    print(topic)
    random_name = str(uuid.uuid4())
    filename = f"./books/{random_name}.pdf"
    print(filename)
    doc = MyDocTemplate(filename) #SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=1.5*inch, bottomMargin=1*inch)
    data = []
    styles = getSampleStyleSheet()

    messages = [
        {
            'role': 'system',
            'content': 'Act like a wonderful writer'
            
        },
        {
            'role': 'assistant',
            'content': 'You are a helpful assistant'
        },
        {
            'role':'user',
            'content': f"Write a title of a {format} book about {topic}"
        }
    ]
    print("YY")
    try:
        page_break = PageBreak()
        # Generate Title
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        title = response.choices[0].message.content
        title = Paragraph(title, h1)


        #Make Table Of Content
        toc = TableOfContents()
        toc.levelStyles = [
            # ParagraphStyle(fontName='Times-Bold', fontSize=20, name='TOCHeading1', leftIndent=20, firstLineIndent=-20, spaceBefore=10, leading=16),
            ParagraphStyle(fontSize=16, name='TOCHeading2', leftIndent=-60, rightIndent=40, spaceBefore=5, leading=12),
        ]


        # Generate Summary
        messages = [
            {
                'role': 'system',
                'content': 'Act like a wonderful writer'
                
            },
            {
                'role': 'user',
                'content': f"This {format} book is about {topic}"
            },
            {
                'role': 'user',
                'content': f"Write a summary of a story that its title is {title} and has 25 chapters."
            }
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            max_tokens=1024,
            temperature= 0.7,
        )
        summary = response.choices[0].message.content

        img = generate_image_from_prompt(summary, 'cover')
        if img['status'] == 'success':
            print("TT")
            url = img['message']
            image = Image(url, width=610, height=500)
            data.append(image)
        data.append(title)  
        data.append(page_break)

        data.append(title)   
        data.append(page_break)
        data.append(Paragraph('<b>Table of Contents</b>', centered))
        data.append(toc)
        data.append(page_break)
        data.append(Paragraph('Summary', h2))
        data.append(Paragraph(summary, para_style))
        data.append(page_break)

        # # Generate content of first chapter
        messages = [
            {
                'role': 'system',
                'content': 'Act like a wonderful writer'
                
            },
            {
                'role': 'user',
                'content': summary
            },
            {
                'role': 'user',
                'content': 'Write content of first chapter of the story.'
            }
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            max_tokens=1024,
            temperature= 0.7,
        )
        chapter = response.choices[0].message.content

        img = generate_image_from_prompt(chapter, 'normal')
        if img['status'] == 'success':
            url = img['message']
            image = Image(url, width=400, height=300)
            data.append(image)
        title, content = chapter.split('\n', 1)
        data.append(Paragraph(title, h2))
        data.append(Paragraph(content, para_style))
        data.append(page_break)

        # Generate content of first chapter
        for i in range(18):
            messages = [
                {
                    'role': 'system',
                    'content': 'Act like a wonderful writer'
                    
                },
                {
                    'role': 'user',
                    'content': summary
                },
                {
                    'role':'user',
                    'content': chapter
                },
                {
                    'role': 'user',
                    'content': f"Write next chapter(chapter {i+2}) of this story"
                }
            ]
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0613",
                messages=messages,
                max_tokens=1024,
                temperature= 0.7,
            )
            chapter = response.choices[0].message.content


            img = generate_image_from_prompt(chapter, 'normal')
            if img['status'] == 'success':
                url = img['message']
                image = Image(url, width=400, height=300)
                data.append(image)

            
            title, content = chapter.split('\n', 1)
            data.append(Paragraph(title, h2))
            data.append(Paragraph(content, para_style))
            data.append(page_break)

        # Generate content of last chapter
        messages = [
            {
                'role': 'system',
                'content': 'Act like a wonderful writer'
                
            },
            {
                'role': 'user',
                'content': summary
            },
            {
                'role':'user',
                'content': chapter
            },
            {
                'role': 'user',
                'content': 'Write last chapter(chapter 20) of this story'
            }

        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            max_tokens=1024,
            temperature= 0.7,
        )
        chapter = response.choices[0].message.content

        img = generate_image_from_prompt(chapter, 'normal')
        if img['status'] == 'success':
            url = img['message']
            image = Image(url, width=400, height=300)
            data.append(image)
        title, content = chapter.split('\n', 1)
        data.append(Paragraph(title, h2))
        data.append(Paragraph(content, para_style))

        doc.multiBuild(data)
        # with open('my_document.pdf', 'wb') as f:
        #     f.write(buffer.getbuffer())
        return FileResponse(filename, media_type="application/pdf")#
    except OpenAIError as e:
       print(e)
       return ''
    
# @app.post("/write", response_model_exclude_unset=True)
# async def gpt_writer(payload: DataPayload):
#     assistant_response = write_data_stream(payload)
#     return StreamingResponse(assistant_response, media_type='text/event-stream')


def generate_image_from_prompt(text, mode):
    # get summarize text from chatgpt

    messages = []
    messages.append({'role': 'assistant', 'content': text})
    messages.append({'role': 'user', 'content': 'Please Summarize your word less than 400 charactors'})
    # print(messages)
    try:
        out_prompt = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )
    except OpenAIError as e:
       return {
           'message': e,
           'status': 'error'
       }
    
    #request parameters
    prompt = str(out_prompt.choices[0].message["content"]).strip()

    try:
        if mode=='normal':
            imageFromDallE = openai.Image.create(
                prompt=prompt,
                n=1,
                size="512x512",
            )
            return{
                'message': imageFromDallE["data"][0]["url"],
                'caption': prompt,
                'status': 'success'
            }
        if mode=='cover':
            imageFromDallE = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024",
            )
            # print(imageFromDallE)
            return{
                'message': imageFromDallE["data"][0]["url"],
                'caption': prompt,
                'status': 'success'
            }
    except OpenAIError as e:
       return {
           'message': e,
           'status': 'error'
       }


if __name__ == "__main__":
    uvicorn.run('main:app', host='0.0.0.0', port=5000, reload=True)
    # write_data_stream()
