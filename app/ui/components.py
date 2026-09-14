from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None):
        super().__init__()
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("cardTitle")
            self.layout.addWidget(label)
        if subtitle:
            text = QLabel(subtitle)
            text.setObjectName("muted")
            text.setWordWrap(True)
            self.layout.addWidget(text)


class SectionHeader(QWidget):
    def __init__(self, title: str, subtitle: str | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("muted")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)


class StatusBadge(QLabel):
    def __init__(self, text: str = "Non configure", state: str = "neutral"):
        super().__init__(text)
        self.set_state(state, text)

    def set_state(self, state: str, text: str) -> None:
        self.setText(text)
        self.setProperty("state", state)
        self.setObjectName("statusBadge")
        self.style().unpolish(self)
        self.style().polish(self)


class PrimaryButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("primaryButton")


class SecondaryButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("secondaryButton")


class SearchBox(QLineEdit):
    def __init__(self, placeholder: str):
        super().__init__()
        self.setObjectName("searchBox")
        self.setPlaceholderText(placeholder)


class StatCard(QFrame):
    def __init__(self, title: str, value: str, detail: str = ""):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("muted")
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        detail_label = QLabel(detail)
        detail_label.setObjectName("muted")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(detail_label)


class EmptyState(QFrame):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignCenter)
        title_label = QLabel(title)
        title_label.setObjectName("emptyTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("muted")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)


class CollapsibleSection(QFrame):
    toggled = Signal(bool)

    def __init__(self, title: str, summary: str = ""):
        super().__init__()
        self.setObjectName("collapsible")
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        header = QFrame()
        header.setObjectName("collapsibleHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(">")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.set_expanded)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        self.summary_label = QLabel(summary)
        self.summary_label.setObjectName("muted")
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.summary_label, 1)
        self.root.addWidget(header)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 12, 16, 16)
        self.content_layout.setSpacing(10)
        self.content.hide()
        self.root.addWidget(self.content)

    def set_summary(self, summary: str) -> None:
        self.summary_label.setText(summary)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setText("v" if expanded else ">")
        self.content.setVisible(expanded)
        self.toggled.emit(expanded)


class ModeButton(QPushButton):
    def __init__(self, title: str, subtitle: str):
        super().__init__(f"{title}\n{subtitle}")
        self.setCheckable(True)
        self.setObjectName("modeButton")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class KeyValueGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

    def set_rows(self, rows: list[tuple[str, str]]) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for label, value in rows:
            row = QFrame()
            row.setObjectName("kvRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            key = QLabel(label)
            key.setObjectName("muted")
            val = QLabel(value)
            val.setObjectName("kvValue")
            val.setWordWrap(True)
            row_layout.addWidget(key, 1)
            row_layout.addWidget(val, 2)
            self.layout.addWidget(row)
