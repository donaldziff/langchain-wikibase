# Wikidata Chat

This repository is an chat bot app powered by Generative AI that is based on a Langchain Reasoning-Acting (ReAct) Agent. This autonomous agent can execute python code to retrieve information from Wikidata API or any local instance of Wikibase Knowledge Graph API. Moreover, the agent is able to generate SPARQL queries and run in the Wikibase SPARQL endpoint, fed by Blazegraph database. The technique used to generate answers is a Retrieval Augmented Generation (RAG) based on Knowledge Graphs instead of vector databases.

## Usage
* Create a python virtual env and install the `requirements.txt` packages.
* Move the `template.env` file to `.env`
* Set your GOOGLE_APY_KEY as env variable in `.env` file.
* Run the `ui.py` file
* The Wikidata Chat must be running on http://localhost:7861

![Captura de tela 2024-06-27 094505](https://github.com/dimasjackson/langchain-wikibase-agent/assets/114688989/c6ba6f47-cd42-492e-b8af-e39fcbb7ace3)

![image](https://github.com/dimasjackson/langchain-wikibase-agent/assets/114688989/9191536b-83f9-4a1b-a75e-0cdd047d53e2)

This repository contains work on a langchain agent for question answering against a Wikidata or any local instance of Wikibase/Mediawiki.

The agent is congirude to cal Google Gemini API, if you want to use othe LLMs via Ollama, like Mixtral 70b or Open AI's Chat GPT check the file `wikibase_agent.py`.

At present, this work is very preliminary, contributions are welcome! 

# Use in local Wikibase instance

To use in your local Wikibase instance change the settings in `.env` file.
