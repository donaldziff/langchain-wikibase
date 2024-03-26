import os
import requests
import re
import argparse

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI
from langchain.agents import tool
from langchain.prompts import PromptTemplate
from langchain.globals import set_debug
from langchain_community.llms import Ollama
from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun

from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config


WB_LANGUAGE = 'en'
WB_LIMIT = 100
WB_USER_AGENT = 'MyWikibaseBot/1.0'

wbi_config['USER_AGENT'] = 'MyWikibaseBot/1.0'

def extract_error_message(response):
  pattern = re.compile(r'MalformedQueryException:(.*)\n')
  match = pattern.search(response.text)
  if match:
    return match.group(1).strip()
  else:
    return None

@tool
def WikidataRetrieval(item: str) -> str:
  """Returns all the information about the input Q item or property from my wikibase."""
  wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())
    
  return wikidata.run(item)

def load_prompt_file(full_path):
  with open(full_path, 'r') as f:
    txt_prompt = f.read()
  prompt = PromptTemplate.from_template(txt_prompt);
  return prompt

@tool
def getQItem(name: str) -> str:
  """Returns the Q item from my wikibase."""

  name = name.strip("'").strip('"')

  data = {
    'action': 'wbsearchentities',
    'search': name,
    'type': 'item',
    'language': WB_LANGUAGE,
    'limit': WB_LIMIT
  }
  result = wbi_helpers.mediawiki_api_call_helper(data=data, allow_anonymous=True)
  if result['search']:
    return result['search'][0]['id']
  else:
    return 'Item not found by this name, try another name.'

@tool
def getProperty(name: str) -> str:
  """Returns the property from my wikibase."""

  name = name.strip("'").strip('"')

  data = {
    'action': 'wbsearchentities',
    'search': name,
    'type': 'property',
    'language': WB_LANGUAGE,
    'limit': WB_LIMIT
  }
  result = wbi_helpers.mediawiki_api_call_helper(data=data, allow_anonymous=True)
  if result['search']:
    return result['search'][0]['id']
  else:
    return 'Property not found by this name, try another name.'


def answer_the_question(question, final_answer):

  if 'OPENAI_API_URL' in os.environ:
      llm = OpenAI(openai_api_base=os.environ['OPENAI_API_URL'],
            openai_api_key="dummy",
            temperature=0,
            top_p=0,
            max_tokens=1024,
            model_kwargs={"seed": 42})
  else:
      llm = Ollama(
              model="mixtral:latest",
              temperature=0,
              top_p=0)
            #max_tokens=1024,
            #model_kwargs={"seed": 42})

  if final_answer:
#    tools = [getQItem, getProperty,  WikidataRetrieval]
    prompt = load_prompt_file('prompts/retrieval-to-answer.prompt')
  else:
    tools = [getQItem, WikidataRetrieval]
    prompt = load_prompt_file('prompts/question-to-retrieval.prompt')

  agent = create_react_agent(llm, tools, prompt)

  agent_executor = AgentExecutor(
          agent=agent, 
          tools=tools, 
          verbose=True, 
          handle_parsing_errors=True, 
          early_stop_method='generate', 
          max_iteratin=5
          )

  set_debug(False)

  result = agent_executor.invoke({"input": f"{question}"})
  return result


def main():
  parser = argparse.ArgumentParser(description='Wikibase agent.')
  parser.add_argument('--question', type=str, required=True, help='Your question.')
  parser.add_argument('--final-answer', action='store_true', help='Try to get an answer in natural language.')

  args = parser.parse_args()
  print(answer_the_question(args.question, args.final_answer))


if __name__ == '__main__':
  main()

