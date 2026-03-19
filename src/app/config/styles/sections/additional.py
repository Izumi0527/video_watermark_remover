"""附加样式片段。"""


def additional_styles(colors: dict) -> str:
    """附加组件样式."""
    return f"""
    QSplitter::handle {{
        background-color: transparent;
        margin: 2px;
    }}

    QSplitter::handle:horizontal {{ width: 4px; }}
    QSplitter::handle:vertical {{ height: 4px; }}

    QSplitter::handle:hover {{
        background-color: {colors['primary_light']};
        border-radius: 2px;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {colors['text_disabled']};
        border-radius: 5px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {colors['text_secondary']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    QToolTip {{
        background-color: {colors['card']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 4px;
    }}

    QLabel#preview_placeholder, QLabel#image_label {{
        border: 1px solid {colors['border']};
        border-radius: 8px;
        background-color: {colors['surface']};
        color: {colors['text_secondary']};
        font-size: 11pt;
    }}

    /* 视频占位符样式 */
    QLabel#preview_placeholder[state="video"] {{
        border: 2px solid {colors['border']};
        border-radius: 12px;
        background-color: {colors['surface']};
        color: {colors['primary']};
        font-size: 11pt;
    }}

    /* 对比信息标签 - 默认状态 */
    QLabel#comparison_info {{
        background-color: {colors['surface']};
        border: 1px solid {colors['primary']};
        border-radius: 6px;
        padding: 6px 12px;
        color: {colors['primary']};
        font-weight: 600;
    }}

    /* 对比信息标签 - 成功状态 */
    QLabel#comparison_info[state="success"] {{
        background-color: {colors['success_light']};
        border: 1px solid {colors['success']};
        color: {colors['success']};
    }}

    /* 对比信息标签 - 处理中状态 */
    QLabel#comparison_info[state="processing"] {{
        background-color: {colors['warning_light']};
        border: 1px solid {colors['warning']};
        color: {colors['warning_dark']};
    }}

    QFrame#preview_container {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 6px;
    }}

    QLabel#preview_title {{
        font-weight: bold;
        color: {colors['text_primary']};
        font-size: 14px;
        padding-bottom: 5px;
    }}

    QScrollArea#image_scroll_area {{
        border: 1px solid {colors['border']};
        background-color: {colors['background']};
    }}

    QScrollArea#control_scroll_area {{
        background-color: transparent;
        border: none;
    }}

    QWidget#control_content {{ background-color: transparent; }}

    QLabel#info_label {{
        color: {colors['text_secondary']};
        font-style: italic;
        padding-left: 10px;
    }}

    QFrame#phase_container {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
    }}

    QLabel#phase_icon {{ font-size: 24px; }}

    QLabel#phase_text {{
        font-size: 14px;
        font-weight: bold;
        color: {colors['text_secondary']};
    }}

    QFrame#info_container {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
    }}

    QLabel[class="info_label"] {{
        font-size: 11px;
        color: {colors['text_secondary']};
    }}

    QLabel[class="info_value"] {{
        font-size: 12px;
        font-weight: bold;
        color: {colors['text_primary']};
    }}

    /* ========== 按钮样式 ========== */

    /* 成功按钮 (绿色) */
    QPushButton#btn_success {{
        background-color: {colors['success']};
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 16px;
    }}

    QPushButton#btn_success:hover {{
        background-color: #45a049;
    }}

    QPushButton#btn_success:disabled {{
        background-color: {colors['text_disabled']};
        color: {colors['text_secondary']};
    }}

    /* 危险按钮 (红色) */
    QPushButton#btn_danger {{
        background-color: {colors['error']};
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 16px;
    }}

    QPushButton#btn_danger:hover {{
        background-color: #da190b;
    }}

    QPushButton#btn_danger:disabled {{
        background-color: {colors['text_disabled']};
        color: {colors['text_secondary']};
    }}

    /* ========== 批处理样式 ========== */

    /* 队列信息标签 */
    QLabel#queue_info_label {{
        color: {colors['text_secondary']};
        font-style: italic;
    }}

    /* 批处理统计标签通用样式 */
    QLabel#batch_stat_total {{
        font-weight: bold;
        padding: 5px;
        background-color: {colors['info']};
        color: white;
        border-radius: 3px;
    }}

    QLabel#batch_stat_success {{
        font-weight: bold;
        padding: 5px;
        background-color: {colors['success']};
        color: white;
        border-radius: 3px;
    }}

    QLabel#batch_stat_failed {{
        font-weight: bold;
        padding: 5px;
        background-color: {colors['error']};
        color: white;
        border-radius: 3px;
    }}

    QLabel#batch_stat_waiting {{
        font-weight: bold;
        padding: 5px;
        background-color: {colors['warning']};
        color: white;
        border-radius: 3px;
    }}

    QLabel#batch_stat_concurrent {{
        font-weight: bold;
        padding: 5px;
        background-color: {colors['primary']};
        color: white;
        border-radius: 3px;
    }}

    /* 当前文件标签 */
    QLabel#current_file_label {{
        font-size: 12px;
        color: {colors['text_secondary']};
        margin-top: 10px;
    }}

    /* 批处理状态标签 */
    QLabel#batch_status_label {{
        padding: 8px;
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 3px;
        font-size: 11px;
        color: {colors['text_primary']};
    }}

    /* ========== 进度条样式 ========== */

    /* 当前文件进度条 (蓝色) */
    QProgressBar#current_progress_bar {{
        border: 2px solid {colors['border']};
        border-radius: 5px;
        text-align: center;
        height: 25px;
        background-color: {colors['surface']};
        color: {colors['text_primary']};
    }}

    QProgressBar#current_progress_bar::chunk {{
        background-color: {colors['primary']};
        border-radius: 3px;
    }}

    /* 总体进度条 (绿色) */
    QProgressBar#overall_progress_bar {{
        border: 2px solid {colors['border']};
        border-radius: 5px;
        text-align: center;
        height: 25px;
        background-color: {colors['surface']};
        color: {colors['text_primary']};
    }}

    QProgressBar#overall_progress_bar::chunk {{
        background-color: {colors['success']};
        border-radius: 3px;
    }}

    /* ========== 可选择图像标签样式 ========== */

    QLabel#selectable_image_label {{
        border: 2px solid {colors['border']};
        border-radius: 5px;
        background-color: {colors['surface']};
    }}
    """
