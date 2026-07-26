import os

from src.tools.registry import register

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


@register(
    name="web_search",
    description="Search the web for current information. Input: {query: str}",
)
def web_search(query: str) -> str:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key or TavilyClient is None:
        return (
            f"[MOCK web_search result -- set TAVILY_API_KEY for real results] "
            f"No real search performed for query: '{query}'."
        )
    client = TavilyClient(api_key=api_key)
    result = client.search(query=query, max_results=3)
    snippets = []
    for r in result.get("results", []):
        snippets.append(f"- {r.get('title')}: {r.get('content', '')[:200]}")
    return "\n".join(snippets) if snippets else "No results found."
