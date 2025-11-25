def progressbar_styles(colors: dict) -> str:
    return f"""
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {colors['hover']};
        text-align: center;
        color: {colors['text_primary']};
        font-weight: bold;
        height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {colors['primary']};
        border-radius: 4px;
    }}

    QProgressBar#detailed_progress_bar {{
        height: 25px;
        font-size: 12px;
        border: 1px solid {colors['border']};
        background-color: {colors['background']};
    }}

    QProgressBar#detailed_progress_bar[phase="loading_models"]::chunk {{ background-color: {colors['info']}; }}
    QProgressBar#detailed_progress_bar[phase="detecting_watermarks"]::chunk {{ background-color: {colors['warning']}; }}
    QProgressBar#detailed_progress_bar[phase="processing_frames"]::chunk {{ background-color: {colors['success']}; }}
    QProgressBar#detailed_progress_bar[phase="merging_audio"]::chunk {{ background-color: #9C27B0; }}
    QProgressBar#detailed_progress_bar[phase="completed"]::chunk {{ background-color: {colors['success']}; }}
    QProgressBar#detailed_progress_bar[phase="error"]::chunk {{ background-color: {colors['error']}; }}
    """
