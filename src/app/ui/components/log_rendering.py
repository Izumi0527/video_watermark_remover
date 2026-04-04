"""日志富文本渲染辅助模块。"""

from dataclasses import dataclass
from html import escape
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class LogEntry:
    """日志面板中的单条结构化记录。"""

    timestamp: str
    level: str
    message: str


def render_log_entry_html(entry: LogEntry, colors: Mapping[str, str]) -> str:
    """将单条日志记录渲染为稳定的独立 HTML 块。"""
    level_key = entry.level.upper()
    theme_level_key = f"log_{entry.level.lower()}"

    timestamp_color = colors.get("TIMESTAMP", colors.get("log_timestamp", "#888888"))
    message_color = colors.get("MESSAGE", colors.get("text_primary", "#FFFFFF"))
    level_color = colors.get(
        level_key,
        colors.get(theme_level_key, colors.get("INFO", colors.get("log_info", message_color))),
    )

    safe_timestamp = escape(entry.timestamp)
    safe_level = escape(entry.level)
    safe_message = escape(entry.message)

    return (
        '<div class="log-entry" style="line-height: 1.45; margin: 0 0 2px 0;">'
        f'<span style="color: {timestamp_color}; font-weight: 500;">[{safe_timestamp}]</span>'
        f'&nbsp;<span style="color: {level_color}; font-weight: 700;">[{safe_level}]</span>'
        f'&nbsp;<span style="color: {message_color}; font-weight: 500;">'
        f"{safe_message}</span></div>"
    )


def render_log_document_html(entries: Iterable[LogEntry], colors: Mapping[str, str]) -> str:
    """将全部日志记录渲染为完整 HTML 文档，便于主题切换后整体重绘。"""
    entry_html = "".join(render_log_entry_html(entry, colors) for entry in entries)
    body_color = colors.get("MESSAGE", colors.get("text_primary", colors.get("INFO", "#FFFFFF")))

    return (
        "<html><head><meta charset='utf-8'></head>"
        f"<body style='margin: 0; padding: 0 0 8px 0; color: {body_color};'>{entry_html}</body></html>"
    )
