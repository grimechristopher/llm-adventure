# shared/tools/file.py
from langchain_core.tools import tool
from pathlib import Path
from typing import Optional

@tool
async def read_file(path: str) -> str:
    """
    Read contents from a file

    Args:
        path: Path to the file to read

    Returns:
        File contents as text
    """
    try:
        with open(path, 'r') as f:
            content = f.read()

        return f"File: {path}\nSize: {len(content)} bytes\n\nContent:\n{content}"
    except Exception as e:
        return f"Read failed: {str(e)}"

@tool
async def write_file(path: str, content: str) -> str:
    """
    Write content to a file

    Args:
        path: Path to the file to write
        content: Content to write to the file

    Returns:
        Success message
    """
    try:
        with open(path, 'w') as f:
            f.write(content)

        return f"Successfully written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Write failed: {str(e)}"

@tool
async def list_files(path: str, pattern: Optional[str] = None) -> str:
    """
    List files in a directory

    Args:
        path: Path to the directory
        pattern: Optional glob pattern (e.g., "*.txt")

    Returns:
        List of files as formatted text
    """
    try:
        dir_path = Path(path)

        if pattern:
            files = list(dir_path.glob(pattern))
        else:
            files = list(dir_path.iterdir())

        if not files:
            return f"No files found in {path}"

        # Format results
        formatted = [f"Files in {path}:"]
        for file in sorted(files):
            file_type = "dir" if file.is_dir() else "file"
            size = file.stat().st_size if file.is_file() else "-"
            formatted.append(f"  [{file_type}] {file.name} ({size} bytes)" if size != "-" else f"  [{file_type}] {file.name}")

        return "\n".join(formatted)
    except Exception as e:
        return f"List failed: {str(e)}"

@tool
async def delete_file(path: str) -> str:
    """
    Delete a file

    Args:
        path: Path to the file to delete

    Returns:
        Success message
    """
    try:
        file_path = Path(path)
        file_path.unlink()

        return f"Successfully deleted {path}"
    except Exception as e:
        return f"Delete failed: {str(e)}"
