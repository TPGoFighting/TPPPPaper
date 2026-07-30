"""结构化日志配置。

使用 structlog 统一日志格式，支持 JSON 输出（生产）和彩色控制台（开发）。
所有模块通过 `logging.getLogger(__name__)` 获取 logger，structlog 自动接管。

用法：
    from app.logging_config import get_logger
    logger = get_logger()
    logger.info("model_call", model="gpt-4o", stage="extract", duration_ms=8500)
"""

import logging
import os
import sys

import structlog


def setup_logging(json_output: bool | None = None) -> None:
    """初始化 structlog 配置。

    Args:
        json_output: 是否输出 JSON 格式。None 时根据 LOG_FORMAT 环境变量决定，
                     默认 False（开发模式用 console）。
    """
    if json_output is None:
        json_output = os.environ.get("LOG_FORMAT", "").lower() in ("json", "json_lines")

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    # 降低第三方库日志级别
    for noisy in ("httpx", "httpcore", "urllib3", "sqlalchemy.engine", "bleach"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取 structlog 绑定的 logger。"""
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()
