import gradio as gr

import gemini_module

from gemini_module import answer_the_question

import os

LANGCHAIN_TRACING_V2=os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_API_KEY=os.getenv('LANGCHAIN_API_KEY')
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')

def result(question, history):
    answer = answer_the_question(question)
    return answer['output']

demo = gr.ChatInterface(
    result, 
    chatbot=gr.Chatbot(height=300),
    #textbox=gr.Textbox(placeholder="Faça uma pergunta sobre alguma informação da Wikidata:", container=False, scale=7),
    title="Wikidata Chat ✨",
    description="Faça uma pergunta para a Wikidata!",
    theme="soft",
    examples=['Qual o PIB do Brasil?', 'Qual a população de São Paulo', "Quem foi Albert Einstein?"],
    cache_examples=False,
    undo_btn="⬅️ Apagar último",
    clear_btn="🗑️ Limpar",
    )

if __name__ == "__main__":
    demo.launch(server_name="10.0.2.88")
