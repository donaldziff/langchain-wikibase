import os
import requests
import re
import argparse

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI
from langchain.agents import tool
from langchain.prompts import PromptTemplate
from langchain.globals import set_debug

from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config


WB_LANGUAGE = 'en'
WB_LIMIT = 10
WB_USER_AGENT = 'MyWikibaseBot/1.0'

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

  query = query.lstrip('sparql').strip("'").strip('"').strip('`')

  headers = {"Accept": "application/json"}
  if user_agent_header is not None:
      headers["User-Agent"] = user_agent_header

  return requests.get(
      url, headers=headers, params={"query": query, "format": "json"}
  )

@tool
def checkSparql(query: str) -> str:
  """Given a SPARQL query check if is valid."""

  response = performSparqlQuery(query)

  if response.status_code != 200:
      error_message = extract_error_message(response)
      if error_message:
          return f'Query failed with this syntax error: {error_message}, try to fix it with another one.'
      else:
        return 'Query failed, try another one.'

  print(f"Sparql results: {response.json()}")

  return 'Query is valid'

@tool
def runSparql(query: str) -> str:
  """Given a SPARQL query returns the results."""

  response = performSparqlQuery(query)

  if response.status_code != 200:
      error_message = extract_error_message(response)
      if error_message:
          return f'Query failed with this syntax error: {error_message}, try to fix it with another one.'
      else:
        return 'Query failed, try another one.'

  return response.json()

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


def answer_the_question(question, final_answer):

  if 'OPENAI_API_URL' in os.environ:
      llm = OpenAI(openai_api_base=os.environ['OPENAI_API_URL'],
            openai_api_key="dummy",
            temperature=0,
            top_p=0,
            max_tokens=1024,
            model_kwargs={"seed": 42})
  else:
      llm = OpenAI(temperature=0,
            top_p=0,
            max_tokens=1024,
            model_kwargs={"seed": 42})

  if final_answer:
    tools = [getQItem, getProperty, runSparql]
    prompt = load_prompt_file('prompts/question-to-answer.prompt')
  else:
    tools = [getQItem, getProperty, checkSparql]
    prompt = load_prompt_file('prompts/question-to-sparql.prompt')

  agent = create_react_agent(llm, tools, prompt)

  agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

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
