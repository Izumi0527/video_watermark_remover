"""
样式表工厂，负责组合各组件样式。
"""

from typing import Dict

from .sections.additional import additional_styles
from .sections.buttons import button_styles
from .sections.checkbox import checkbox_styles
from .sections.combobox import combobox_styles
from .sections.groupbox import groupbox_styles
from .sections.label import label_styles
from .sections.listwidget import listwidget_styles
from .sections.main_window import main_window_styles
from .sections.progress import progressbar_styles
from .sections.tab import tab_styles
from .sections.textedit import textedit_styles


class StyleFactory:
    """样式工厂类，生成各种UI组件的样式表。"""

    def __init__(self, theme_colors: Dict[str, str]):
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

    def get_label_stylesheet(self) -> str:
        return label_styles(self.colors)

    def get_listwidget_stylesheet(self) -> str:
        return listwidget_styles(self.colors)

    def get_additional_styles(self) -> str:
        return additional_styles(self.colors)


__all__ = ["StyleFactory"]
