
import logging
from app.utils.logger import get_logger, ColoredFormatter, log_separator

class TestLogger:

    def test_get_logger_config(self):
        """Verify logger is configured correctly"""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0 # At least console handler

    def test_colored_formatter(self):
        """Verify formatter adds color codes"""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        record = logging.LogRecord("test", logging.ERROR, "path", 1, "test message", (), None)
        
        output = formatter.format(record)
        # Should contain ANSI red color code
        assert "\033[31m" in output
        assert "test message" in output
        
    def test_log_separator(self):
        """Verify separator line logging"""
        mock_log = logging.getLogger("mock")
        # Just ensure it doesn't crash
        log_separator(mock_log, "*", 10)
