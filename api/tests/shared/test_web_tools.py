# tests/shared/test_web_tools.py
import pytest
from unittest.mock import patch, Mock

def test_web_search_tool():
    """Test web search tool returns results"""
    from shared.tools.web import web_search

    with patch('langchain_community.tools.tavily_search.TavilySearchResults') as mock_tavily:
        mock_tavily.return_value.run.return_value = [{"title": "Test", "url": "http://example.com"}]

        result = web_search.invoke("test query")

        assert "Test" in result
        assert "http://example.com" in result

def test_http_request_tool():
    """Test HTTP request tool"""
    from shared.tools.web import http_request

    with patch('shared.tools.web.requests.request') as mock_request:
        mock_response = Mock()
        mock_response.text = "response content"
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = http_request.invoke({"url": "http://example.com", "method": "GET"})

        assert "response content" in result
