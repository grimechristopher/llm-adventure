# tests/shared/test_file_tools.py
import pytest
from unittest.mock import AsyncMock, Mock, patch, mock_open
from pathlib import Path

@pytest.mark.asyncio
async def test_read_file():
    """Test reading file contents"""
    from shared.tools.file import read_file

    mock_content = "Test file content"

    with patch('builtins.open', mock_open(read_data=mock_content)):
        result = await read_file.ainvoke({"path": "/test/file.txt"})

        assert "Test file content" in result

@pytest.mark.asyncio
async def test_write_file():
    """Test writing to a file"""
    from shared.tools.file import write_file

    m = mock_open()

    with patch('builtins.open', m):
        result = await write_file.ainvoke({
            "path": "/test/file.txt",
            "content": "New content"
        })

        assert "success" in result.lower() or "written" in result.lower()
        m.assert_called_once_with("/test/file.txt", "w")

@pytest.mark.asyncio
async def test_list_files():
    """Test listing files in a directory"""
    from shared.tools.file import list_files

    mock_files = [
        Path("/test/dir/file1.txt"),
        Path("/test/dir/file2.py"),
        Path("/test/dir/subdir")
    ]

    with patch('pathlib.Path.iterdir', return_value=mock_files):
        result = await list_files.ainvoke({"path": "/test/dir"})

        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result

@pytest.mark.asyncio
async def test_delete_file():
    """Test deleting a file"""
    from shared.tools.file import delete_file

    with patch('pathlib.Path.unlink') as mock_unlink:
        result = await delete_file.ainvoke({"path": "/test/file.txt"})

        assert "success" in result.lower() or "deleted" in result.lower()
        mock_unlink.assert_called_once()

@pytest.mark.asyncio
async def test_read_file_error_handling():
    """Test read file handles errors gracefully"""
    from shared.tools.file import read_file

    with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
        result = await read_file.ainvoke({"path": "/test/nonexistent.txt"})

        assert "failed" in result.lower() or "error" in result.lower()

@pytest.mark.asyncio
async def test_list_files_with_pattern():
    """Test listing files with glob pattern"""
    from shared.tools.file import list_files

    mock_files = [
        Path("/test/dir/file1.txt"),
        Path("/test/dir/file2.txt"),
        Path("/test/dir/file3.py")
    ]

    with patch('pathlib.Path.glob', return_value=mock_files):
        result = await list_files.ainvoke({
            "path": "/test/dir",
            "pattern": "*.txt"
        })

        assert "file1.txt" in result
        assert "file2.txt" in result
