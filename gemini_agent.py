import os
from dotenv import load_dotenv
import requests
import re
import argparse
import time
from datetime import datetime

from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents import tool
from langchain.prompts import PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from langchain.globals import set_debug
from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai.types.safety_types import HarmBlockThreshold, HarmCategory
from langchain_core.prompts.chat import ChatPromptTemplate, MessagesPlaceholder

# Use tho langchain API Wrapper to access Wikidata APIs. Comment this line for local Wikibase instance
from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun

# Use the modified API Wrapper libraries below to acces a local wikibase instance API
#from langchain_mod.tools import WikidataQueryRun
#from langchain_mod.utilities import WikidataAPIWrapper

from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config

load_dotenv()

wb_url = os.getenv('WIKIBASE_URL')
wb_api_url = os.getenv('MEDIAWIKI_API_URL')
wb_sparql_url = os.getenv('MEDIAWIKI_SPARQL_ENDPOINT')
wbi_config['MEDIAWIKI_API_URL'] = wb_api_url
wbi_config['SPARQL_ENDPOINT_URL'] = wb_sparql_url
wbi_config['WIKIBASE_URL'] = wb_url

WB_LANGUAGE = os.getenv('WIKIBASE_LANGUAGE')
WB_LIMIT = int(os.getenv('WIKIBASE_LIMIT'))
WB_USER_AGENT = os.getenv('WIKIBASE_USER_AGENT')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

wbi_config['USER_AGENT'] = WB_USER_AGENT

def extract_error_message(response):
  pattern = re.compile(r'MalformedQueryException:(.*)\n')
  match = pattern.search(response.text)
  if match:
    return match.group(1).strip()
  else:
    return None

def performSparqlQuery(query: str) -> str:
#  url = "https://query.wikidata.org/sparql"
  url = wb_sparql_url
  user_agent_header = WB_USER_AGENT

  query = str(query).lstrip('sparql').strip('\n').strip("'").strip('"').strip('`')
  prefix = f"""
    PREFIX p: <{wb_url}/prop/>
    PREFIX pq: <{wb_url}/prop/qualifier/>
    PREFIX ps: <{wb_url}/prop/statement/>
    PREFIX wd: <{wb_url}/entity/>
    PREFIX wdt: <{wb_url}/prop/direct/>
  """
  query = prefix+query+'LIMIT'+str(os.getenv('SPARQL_QUERY_LIMIT'))

  headers = {"Accept": "application/json"}
  if user_agent_header is not None:
      headers["User-Agent"] = user_agent_header

  return requests.get(
      url, headers=headers, params={"query": query, "format": "json"}
  )

@tool
def WikibaseRetrieval(item: str) -> str:
  """Returns all the information about the input name, label, Q item or property from my Wikibase."""
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
  """Returns the Q item from my Wikibase."""

  name = str(name).strip("'").strip('"')

  data = {
    'action': 'wbsearchentities',
    'search': name,
    'type': 'item',
    'language': WB_LANGUAGE,
    'limit': WB_LIMIT
  }
  result = wbi_helpers.mediawiki_api_call_helper(data=data, mediawiki_api_url=wb_api_url, allow_anonymous=True)
  if result['search']:
      return result['search'][0]['id']
  else:
    return 'Item not found by this name, try another name.'

@tool
def getProperty(name: str) -> str:
  """Returns the property from Wikibase."""

  name = str(name).strip("'").strip('"')

  data = {
    'action': 'wbsearchentities',
    'search': name,
    'type': 'property',
    'language': WB_LANGUAGE,
    'limit': WB_LIMIT
  }
  result = wbi_helpers.mediawiki_api_call_helper(data=data, mediawiki_api_url=wb_api_url, allow_anonymous=True)
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

llm = ChatGoogleGenerativeAI(
            model=os.getenv('GEMINI_MODEL'), 
            temperature=float(os.getenv('TEMPERATURE')),
            top_p=float(os.getenv('TOP_P')),
            top_k=int(os.getenv('TOP_K')),
            max_output_token=int(os.getenv('MAX_OUTPUT_TOKEN')),
            safety_settings = {
                  HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                  HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                  HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                  HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
              }
            )

tools = [getQItem, getProperty, runSparql, WikibaseRetrieval]

file_prompt = open('prompts/gemini.prompt', 'r')

system_prompt = file_prompt.read()

user_prompt = '''
Question: {input}
Thought:{agent_scratchpad}
'''
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", user_prompt),
    ]
)

agent = create_react_agent(llm, tools, prompt)

memory = ChatMessageHistory(session_id="test-session")

agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="Check your output and make sure it conforms, use the Action/Action Input syntax",
        early_stop_method='generate',
        return_intermediate_steps=True,
        max_iteration=10,
        )

agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    # This is needed because in most real world scenarios, a session id is needed
    # It isn't really used here because we are using a simple in memory ChatMessageHistory
    lambda session_id: memory,
    input_messages_key="input",
    history_messages_key="chat_history",
)

def agent_chat(question,agent_with_chat_history):
  
  result = agent_with_chat_history.invoke(
      {"input": f"{question}"},
      config={"configurable": {"session_id": "test-session"}},
  )

  set_debug(False)

  return result
