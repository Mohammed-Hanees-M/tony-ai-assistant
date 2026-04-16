def mock_web_search(query: str) -> str:
    return f"Search results for: {query}"

def mock_document_reader(file_path: str) -> str:
    if file_path == "bad.txt":
        raise ValueError("File corrupted")
    return f"Contents of {file_path}"

def mock_python_interpreter(code: str, previous_output: str = "") -> str:
    return f"Execution of [{code}] returned: Success"

# A simple registry for available tools
AVAILABLE_TOOLS = {
    "web_search": {
        "description": "Searches the web for current information, news, or topics outside general knowledge.",
        "parameters": {"query": "string"},
        "handler": mock_web_search
    },
    "document_reader": {
        "description": "Reads and extracts information from local files or documents.",
        "parameters": {"file_path": "string"},
        "handler": mock_document_reader
    },
    "python_interpreter": {
        "description": "Executes python code for math, data analysis, or logic.",
        "parameters": {"code": "string"},
        "handler": mock_python_interpreter
    }
}

def is_tool_registered(tool_name: str) -> bool:
    return tool_name in AVAILABLE_TOOLS
    
def get_registry_manifest() -> str:
    manifest = []
    for name, metadata in AVAILABLE_TOOLS.items():
        manifest.append(f"- Tool: {name}\n  Description: {metadata['description']}\n  Params: {metadata['parameters']}")
    return "\n".join(manifest)
