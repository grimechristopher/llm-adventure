# tests/core/test_logging.py
import json
from io import StringIO

def test_get_logger_creates_structured_logger():
    """Test logger outputs structured JSON"""
    from core.logging import get_logger

    logger = get_logger("test.module")
    assert logger is not None

def test_logger_outputs_json_format(tmp_path):
    """Test logger writes JSON to file"""
    import structlog
    from core.logging import configure_logging

    log_file = tmp_path / "test.log"
    configure_logging(log_file=str(log_file), log_to_console=False)

    logger = structlog.get_logger("test")
    logger.info("test_event", key1="value1", key2=42)

    # Read log file
    with open(log_file) as f:
        log_line = f.readline()
        log_data = json.loads(log_line)

    assert log_data["event"] == "test_event"
    assert log_data["key1"] == "value1"
    assert log_data["key2"] == 42
    assert "timestamp" in log_data
