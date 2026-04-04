"""样式表工厂，负责组合各组件样式."""

from typing import Dict

# Phase 6: 从重构后的 sections 包统一导入
from .sections import (
    additional_styles,
    button_styles,
    checkbox_styles,
    combobox_styles,
    groupbox_styles,
    label_styles,
    listwidget_styles,
    main_window_styles,
    progressbar_styles,
    spinbox_styles,
    tab_styles,
    textedit_styles,
)


class StyleFactory:
    """样式工厂类，生成各种 UI 组件的样式表."""

    def __init__(self, theme_colors: Dict[str, str]):
        """初始化样式工厂。"""
        self.colors = theme_colors

    def get_main_window_stylesheet(self) -> str:
        return main_window_styles(self.colors)

    def get_button_stylesheet(self) -> str:
        return button_styles(self.colors)

    def get_groupbox_stylesheet(self) -> str:
        return groupbox_styles(self.colors)

    def get_tab_stylesheet(self) -> str:
        return tab_styles(self.colors)

    def get_progressbar_stylesheet(self) -> str:
        return progressbar_styles(self.colors)

    def get_textedit_stylesheet(self) -> str:
        return textedit_styles(self.colors)

    def get_checkbox_stylesheet(self) -> str:
        return checkbox_styles(self.colors)

    def get_combobox_stylesheet(self) -> str:
        return combobox_styles(self.colors)

    def get_spinbox_stylesheet(self) -> str:
        return spinbox_styles(self.colors)

    def get_label_stylesheet(self) -> str:
        return label_styles(self.colors)

    def get_listwidget_stylesheet(self) -> str:
        return listwidget_styles(self.colors)

    def get_additional_styles(self) -> str:
        return additional_styles(self.colors)


__all__ = ["StyleFactory"]
