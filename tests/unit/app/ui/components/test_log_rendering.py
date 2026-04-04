from app.config.styles.colors import get_theme_colors
from app.ui.components.log_rendering import LogEntry, render_log_document_html


def test_render_log_document_keeps_each_entry_in_separate_block():
    """日志文档应将每条记录渲染为独立块，避免时间戳与正文串行混排。"""
    colors = get_theme_colors("light")
    entries = [
        LogEntry(timestamp="11:36:18", level="INFO", message="🚀 日志系统已启动"),
        LogEntry(timestamp="11:36:39", level="INFO", message="📊 主题已切换为: light"),
        LogEntry(timestamp="11:36:42", level="INFO", message="📊 主题已切换为: light"),
    ]

    html = render_log_document_html(entries, colors)

    assert html.count('class="log-entry"') == 3
    assert 'line-height: 1.45;' in html
    assert 'margin: 0 0 2px 0;' in html
    assert '&nbsp;<span style="color:' in html
    assert "&nbsp;&nbsp;" not in html
    assert html.index("[11:36:18]") < html.index("[11:36:39]") < html.index("[11:36:42]")
    assert "主题已切换为: light" in html


def test_render_log_document_uses_current_theme_colors_when_rerendered():
    """相同日志在不同主题下重绘时应使用当前主题颜色，而不是保留旧内联颜色。"""
    entry = LogEntry(timestamp="11:36:42", level="INFO", message="📊 主题已切换为: light")

    light_colors = get_theme_colors("light")
    dark_colors = get_theme_colors("dark")

    light_html = render_log_document_html([entry], light_colors)
    dark_html = render_log_document_html([entry], dark_colors)

    assert light_colors["log_info"] in light_html
    assert dark_colors["log_info"] in dark_html
    assert light_colors["log_info"] != dark_colors["log_info"]


def test_render_log_document_adds_bottom_padding_for_last_visible_entry():
    """日志文档应保留底部安全留白，避免自动滚动到底部时最后一行被裁切。"""
    html = render_log_document_html([], get_theme_colors("light"))

    assert "padding: 0 0 8px 0;" in html
