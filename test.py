from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun

wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())

print(wikidata.run("Q1"))
