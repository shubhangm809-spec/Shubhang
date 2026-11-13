
import ast
import asyncio
import operator as op
import ipaddress
import socket
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse


try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from rag import search_documents


# ==========================================
# 1. TOOL SCHEMAS
# ==========================================

TOOL_SCHEMAS = [

    # TOOL 1: WEB SEARCH
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current or factual information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
        },
    },

    # TOOL 2: FETCH WEB PAGE
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Download a web page and return its text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"],
            },
        },
    },

    # TOOL 3: CALCULATOR
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"],
            },
        },
    },

    # TOOL 4: PDF DOCUMENT SEARCH
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search uploaded PDF documents and return relevant text with filename and page numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
        },
    },

]


# ==========================================
# 2. SAFE CALCULATOR
# ==========================================

_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.USub: op.neg,
}


def _eval(node):

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](
            _eval(node.left),
            _eval(node.right)
        )

    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](
            _eval(node.operand)
        )

    raise ValueError("Unsupported expression")


def _calculate(expr: str):

    return _eval(ast.parse(expr, mode="eval").body)


# ==========================================
# 3. WEB SEARCH
# ==========================================

def _search(query: str):

    return list(DDGS().text(query, max_results=4))


# ==========================================
# 4. FETCH WEB PAGE
# ==========================================

def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False

        hostname = parsed.hostname

        # Resolve the hostname to IP addresses
        addresses = socket.getaddrinfo(hostname, None)

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False

        return True

    except (ValueError, socket.gaierror, OSError):
        return False


async def _fetch(url: str):
    current_url = url

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as client:

        for _ in range(4):
            if not await asyncio.to_thread(_is_safe_url, current_url):
                raise ValueError("Blocked unsafe URL")

            response = await client.get(current_url)

            if response.is_redirect:
                location = response.headers.get("location")

                if not location:
                    raise ValueError("Invalid redirect")

                current_url = str(response.url.join(location))
                continue

            response.raise_for_status()
            break
        else:
            raise ValueError("Too many redirects")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    text = " ".join(soup.get_text(" ").split())

    return text[:3000]
# ==========================================
# 5. TOOL DISPATCHER
# ==========================================

async def run_tool(name: str, args: dict, sources: list):

    try:

        # ----------------------------------
        # TOOL 1: WEB SEARCH
        # ----------------------------------

        if name == "web_search":

            results = await asyncio.to_thread(
                _search,
                args.get("query", "")
            )

            lines = []

            for result in results:

                sources.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", "")
                })

                n = len(sources)

                lines.append(
                    f"[{n}] {result.get('title', '')}\n"
                    f"{result.get('body', '')}\n"
                    f"URL: {result.get('href', '')}"
                )

            return "\n\n".join(lines) or "No results found."


        # ----------------------------------
        # TOOL 2: FETCH WEB PAGE
        # ----------------------------------

        if name == "fetch_page":

            return await _fetch(
                args.get("url", "")
            )


        # ----------------------------------
        # TOOL 3: CALCULATOR
        # ----------------------------------

        if name == "calculator":

            return str(
                _calculate(
                    args.get("expression", "")
                )
            )


        # ----------------------------------
        # TOOL 4: SEARCH PDF DOCUMENTS
        # ----------------------------------

        if name == "search_documents":

            results = await asyncio.to_thread(
                search_documents,
                args.get("query", "")
            )

            if not results:

                return "No relevant information found in uploaded documents."

            lines = []

            for result in results:

                sources.append({
                    "title": result["filename"],
                    "page": result["page"],
                    "type": "uploaded_document"
                })

                lines.append(
                    f"Document: {result['filename']}\n"
                    f"Page: {result['page']}\n"
                    f"Content: {result['text']}"
                )

            return "\n\n".join(lines)


        # ----------------------------------
        # UNKNOWN TOOL
        # ----------------------------------

        return f"Unknown tool: {name}"


    except Exception as e:

        return f"Tool error: {e}"
