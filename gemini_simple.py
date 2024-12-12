import google.generativeai as genai
import os
from dotenv import load_dotenv

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Set up the model
generation_config = {
  "temperature": float(os.getenv('TEMPERATURE')),
  "top_p": float(os.getenv('TOP_P')),
  "top_k": int(os.getenv('TOP_K')),
  "max_output_tokens": int(os.getenv('MAX_OUTPUT_TOKEN')),
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

model = genai.GenerativeModel(model_name=os.getenv('GEMINI_MODEL'),
                              generation_config=generation_config,
                              safety_settings=safety_settings)

chat_session = model.start_chat(history=[])

def simple_chat(question,chat_session):
    chat_session.send_message(question)
    answer = chat_session.last.text
    return answer
