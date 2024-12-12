import gradio as gr
import gemini_agent
import gemini_simple
from gemini_agent import agent_chat
from gemini_simple import simple_chat

import os
from dotenv import load_dotenv

load_dotenv()

checkbox = gr.Checkbox(label='Use Wikidata/Wikibase Knowledge Graph.')

def result(question, history, checkbox):
    if checkbox:
      r = agent_chat(
              question,
              gemini_agent.agent_with_chat_history
              )
      answer = r['output']
    else:
      answer = simple_chat(
              question,
              gemini_simple.chat_session
              )
    return answer

chat = gr.ChatInterface(
    result, 
    chatbot=gr.Chatbot(height=550),
    title="Wikibase Chat ✨",
    description="Ask a question to you local Wikibase Knowledge Graph or Wikidata!",
    theme="soft",
    examples=[
        ['What is Google?'],
        ['What is the Google inception date? Search for the property \'inception\''],
        ["What is the US GDP?"],
    ],
    cache_examples=False,
    retry_btn="🔄 Try again",
    undo_btn="⬅️ Delete last",
    clear_btn="🗑️ Clear",
    additional_inputs=[checkbox]
    )

if __name__ == "__main__":
    chat.launch(server_name=str(os.getenv('UI_SERVER_NAME')),server_port=int(os.getenv('UI_SERVER_PORT')))
