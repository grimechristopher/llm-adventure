# shared/tools/web.py
from langchain_core.tools import tool
import requests

@tool
def web_search(query: str) -> str:
    """
    Search the web for information

    Args:
        query: The search query

    Returns:
        Search results as formatted text
    """
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        search = TavilySearchResults(max_results=5)
        results = search.run(query)

        # Format results
        formatted = []
        for result in results:
            formatted.append(f"Title: {result.get('title', 'N/A')}")
            formatted.append(f"URL: {result.get('url', 'N/A')}")
            formatted.append(f"Content: {result.get('content', 'N/A')}")
            formatted.append("---")

        return "\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool
def http_request(url: str, method: str = "GET", headers: dict = None, data: dict = None) -> str:
    """
    Make an HTTP request

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        headers: Optional headers dict
        data: Optional data dict for POST requests

    Returns:
        Response text
    """
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        return f"Status: {response.status_code}\n\n{response.text}"
    except Exception as e:
        return f"Request failed: {str(e)}"

@tool
def fetch_url(url: str) -> str:
    """
    Fetch content from a URL

    Args:
        url: The URL to fetch

    Returns:
        Page content
    """
    return http_request.invoke({"url": url, "method": "GET"})
