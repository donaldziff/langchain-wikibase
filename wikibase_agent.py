import os
import requests
import re
import argparse
import time
from datetime import datetime

from langchain.agents import AgentExecutor, create_react_agent, create_openai_tools_agent

from langchain_openai import OpenAI

from langchain.agents import tool
from langchain.prompts import PromptTemplate
from langchain.globals import set_debug

from langchain_community.llms import Ollama

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun
from google.generativeai.types.safety_types import HarmBlockThreshold, HarmCategory

from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config


WB_LANGUAGE = 'en'
#WB_LANGUAGE = 'pt-br'
WB_LIMIT = 200
WB_USER_AGENT = 'MyWikibaseBot/1.0'
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

wbi_config['USER_AGENT'] = 'MyWikibaseBot/1.0'

def extract_error_message(response):
  pattern = re.compile(r'MalformedQueryException:(.*)\n')
  match = pattern.search(response.text)
  if match:
    return match.group(1).strip()
  else:
    return None

def performSparqlQuery(query: str) -> str:
  url = "https://query.wikidata.org/sparql"
  user_agent_header = WB_USER_AGENT

  query = str(query).lstrip('sparql').strip('\n').strip("'").strip('"').strip('`')

  headers = {"Accept": "application/json"}
  if user_agent_header is not None:
      headers["User-Agent"] = user_agent_header

  return requests.get(
      url, headers=headers, params={"query": query, "format": "json"}
  )

@tool
def WikidataRetrieval(item: str) -> str:
  """Returns all the information about the input name, label, Q item or property from Wikidata."""
  wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())
  info = wikidata.run(item)
  return str(info)

@tool
def runSparql(query: str) -> str:
  """Given a SPARQL query returns the results."""

  response = performSparqlQuery(str(query))

  if response.status_code != 200:
      error_message = extract_error_message(response)
      if error_message:
          return f'Query failed with this syntax error: {error_message}, try to fix it with another one.'
      else:
        return 'Query failed, try another one.'

  return response.json()

@tool
def getQItem(name: str) -> str:
  """Returns the Q item from Wikidata."""

  name = str(name).strip("'").strip('"')

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
  """Returns the property from Wikidata."""

  name = str(name).strip("'").strip('"')

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

@tool
def runSparqlQuery(query: str) -> str:
  """Given a SPARQL query returns the results."""
  try:
    results = wbi_helpers.execute_sparql_query(query, max_retries=1)
    return results
  except Exception as e:
    return 'Query is not working, try another one.'

def load_prompt_file(full_path):
  with open(full_path, 'r') as f:
    txt_prompt = f.read()
  prompt = PromptTemplate.from_template(txt_prompt);
  return prompt


def answer_the_question(question):

  if 'OPENAI_API_KEY' in os.environ:
      llm = OpenAI(
            temperature=0,
            top_p=0,
            max_tokens=1024,
            model_kwargs={"seed": 42})
  elif 'GOOGLE_API_KEY' in os.environ:
      llm = ChatGoogleGenerativeAI(
              model="gemini-1.0-pro",
              temperature=0,
              top_p=0,
              safety_settings = {
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                }
              )
  else:
      llm = Ollama(
              model="mixtral:latest",
              temperature=0,
              top_p=0)


  tools = [getQItem, getProperty, runSparql, WikidataRetrieval]
  prompt = load_prompt_file('prompts/gemini.prompt')

  agent = create_react_agent(llm, tools, prompt)

  agent_executor = AgentExecutor(
          agent=agent,
          tools=tools,
          verbose=True,
          handle_parsing_errors=True,
          early_stop_method='generate',
          return_intermediate_steps=False,
          max_iteration=10
          )

  set_debug(False)

  result = agent_executor.invoke({"input": f"{question}"})
  return result