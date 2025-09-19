import logging
import sys
import time
from datetime import datetime
import json
from functools import wraps
import inspect
from typing import Any, Callable, Dict, Optional
from rich.console import Console
from rich.markdown import Markdown
from io import StringIO


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class AgentLogger:
    """
    A simple, centralized logger for multi-agent systems that provides
    real-time, color-coded logging to console.
    """

    def __init__(self, level=logging.INFO, log_file=None):
        """
        Initialize the logger with custom formatting

        Args:
            level: Logging level
            log_file: Optional file path to write logs to
        """
        self.logger = logging.getLogger("agent_logger")
        self.logger.setLevel(level)
        self.logger.handlers = []  # Clear any existing handlers

        # Console handler with color formatting
        self.console = Console()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # File handler if requested
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

    def _format_time(self):
        """Format current time for log messages"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _format_message(self, color, category, message):
        """Format a message with timestamp, category, and color"""
        time_str = f"{Colors.BRIGHT_WHITE}[{self._format_time()}]{Colors.RESET}"
        category_str = f"{color}[{category.upper()}]{Colors.RESET}"
        return f"{time_str} {category_str} {message}"

    def log_user_input(self, message):
        """Log user input"""
        formatted = self._format_message(Colors.BRIGHT_GREEN, "USER", message)
        self.logger.info(formatted)

    def log_agent_response(self, agent_name, message):
        """Log agent response"""
        message = Markdown(message)
        # Capture the rendered markdown as text
        with StringIO() as buffer:
            self.console.file = buffer  # Redirect console output
            self.console.print(message)
            formatted_message = buffer.getvalue().strip()
        formatted = self._format_message(
            Colors.BRIGHT_BLUE, agent_name, formatted_message
        )
        self.logger.info(formatted)

    def log_tool_call(self, tool_name, params):
        """Log tool call with parameters"""
        # Format parameters for better readability
        params_str = (
            json.dumps(params, indent=2) if isinstance(params, dict) else str(params)
        )
        header = self._format_message(
            Colors.BRIGHT_YELLOW, "TOOL", f"{tool_name} called with params:"
        )
        self.logger.info(f"{header}\n{Colors.YELLOW}{params_str}{Colors.RESET}")

    def log_tool_result(self, tool_name, result):
        """Log tool result"""
        # Try to parse JSON for better formatting if possible
        try:
            if isinstance(result, str) and (
                result.startswith("{") or result.startswith("[")
            ):
                parsed = json.loads(result)
                result_str = json.dumps(parsed, indent=2)
            else:
                result_str = str(result)
        except:
            result_str = str(result)

        header = self._format_message(
            Colors.BRIGHT_MAGENTA, "RESULT", f"{tool_name} returned:"
        )
        self.logger.info(f"{header}\n{Colors.MAGENTA}{result_str}{Colors.RESET}")

    def log_error(self, message, exc_info=None):
        """Log errors"""
        formatted = self._format_message(Colors.BRIGHT_RED, "ERROR", message)
        self.logger.error(formatted, exc_info=exc_info)

    def log_system(self, message):
        """Log system-level messages"""
        formatted = self._format_message(Colors.BRIGHT_WHITE, "SYSTEM", message)
        self.logger.info(formatted)


# Create a singleton instance
logger = AgentLogger()


def log_tool_execution(func):
    """
    Decorator to log tool calls and their results

    Usage:
    @log_tool_execution
    def my_tool_function(param1, param2):
        ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the function signature
        sig = inspect.signature(func)

        # Build a dictionary of parameters
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        params = dict(bound_args.arguments)

        # Log the tool call
        logger.log_tool_call(func.__name__, params)

        # Execute the function and track time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Add execution time to the log
            logger.log_system(f"{func.__name__} executed in {execution_time:.3f}s")

            # Log the result
            logger.log_tool_result(func.__name__, result)
            return result

        except Exception as e:
            logger.log_error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise

    return wrapper


def log_agent_util(
    message: str,
    title: Optional[str] = "UTIL",
    color: Optional[str] = Colors.BRIGHT_CYAN,
):
    """
    Log a utility message for agent helper nodes like verification, retries, etc.

    Args:
        message (str): The message content to log.
        title (str): Optional tag for the category of message (default: "UTIL").
        color (str): Optional ANSI color code for the tag.
    """
    formatted = logger._format_message(color, title, message)
    logger.logger.info(formatted)
