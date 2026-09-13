from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

import pandas as pd

from app.ui.qt_environment import configure_qt_plugin_path

configure_qt_plugin_path()

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import DEFAULT_PREVIEW_ROWS, DEFAULT_RANDOM_SEED, DEFAULT_RING_COLUMN
from app.deployment.ring_builder import (
    apply_exclusions,
    build_custom_size_rings,
    build_equal_rings,
    build_progressive_rings,
    build_representative_pilot,
)
from app.graph.auth import ClientCredentialsAuth
from app.graph.client import GraphReadOnlyClient
from app.graph.config import GraphConfigStore
from app.graph.errors import GraphError, SecureStorageUnavailable
from app.graph.factory import build_intune_device_inspector
from app.graph.models import GraphRequestLog, GraphSettings
from app.graph.secrets import GraphSecretStore
from app.intune.device_inspector import IntuneDeviceInspectorService
from app.intune.models import ApplicationStatus, DeviceHealth, DeviceInspectorResult, DeviceSearchResult, ManagedDevice
from app.intune.support_bundle import export_support_bundle
from app.io.exporters import export_rings
from app.io.tables import load_table, preview_rows
from app.models.deployment import ExportOptions, RingDefinition, RingResult
from app.ui.components import (
    Card,
    CollapsibleSection,
    EmptyState,
    KeyValueGrid,
    ModeButton,
    PrimaryButton,
    SearchBox,
    SecondaryButton,
    SectionHeader,
    StatCard,
    StatusBadge,
)
from app.ui.styles import APP_STYLESHEET
from app.utils.time import relative_datetime


class TaskWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable[[], object]):
        super().__init__()
        self.task = task

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.task())
        except GraphError as exc:
            detail = f"\n\nDetails: {exc.details}" if exc.details and exc.details != exc.user_message else ""
            self.failed.emit(f"{exc.user_message}{detail}")
        except Exception as exc:
            self.failed.emit(str(exc))


class AsyncPageMixin:
    thread: QThread | None
    worker: TaskWorker | None
    progress: QProgressBar

    def _start_task(self, task: Callable[[], object], on_success: Callable[[object], None], on_error: Callable[[str], None]) -> None:
        self.progress.show()
        self.thread = QThread(self)  # type: ignore[arg-type]
        self.worker = TaskWorker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(on_success)
        self.worker.finished.connect(self._task_finished)
        self.worker.failed.connect(on_error)
        self.worker.failed.connect(lambda _message: self._task_finished())
        self.thread.start()

    def _task_finished(self) -> None:
        self.progress.hide()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.thread = None
        self.worker = None


class DropZone(QFrame):
    fileDropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel("Drop CSV/XLSX/XLSM here")
        title.setObjectName("emptyTitle")
        subtitle = QLabel("or choose a file")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # type: ignore[override]
        urls = event.mimeData().urls()
        if urls:
            self.fileDropped.emit(urls[0].toLocalFile())


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def not_available(value: object) -> str:
    if value is None or value == "":
        return "Not available"
    return str(value)


def make_scroll_page(content: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(content)
    return scroll


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(EmptyState(title, subtitle))
        layout.addStretch()


class HomePage(QWidget):
    def __init__(self, navigate: Callable[[str, str | None], None]):
        super().__init__()
        self.navigate = navigate
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 36, 32, 32)
        root.setSpacing(24)

        hero = QWidget()
        hero_layout = QVBoxLayout(hero)
        hero_layout.setAlignment(Qt.AlignHCenter)
        title = QLabel("What do you want to do?")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Search tools, devices and Endpoint data.")
        subtitle.setObjectName("muted")
        self.search = SearchBox("Search tools or devices...")
        self.search.setMaximumWidth(640)
        hero_layout.addWidget(title, 0, Qt.AlignHCenter)
        hero_layout.addWidget(subtitle, 0, Qt.AlignHCenter)
        hero_layout.addWidget(self.search)
        root.addWidget(hero)

        root.addWidget(SectionHeader("QUICK TOOLS"))
        grid = QGridLayout()
        grid.setSpacing(14)
        tools = [
            ("Split into Waves", "Create equal deployment waves.", "Deployment Tools", "simple", True),
            ("Representative Pilot", "Build a pilot matching your fleet.", "Deployment Tools", "pilot", True),
            ("Device Inspector", "Find issues on an Intune device.", "Intune", None, True),
            ("Autopilot Inspector", "Coming soon", "Autopilot", None, False),
        ]
        for index, (title_text, subtitle_text, page, mode, enabled) in enumerate(tools):
            button = QPushButton(f"{title_text}\n{subtitle_text}")
            button.setObjectName("modeButton")
            button.setEnabled(enabled)
            if enabled:
                button.clicked.connect(lambda _=False, p=page, m=mode: self.navigate(p, m))
            grid.addWidget(button, index // 2, index % 2)
        root.addLayout(grid)
        root.addStretch()


class DeploymentToolsPage(QWidget, AsyncPageMixin):
    def __init__(self):
        super().__init__()
        self.dataframe: pd.DataFrame | None = None
        self.result: RingResult | None = None
        self.source_path: Path | None = None
        self.thread: QThread | None = None
        self.worker: TaskWorker | None = None
        self.progressive_rows: list[tuple[QWidget, QLineEdit, QDoubleSpinBox]] = []
        self.custom_rows: list[tuple[QWidget, QLineEdit, QSpinBox, QCheckBox]] = []
        self.criteria_checks: dict[str, QCheckBox] = {}
        self.all_criteria_visible = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        self.source_card = Card("1 Source", "Start with a CSV, XLSX or XLSM file.")
        self.source_layout = QVBoxLayout()
        self.source_layout.setContentsMargins(0, 0, 0, 0)
        self.source_card.layout.addLayout(self.source_layout)
        root.addWidget(self.source_card)
        self._render_source_empty()

        body = QHBoxLayout()
        body.setSpacing(18)
        self.config_card = Card("2 Configuration")
        self.preview_card = Card("3 Preview", "Generate a preview before exporting.")
        body.addWidget(self.config_card, 1)
        body.addWidget(self.preview_card, 1)
        root.addLayout(body)
        self._build_configuration()
        self._build_preview()

        self.export_card = Card("4 Export")
        self._build_export()
        root.addWidget(self.export_card)
        root.addStretch()

    def activate_mode(self, mode: str | None) -> None:
        index = {"simple": 0, "progressive": 1, "custom": 2, "pilot": 3}.get(mode or "simple", 0)
        self.mode_stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.mode_buttons):
            button.setChecked(button_index == index)

    def _render_source_empty(self) -> None:
        clear_layout(self.source_layout)
        drop = DropZone()
        drop.fileDropped.connect(self.load_file)
        choose = PrimaryButton("Choose file")
        choose.clicked.connect(self.select_file)
        self.source_layout.addWidget(drop)
        self.source_layout.addWidget(choose, 0, Qt.AlignLeft)

    def _render_source_loaded(self) -> None:
        clear_layout(self.source_layout)
        assert self.dataframe is not None
        row = QFrame()
        row.setObjectName("compactRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 12, 14, 12)
        info = QLabel(f"{self.source_path.name if self.source_path else 'Source file'}\n{len(self.dataframe):,} devices · {len(self.dataframe.columns)} columns")
        info.setObjectName("cardTitle")
        change = SecondaryButton("Change file")
        change.clicked.connect(self.select_file)
        columns = SecondaryButton("View columns")
        columns.clicked.connect(self.show_columns)
        layout.addWidget(info, 1)
        layout.addWidget(columns)
        layout.addWidget(change)
        self.source_layout.addWidget(row)

    def _build_configuration(self) -> None:
        self.config_card.layout.addWidget(SectionHeader("Distribution mode"))
        mode_row = QGridLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_buttons = [
            ModeButton("Equal Split", "Same size waves"),
            ModeButton("Progressive Rings", "Percent based rollout"),
            ModeButton("Custom Sizes", "Exact device counts"),
            ModeButton("Representative Pilot", "Stratified pilot"),
        ]
        for index, button in enumerate(self.mode_buttons):
            self.mode_group.addButton(button, index)
            mode_row.addWidget(button, index // 2, index % 2)
        self.config_card.layout.addLayout(mode_row)
        self.mode_group.idClicked.connect(self.activate_mode_index)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._build_equal_panel())
        self.mode_stack.addWidget(self._build_progressive_panel())
        self.mode_stack.addWidget(self._build_custom_panel())
        self.mode_stack.addWidget(self._build_pilot_panel())
        self.config_card.layout.addWidget(self.mode_stack)
        self.activate_mode("simple")

        self.advanced = CollapsibleSection("Advanced options", "Seed: 42 · No exclusions")
        self._build_advanced()
        self.config_card.layout.addWidget(self.advanced)

        generate = PrimaryButton("Generate preview")
        generate.clicked.connect(self.generate_preview)
        self.config_card.layout.addWidget(generate, 0, Qt.AlignLeft)

    def activate_mode_index(self, index: int) -> None:
        self.mode_stack.setCurrentIndex(index)

    def _build_equal_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.addWidget(SectionHeader("Number of waves"))
        row = QHBoxLayout()
        minus = SecondaryButton("-")
        plus = SecondaryButton("+")
        self.simple_count = QSpinBox()
        self.simple_count.setRange(1, 50)
        self.simple_count.setValue(5)
        minus.clicked.connect(lambda: self.simple_count.setValue(max(1, self.simple_count.value() - 1)))
        plus.clicked.connect(lambda: self.simple_count.setValue(self.simple_count.value() + 1))
        row.addWidget(minus)
        row.addWidget(self.simple_count)
        row.addWidget(plus)
        row.addStretch()
        layout.addLayout(row)
        self.randomize_checkbox = QCheckBox("Randomize devices")
        self.randomize_checkbox.setChecked(True)
        layout.addWidget(self.randomize_checkbox)
        self.criteria_container = QWidget()
        self.criteria_layout = QVBoxLayout(self.criteria_container)
        self.criteria_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(SectionHeader("Balance waves by"))
        layout.addWidget(self.criteria_container)
        self.more_fields_button = SecondaryButton("More fields")
        self.more_fields_button.clicked.connect(self.toggle_all_criteria)
        layout.addWidget(self.more_fields_button, 0, Qt.AlignLeft)
        return panel

    def _build_progressive_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        self.progressive_list = QVBoxLayout()
        layout.addLayout(self.progressive_list)
        self.progressive_total = QLabel("Total 0%")
        self.progressive_total.setObjectName("cardTitle")
        for name, pct in [("Pilot", 2), ("Ring 1", 8), ("Ring 2", 20), ("Ring 3", 30), ("Broad", 40)]:
            self.add_progressive_row(name, pct)
        add = SecondaryButton("+ Add ring")
        add.clicked.connect(lambda: self.add_progressive_row("Ring", 0))
        layout.addWidget(add, 0, Qt.AlignLeft)
        layout.addWidget(self.progressive_total)
        return panel

    def _build_custom_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        self.custom_list = QVBoxLayout()
        layout.addLayout(self.custom_list)
        for name, size, remaining in [("Pilot", 50, False), ("Ring 1", 100, False), ("Ring 2", 250, False), ("Broad", 0, True)]:
            self.add_custom_row(name, size, remaining)
        add = SecondaryButton("+ Add group")
        add.clicked.connect(lambda: self.add_custom_row("Group", 0, False))
        layout.addWidget(add, 0, Qt.AlignLeft)
        return panel

    def _build_pilot_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.addWidget(SectionHeader("Representative Pilot", "Build a pilot group reflecting the overall fleet."))
        row = QHBoxLayout()
        row.addWidget(QLabel("Pilot size"))
        self.pilot_size = QSpinBox()
        self.pilot_size.setRange(1, 1_000_000)
        self.pilot_size.setValue(100)
        row.addWidget(self.pilot_size)
        row.addWidget(QLabel("devices"))
        row.addStretch()
        layout.addLayout(row)
        return panel

    def _build_advanced(self) -> None:
        form = QFormLayout()
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 999999999)
        self.seed_input.setValue(DEFAULT_RANDOM_SEED)
        self.identifier_column = QComboBox()
        form.addRow("Deterministic seed", self.seed_input)
        form.addRow("Identity field", self.identifier_column)
        self.advanced.content_layout.addLayout(form)
        self.exclusion_summary = QLabel("No exclusions")
        self.exclusion_summary.setObjectName("muted")
        self.exclusion_text = QPlainTextEdit()
        self.exclusion_text.setPlaceholderText("Paste exclusions, one per line")
        self.exclusion_text.setMaximumHeight(88)
        load = SecondaryButton("Load file")
        load.clicked.connect(self.load_exclusion_file)
        self.advanced.content_layout.addWidget(SectionHeader("Exclusions"))
        self.advanced.content_layout.addWidget(self.exclusion_summary)
        self.advanced.content_layout.addWidget(self.exclusion_text)
        self.advanced.content_layout.addWidget(load, 0, Qt.AlignLeft)

    def _build_preview(self) -> None:
        self.preview_summary = QLabel("No preview yet")
        self.preview_summary.setObjectName("muted")
        self.preview_card.layout.addWidget(self.preview_summary)
        self.ring_cards_layout = QGridLayout()
        self.preview_card.layout.addLayout(self.ring_cards_layout)
        self.distribution_container = QWidget()
        self.distribution_layout = QVBoxLayout(self.distribution_container)
        self.distribution_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_card.layout.addWidget(self.distribution_container)
        devices = SecondaryButton("View devices")
        devices.clicked.connect(self.show_devices)
        self.preview_card.layout.addWidget(devices, 0, Qt.AlignLeft)

    def _build_export(self) -> None:
        form = QFormLayout()
        self.export_xlsx = QRadioButton("XLSX")
        self.export_csv = QRadioButton("CSV")
        self.export_xlsx.setChecked(True)
        format_row = QHBoxLayout()
        format_row.addWidget(self.export_xlsx)
        format_row.addWidget(self.export_csv)
        format_row.addStretch()
        files_row = QHBoxLayout()
        self.export_global = QCheckBox("Global file")
        self.export_global.setChecked(True)
        self.export_split = QCheckBox("One file per ring")
        self.export_split.setChecked(True)
        files_row.addWidget(self.export_global)
        files_row.addWidget(self.export_split)
        self.export_dir = QLineEdit()
        browse = SecondaryButton("Browse")
        browse.clicked.connect(self.select_export_dir)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.export_dir, 1)
        folder_row.addWidget(browse)
        self.export_prefix = QLineEdit("deployment")
        form.addRow("Format", format_row)
        form.addRow("Files", files_row)
        form.addRow("Output folder", folder_row)
        form.addRow("File prefix", self.export_prefix)
        self.export_card.layout.addLayout(form)
        export = PrimaryButton("Export")
        export.clicked.connect(self.export_result)
        self.export_card.layout.addWidget(export, 0, Qt.AlignLeft)

    def add_progressive_row(self, name: str, percentage: float) -> None:
        row = QFrame()
        row.setObjectName("compactRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        name_input = QLineEdit(name)
        pct_input = QDoubleSpinBox()
        pct_input.setRange(0, 100)
        pct_input.setDecimals(2)
        pct_input.setValue(percentage)
        pct_input.valueChanged.connect(self.update_progressive_total)
        remove = SecondaryButton("x")
        remove.clicked.connect(lambda: self.remove_progressive_row(row))
        layout.addWidget(name_input, 1)
        layout.addWidget(pct_input)
        layout.addWidget(QLabel("%"))
        layout.addWidget(remove)
        self.progressive_rows.append((row, name_input, pct_input))
        self.progressive_list.addWidget(row)
        self.update_progressive_total()

    def remove_progressive_row(self, row: QWidget) -> None:
        self.progressive_rows = [item for item in self.progressive_rows if item[0] is not row]
        row.deleteLater()
        self.update_progressive_total()

    def update_progressive_total(self) -> None:
        total = sum(row[2].value() for row in self.progressive_rows)
        text = f"Total {total:g}%"
        if abs(total - 100.0) > 0.0001:
            text += " - Total must equal 100%."
        self.progressive_total.setText(text)

    def add_custom_row(self, name: str, size: int, remaining: bool) -> None:
        row = QFrame()
        row.setObjectName("compactRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        name_input = QLineEdit(name)
        size_input = QSpinBox()
        size_input.setRange(0, 10_000_000)
        size_input.setValue(size)
        remaining_check = QCheckBox("Remaining")
        remaining_check.setChecked(remaining)
        remove = SecondaryButton("x")
        remove.clicked.connect(lambda: self.remove_custom_row(row))
        layout.addWidget(name_input, 1)
        layout.addWidget(size_input)
        layout.addWidget(QLabel("devices"))
        layout.addWidget(remaining_check)
        layout.addWidget(remove)
        self.custom_rows.append((row, name_input, size_input, remaining_check))
        self.custom_list.addWidget(row)

    def remove_custom_row(self, row: QWidget) -> None:
        self.custom_rows = [item for item in self.custom_rows if item[0] is not row]
        row.deleteLater()

    def select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "Data files (*.csv *.xlsx *.xlsm)")
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        source = Path(path)
        self.source_path = source
        self._start_task(lambda: load_table(source), self._file_loaded, self._task_failed)

    def _file_loaded(self, result: object) -> None:
        self.dataframe = result  # type: ignore[assignment]
        self.result = None
        self.export_prefix.setText(self.source_path.stem if self.source_path else "deployment")
        self._populate_columns()
        self._render_source_loaded()
        self.preview_summary.setText("Source loaded. Generate a preview when ready.")

    def _populate_columns(self) -> None:
        self.identifier_column.clear()
        self.criteria_checks.clear()
        clear_layout(self.criteria_layout)
        if self.dataframe is None:
            return
        preferred_identifier = 0
        for index, column in enumerate(self.dataframe.columns):
            self.identifier_column.addItem(str(column))
            if str(column).casefold() in {"devicename", "hostname", "serial", "serialnumber"}:
                preferred_identifier = index
        self.identifier_column.setCurrentIndex(preferred_identifier)
        self._render_criteria()

    def _render_criteria(self) -> None:
        clear_layout(self.criteria_layout)
        if self.dataframe is None:
            return
        preferred = ["Site", "Model", "OSVersion", "Manufacturer"]
        columns = [str(column) for column in self.dataframe.columns]
        visible = columns if self.all_criteria_visible else [column for column in preferred if column in columns]
        if not visible:
            visible = columns[:4]
        grid = QGridLayout()
        for index, column in enumerate(visible):
            checkbox = self.criteria_checks.get(column) or QCheckBox(column)
            if column not in self.criteria_checks:
                checkbox.setChecked(column in {"Site", "Model", "OSVersion"})
            self.criteria_checks[column] = checkbox
            grid.addWidget(checkbox, index // 2, index % 2)
        self.criteria_layout.addLayout(grid)

    def toggle_all_criteria(self) -> None:
        self.all_criteria_visible = not self.all_criteria_visible
        self.more_fields_button.setText("Fewer fields" if self.all_criteria_visible else "More fields")
        self._render_criteria()

    def load_exclusion_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load exclusions", "", "Text/CSV (*.txt *.csv);;All (*.*)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="cp1252")
        self.exclusion_text.setPlainText(text)
        self._update_advanced_summary()

    def generate_preview(self) -> None:
        if self.dataframe is None:
            QMessageBox.information(self, "Deployment Tools", "Choose a source file first.")
            return
        self._start_task(self._build_result, self._preview_ready, self._task_failed)

    def _build_result(self) -> RingResult:
        assert self.dataframe is not None
        base = self.dataframe
        excluded = pd.DataFrame()
        exclusion_report = None
        exclusions = self._exclusion_values()
        if exclusions:
            base, excluded, exclusion_report = apply_exclusions(base, self.identifier_column.currentText(), exclusions)
        criteria = self._selected_criteria()
        seed = self.seed_input.value()
        shuffle = self.randomize_checkbox.isChecked()
        mode_index = self.mode_stack.currentIndex()
        if mode_index == 0:
            result = build_equal_rings(base, self.simple_count.value(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        elif mode_index == 1:
            result = build_progressive_rings(base, self._progressive_definitions(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        elif mode_index == 2:
            result = build_custom_size_rings(base, self._custom_definitions(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        else:
            result = build_representative_pilot(base, self.pilot_size.value(), criteria, seed=seed)
        result.excluded_dataframe = excluded
        result.exclusion_report = exclusion_report
        return result

    def _preview_ready(self, result: object) -> None:
        self.result = result  # type: ignore[assignment]
        self._fill_preview()
        self._update_advanced_summary()

    def _selected_criteria(self) -> list[str]:
        return [column for column, checkbox in self.criteria_checks.items() if checkbox.isChecked()]

    def _exclusion_values(self) -> list[str]:
        raw_lines = self.exclusion_text.toPlainText().replace(",", "\n").replace(";", "\n").splitlines()
        return [line.strip() for line in raw_lines if line.strip()]

    def _progressive_definitions(self) -> list[RingDefinition]:
        return [
            RingDefinition(name=name.text().strip(), percentage=pct.value())
            for _, name, pct in self.progressive_rows
            if name.text().strip()
        ]

    def _custom_definitions(self) -> list[RingDefinition]:
        return [
            RingDefinition(
                name=name.text().strip(),
                size=None if remaining.isChecked() else size.value(),
                is_remaining=remaining.isChecked(),
            )
            for _, name, size, remaining in self.custom_rows
            if name.text().strip()
        ]

    def _fill_preview(self) -> None:
        clear_layout(self.ring_cards_layout)
        clear_layout(self.distribution_layout)
        if self.result is None:
            return
        self.preview_summary.setText(f"{len(self.result.dataframe):,} devices assigned")
        for index, summary in enumerate(self.result.summaries):
            card = StatCard(summary.name, f"{summary.rows:,}", f"{summary.percentage:.1f}%")
            self.ring_cards_layout.addWidget(card, index // 2, index % 2)
        criteria = self._selected_criteria()[:3]
        if criteria:
            self.distribution_layout.addWidget(SectionHeader("Distribution"))
            for column in criteria:
                self._add_distribution(column)

    def _add_distribution(self, column: str) -> None:
        if self.result is None or column not in self.result.dataframe.columns:
            return
        values = self.result.dataframe[column].fillna("Not available").astype(str).value_counts(normalize=True).head(5)
        section = Card(column)
        for value, ratio in values.items():
            row = QHBoxLayout()
            label = QLabel(str(value))
            percent = QLabel(f"{ratio * 100:.0f}%")
            track = QFrame()
            track.setObjectName("barTrack")
            track.setFixedHeight(8)
            fill = QFrame(track)
            fill.setObjectName("barFill")
            fill.setGeometry(0, 0, max(4, int(180 * ratio)), 8)
            row.addWidget(label, 1)
            row.addWidget(track)
            row.addWidget(percent)
            section.layout.addLayout(row)
        self.distribution_layout.addWidget(section)

    def _update_advanced_summary(self) -> None:
        exclusions = self._exclusion_values()
        exclusion_text = f"{len(exclusions)} exclusions" if exclusions else "No exclusions"
        self.exclusion_summary.setText(exclusion_text)
        self.advanced.set_summary(f"Seed: {self.seed_input.value()} · {exclusion_text}")

    def show_columns(self) -> None:
        if self.dataframe is None:
            return
        QMessageBox.information(self, "Columns", "\n".join(str(column) for column in self.dataframe.columns))

    def show_devices(self) -> None:
        if self.result is None:
            QMessageBox.information(self, "Devices", "Generate a preview first.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Assigned devices")
        dialog.resize(980, 620)
        layout = QVBoxLayout(dialog)
        preview = preview_rows(self.result.dataframe, DEFAULT_PREVIEW_ROWS)
        table = QTableWidget(len(preview), len(preview.columns))
        table.setHorizontalHeaderLabels([str(column) for column in preview.columns])
        for row_index, (_, row) in enumerate(preview.iterrows()):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem("" if pd.isna(value) else str(value)))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        dialog.exec()

    def select_export_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose export folder")
        if directory:
            self.export_dir.setText(directory)

    def export_result(self) -> None:
        if self.result is None:
            QMessageBox.information(self, "Export", "Generate a preview before export.")
            return
        if not self.export_dir.text().strip():
            self.select_export_dir()
        if not self.export_dir.text().strip():
            return
        options = ExportOptions(
            output_dir=Path(self.export_dir.text()),
            prefix=self.export_prefix.text().strip() or "deployment",
            file_format="xlsx" if self.export_xlsx.isChecked() else "csv",
            split_by_ring=self.export_split.isChecked(),
            include_global=self.export_global.isChecked(),
        )
        exported = export_rings(self.result, options)
        QMessageBox.information(self, "Export complete", f"{len(exported.paths)} file(s) created.")

    def _task_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Deployment Tools", message)


class IntunePage(QWidget, AsyncPageMixin):
    def __init__(self):
        super().__init__()
        self.service: IntuneDeviceInspectorService | None = None
        self.search_results: list[DeviceSearchResult] = []
        self.current_result: DeviceInspectorResult | None = None
        self.current_device_id: str | None = None
        self.thread: QThread | None = None
        self.worker: TaskWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)
        root.addWidget(SectionHeader("Device Inspector", "Search a device and see what needs attention first."))
        search_row = QHBoxLayout()
        self.search_input = SearchBox("Search device name, serial number or ID...")
        self.search_input.returnPressed.connect(self.search_devices)
        search = PrimaryButton("Search")
        search.clicked.connect(self.search_devices)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(search)
        root.addLayout(search_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        self.results_card = Card("Results")
        self.results_layout = QVBoxLayout()
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_card.layout.addLayout(self.results_layout)
        root.addWidget(self.results_card)

        self.device_card = Card()
        header_row = QHBoxLayout()
        self.device_header = QLabel("No device selected")
        self.device_header.setObjectName("pageTitle")
        self.refresh_button = SecondaryButton("Refresh")
        self.refresh_button.setToolTip("Refresh data from Microsoft Graph")
        self.refresh_button.clicked.connect(self.refresh_current_device)
        self.refresh_button.setEnabled(False)
        header_row.addWidget(self.device_header, 1)
        header_row.addWidget(self.refresh_button)
        self.device_badges = QLabel("")
        self.device_badges.setObjectName("muted")
        self.health_summary = QLabel("Search and select a device to inspect health.")
        self.health_summary.setObjectName("cardTitle")
        self.device_card.layout.addLayout(header_row)
        self.device_card.layout.addWidget(self.health_summary)
        self.device_card.layout.addWidget(self.device_badges)
        root.addWidget(self.device_card)

        self.issues_card = Card("Issues detected")
        self.issues_layout = QVBoxLayout()
        self.issues_layout.setContentsMargins(0, 0, 0, 0)
        self.issues_card.layout.addLayout(self.issues_layout)
        self.issues_layout.addWidget(EmptyState("No device selected", "Issues appear here after inspection."))
        root.addWidget(self.issues_card)

        self.detail_tabs = QTabWidget()
        self.overview_page = QWidget()
        self.overview_layout = QGridLayout(self.overview_page)
        self.compliance_page = QWidget()
        self.compliance_layout = QVBoxLayout(self.compliance_page)
        self.applications_page = QWidget()
        self.applications_layout = QVBoxLayout(self.applications_page)
        raw_page = QWidget()
        raw_layout = QVBoxLayout(raw_page)
        raw_actions = QHBoxLayout()
        copy = SecondaryButton("Copy")
        copy.clicked.connect(self.copy_raw_data)
        copy_endpoint = SecondaryButton("Copy endpoint")
        copy_endpoint.clicked.connect(self.copy_current_endpoint)
        export = SecondaryButton("Export JSON")
        export.clicked.connect(self.export_raw_data)
        export_diagnostics = SecondaryButton("Export Diagnostics")
        export_diagnostics.clicked.connect(self.export_diagnostics_bundle)
        raw_actions.addWidget(copy)
        raw_actions.addWidget(copy_endpoint)
        raw_actions.addWidget(export)
        raw_actions.addWidget(export_diagnostics)
        raw_actions.addStretch()
        self.raw_tabs = QTabWidget()
        self.raw_editors: dict[str, QPlainTextEdit] = {}
        raw_layout.addLayout(raw_actions)
        raw_layout.addWidget(self.raw_tabs)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.detail_tabs.addTab(self.overview_page, "Overview")
        self.detail_tabs.addTab(self.compliance_page, "Compliance")
        self.detail_tabs.addTab(self.applications_page, "Applications")
        self.detail_tabs.addTab(raw_page, "Raw Data")
        self.detail_tabs.addTab(self.diagnostics, "Diagnostics")
        root.addWidget(self.detail_tabs, 1)

    def _get_service(self) -> IntuneDeviceInspectorService:
        if self.service is None:
            self.service = build_intune_device_inspector()
        return self.service

    def search_devices(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        self._start_task(lambda: self._get_service().search_devices(query), self._search_ready, self._task_failed)

    def _search_ready(self, result: object) -> None:
        devices, logs = result  # type: ignore[misc]
        self.search_results = list(devices)
        clear_layout(self.results_layout)
        if not self.search_results:
            self.results_layout.addWidget(EmptyState("No results", "Try another device name."))
        for index, device in enumerate(self.search_results):
            button = QPushButton(
                f"{device.device_name}\n"
                f"{not_available(device.serial_number)} · {not_available(device.user_principal_name)} · "
                f"{not_available(device.model)} · {not_available(device.operating_system)} · "
                f"Enrolled: {not_available(device.enrolled_datetime)} · Last check-in: {relative_datetime(device.last_sync_datetime)}"
            )
            button.setObjectName("modeButton")
            button.clicked.connect(lambda _=False, row=index: self.inspect_device(row))
            self.results_layout.addWidget(button)
        self._fill_diagnostics(logs)

    def inspect_device(self, row: int) -> None:
        if row < 0 or row >= len(self.search_results):
            return
        device_id = self.search_results[row].id
        self.current_device_id = device_id
        self._start_task(lambda: self._get_service().inspect_device(device_id), self._device_ready, self._task_failed)

    def refresh_current_device(self) -> None:
        if not self.current_device_id:
            return
        self._start_task(lambda: self._get_service().inspect_device(self.current_device_id), self._device_ready, self._task_failed)

    def _device_ready(self, result: object) -> None:
        self.current_result = result  # type: ignore[assignment]
        device = self.current_result.device
        health = self.current_result.health
        self.device_header.setText(device.device_name)
        os_label = " ".join(part for part in [device.operating_system, device.os_version] if part) or "OS Not available"
        managed = "Managed" if device.is_managed else "Not Managed"
        failed_apps = len(health.failed_applications) if health else 0
        health_status = health.status if health else ("Attention" if device.issues else "Healthy")
        self.health_summary.setText(f"Health: {health_status} · {len(device.issues)} issues · {failed_apps} app failure(s)")
        self.device_badges.setText(
            f"{managed} · {not_available(device.compliance_state)} · {os_label} · "
            f"Last check-in: {relative_datetime(device.last_sync_datetime)} ({not_available(device.last_sync_datetime)})"
        )
        self.refresh_button.setEnabled(True)
        self._fill_issues(device)
        self._fill_overview(device, health)
        self._fill_compliance(device, health)
        self._fill_applications(health)
        self._fill_raw_data(health, device)
        self._fill_diagnostics(self.current_result.endpoint_logs)

    def _fill_issues(self, device: ManagedDevice) -> None:
        clear_layout(self.issues_layout)
        header = QLabel(f"Issues detected  {len(device.issues)}")
        header.setObjectName("sectionTitle")
        self.issues_layout.addWidget(header)
        if not device.issues:
            self.issues_layout.addWidget(EmptyState("No issues detected", "No deterministic issue was found from the retrieved Intune data."))
            return
        for issue in device.issues:
            card = QFrame()
            card.setObjectName("issueCritical" if issue.severity in {"CRITICAL", "ERROR"} else "issueWarning" if issue.severity == "WARNING" else "issueInfo")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            title = QLabel(f"{issue.severity} · {issue.title}")
            title.setObjectName("cardTitle")
            reason = QLabel(issue.reason)
            reason.setObjectName("muted")
            source = QLabel(f"Source: {issue.source}")
            source.setObjectName("muted")
            evidence = QLabel(f"Evidence: {issue.evidence}") if issue.evidence else None
            if evidence:
                evidence.setObjectName("muted")
            layout.addWidget(title)
            layout.addWidget(reason)
            layout.addWidget(source)
            if evidence:
                layout.addWidget(evidence)
            self.issues_layout.addWidget(card)
        self.issues_layout.addStretch()

    def _fill_overview(self, device: ManagedDevice, health: DeviceHealth | None = None) -> None:
        clear_layout(self.overview_layout)
        primary_user = device.primary_users[0].get("userPrincipalName") if device.primary_users else device.user_principal_name
        entra = health.entra_device if health else None
        groups = [
            ("IDENTITY", [
                ("Device name", device.device_name),
                ("Serial number", device.serial_number),
                ("User", primary_user),
                ("Ownership", device.owner_type),
            ]),
            ("HARDWARE", [
                ("Manufacturer", device.manufacturer),
                ("Model", device.model),
                ("Architecture", None),
            ]),
            ("WINDOWS", [
                ("OS", device.operating_system),
                ("Version", device.os_version),
                ("Enrollment", device.enrollment_type),
            ]),
            ("INTUNE", [
                ("Managed Device ID", device.id),
                ("Enrollment", device.enrollment_type),
                ("Compliance", device.compliance_state),
                ("Last check-in", device.last_sync_datetime),
                ("Management agent", device.management_agent),
            ]),
            ("ENTRA ID", [
                ("Device ID", entra.device_id if entra else device.entra_device_id),
                ("Enabled", entra.account_enabled if entra else None),
                ("Trust / Join", entra.trust_type if entra else None),
            ]),
            ("SECURITY", [
                ("Encryption state", device.is_encrypted),
                ("Jailbroken/rooted", device.jail_broken),
            ]),
        ]
        for index, (title, rows) in enumerate(groups):
            card = Card(title)
            grid = KeyValueGrid()
            grid.set_rows([(label, not_available(value)) for label, value in rows])
            card.layout.addWidget(grid)
            self.overview_layout.addWidget(card, index // 2, index % 2)

    def _fill_compliance(self, device: ManagedDevice, health: DeviceHealth | None) -> None:
        clear_layout(self.compliance_layout)
        compliance = health.compliance if health else None
        grid = KeyValueGrid()
        grid.set_rows(
            [
                ("Compliance state", not_available(compliance.state if compliance else device.compliance_state)),
                ("Grace period expiration", not_available(compliance.grace_period_expiration_datetime if compliance else None)),
                ("Detailed reason", not_available(compliance.detail if compliance else "Not available through the current Graph endpoint.")),
            ]
        )
        card = Card("Compliance")
        card.layout.addWidget(grid)
        self.compliance_layout.addWidget(card)
        self.compliance_layout.addStretch()

    def _fill_applications(self, health: DeviceHealth | None) -> None:
        clear_layout(self.applications_layout)
        if not health:
            self.applications_layout.addWidget(EmptyState("Applications not loaded", "Select a device to load application status."))
            return
        app_source = next((source for source in health.sources if source.name == "Applications"), None)
        failure_source = next((source for source in health.sources if source.name == "Application failures"), None)
        if app_source and app_source.permission_missing:
            self.applications_layout.addWidget(
                EmptyState("Application status unavailable", "Required permission: DeviceManagementManagedDevices.Read.All")
            )
            return
        apps = list(health.applications)
        if not apps:
            message = "No application records were returned for this device."
            if failure_source and failure_source.permission_missing:
                message = "Application troubleshooting details require additional permission or beta endpoint access."
            self.applications_layout.addWidget(EmptyState("No application status", message))
            return
        detected = [app for app in apps if app.kind == "detected_app"]
        deployment = [app for app in apps if app.kind == "deployment_status"]
        if deployment:
            self.applications_layout.addWidget(SectionHeader("Deployment Status", "Troubleshooting events returned by Graph."))
            self._add_application_state_groups(deployment)
        if detected:
            self.applications_layout.addWidget(SectionHeader("Detected Apps", "Inventory presence only; not proof of deployment success."))
            self._add_application_state_groups(detected)
        self.applications_layout.addStretch()

    def _add_application_state_groups(self, apps: list[ApplicationStatus]) -> None:
        order = ["failed", "pending", "installed", "not_applicable", "unknown"]
        for state in order:
            state_apps = [app for app in apps if app.install_state.casefold() == state]
            if state_apps:
                self._add_application_group(state.replace("_", " ").upper(), state_apps)

    def _add_application_group(self, title: str, apps: list[ApplicationStatus]) -> None:
        card = Card(f"{title} — {len(apps)}")
        for app in apps:
            row = QFrame()
            row.setObjectName("kvRow")
            layout = QVBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(app.name)
            name.setObjectName("cardTitle")
            detail = QLabel(
                f"Version: {not_available(app.version)} · Error: {not_available(app.error_code)}"
                + (f" · Decimal: {app.error_decimal}" if app.error_decimal is not None else " · Unknown error")
            )
            detail.setObjectName("muted")
            layout.addWidget(name)
            layout.addWidget(detail)
            card.layout.addWidget(row)
        self.applications_layout.addWidget(card)

    def _fill_raw_data(self, health: DeviceHealth | None, device: ManagedDevice) -> None:
        self.raw_tabs.clear()
        self.raw_editors = {}
        raw_sources = health.raw_sources if health else {"Intune Managed Device": device.raw}
        if "Intune Managed Device" not in raw_sources:
            raw_sources = {"Intune Managed Device": device.raw, **raw_sources}
        for title, payload in raw_sources.items():
            editor = QPlainTextEdit()
            editor.setReadOnly(True)
            editor.setPlainText(json.dumps(self._raw_payload_with_metadata(title, payload, health), indent=2, sort_keys=True))
            self.raw_tabs.addTab(editor, title)
            self.raw_editors[title] = editor

    def _raw_payload_with_metadata(self, title: str, payload: object, health: DeviceHealth | None) -> dict[str, object]:
        source = None
        if health:
            source = next((item for item in health.sources if title.casefold().startswith(item.name.split()[0].casefold())), None)
        return {
            "metadata": {
                "source": title,
                "endpoint": source.endpoint if source else None,
                "api_version": source.api_version if source else None,
                "status": source.status_code if source else None,
                "timestamp": source.response_date if source else None,
                "request_id": source.request_id if source else None,
            },
            "json": payload,
        }

    def _fill_diagnostics(self, logs) -> None:
        lines = []
        if self.current_result and self.current_result.health:
            if self.current_result.health.capabilities:
                lines.append("Capabilities")
                for capability in self.current_result.health.capabilities:
                    extra = f" · Required permission: {capability.required_permission}" if capability.required_permission else ""
                    reason = f" · {capability.reason}" if capability.reason else ""
                    lines.append(f"{capability.name}: {capability.state}{extra}{reason}")
                lines.append("")
            for source in self.current_result.health.sources:
                state = "OK" if source.available else "Unavailable"
                if source.permission_missing:
                    state = "Permission missing"
                lines.append(f"{source.name}: {state}")
                lines.append(f"API: {source.api_version}")
                lines.append(f"Endpoint: {source.endpoint}")
                lines.append(f"HTTP status: {not_available(source.status_code)}")
                lines.append(f"Duration: {source.duration_ms} ms")
                lines.append(f"Objects returned: {not_available(source.object_count)}")
                lines.append(f"Capability: {state.upper().replace(' ', '_')}")
                if source.required_permission:
                    lines.append(f"Required permission: {source.required_permission}")
                if source.request_id:
                    lines.append(f"request-id: {source.request_id}")
                if source.client_request_id:
                    lines.append(f"client-request-id: {source.client_request_id}")
                if source.response_date:
                    lines.append(f"date: {source.response_date}")
                if source.error:
                    lines.append(f"Error: {source.error}")
                lines.append("")
        for log in logs:
            source = getattr(log, "source", "Graph")
            lines.append(f"Source: {source}")
            lines.append(f"API: {getattr(log, 'api_version', 'v1.0')}")
            lines.append(f"Endpoint: {log.url}")
            lines.append(f"HTTP status: {log.status_code}")
            lines.append(f"Duration: {log.duration_ms} ms")
            lines.append(f"Objects returned: {not_available(log.object_count)}")
            if getattr(log, "request_id", None):
                lines.append(f"request-id: {log.request_id}")
            if getattr(log, "client_request_id", None):
                lines.append(f"client-request-id: {log.client_request_id}")
            if getattr(log, "response_date", None):
                lines.append(f"date: {log.response_date}")
            lines.append("")
        self.diagnostics.setPlainText("\n".join(lines).strip())

    def copy_raw_data(self) -> None:
        editor = self.raw_tabs.currentWidget()
        if isinstance(editor, QPlainTextEdit):
            QApplication.clipboard().setText(editor.toPlainText())

    def export_raw_data(self) -> None:
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Raw JSON", f"{self.current_result.device.device_name}.json", "JSON (*.json)")
        if path:
            editor = self.raw_tabs.currentWidget()
            if isinstance(editor, QPlainTextEdit):
                Path(path).write_text(editor.toPlainText(), encoding="utf-8")

    def copy_current_endpoint(self) -> None:
        if not self.current_result or not self.current_result.health:
            return
        title = self.raw_tabs.tabText(self.raw_tabs.currentIndex())
        source = next((item for item in self.current_result.health.sources if title.casefold().startswith(item.name.split()[0].casefold())), None)
        if source:
            QApplication.clipboard().setText(source.endpoint)

    def export_diagnostics_bundle(self) -> None:
        if not self.current_result:
            return
        directory = QFileDialog.getExistingDirectory(self, "Export Diagnostics")
        if not directory:
            return
        path = export_support_bundle(self.current_result, Path(directory))
        QMessageBox.information(self, "Diagnostics exported", f"Support bundle created:\n{path}")

    def _task_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Intune Device Inspector", message)
        self.diagnostics.setPlainText(message)


class SettingsPage(QWidget, AsyncPageMixin):
    def __init__(self):
        super().__init__()
        self.config_store = GraphConfigStore()
        self.secret_store = GraphSecretStore()
        self.thread: QThread | None = None
        self.worker: TaskWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)
        card = Card("Microsoft Graph", "Credentials are stored using the operating system secure credential store.")
        form = QFormLayout()
        self.tenant_id = QLineEdit()
        self.client_id = QLineEdit()
        self.client_secret = QLineEdit()
        self.client_secret.setEchoMode(QLineEdit.Password)
        self.stale_days = QSpinBox()
        self.stale_days.setRange(1, 365)
        self.stale_days.setValue(7)
        self.status = StatusBadge("Not configured", "neutral")
        form.addRow("Status", self.status)
        form.addRow("Tenant ID", self.tenant_id)
        form.addRow("Client ID", self.client_id)
        form.addRow("Client Secret", self.client_secret)
        form.addRow("Stale device threshold", self.stale_days)
        card.layout.addLayout(form)
        actions = QHBoxLayout()
        test = SecondaryButton("Test Connection")
        test.clicked.connect(self.test_connection)
        save = PrimaryButton("Save")
        save.clicked.connect(self.save_configuration)
        clear = SecondaryButton("Clear configuration")
        clear.clicked.connect(self.clear_configuration)
        actions.addWidget(test)
        actions.addWidget(save)
        actions.addWidget(clear)
        actions.addStretch()
        card.layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        card.layout.addWidget(self.progress)
        self.advanced = CollapsibleSection("Advanced / Diagnostics")
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMaximumHeight(120)
        self.advanced.content_layout.addWidget(self.diagnostics)
        card.layout.addWidget(self.advanced)
        root.addWidget(card)
        root.addStretch()
        self.load_configuration()

    def load_configuration(self) -> None:
        settings = self.config_store.load()
        if not settings:
            self.status.set_state("neutral", "Not configured")
            return
        self.tenant_id.setText(settings.tenant_id)
        self.client_id.setText(settings.client_id)
        self.stale_days.setValue(settings.stale_device_days)
        try:
            has_secret = bool(self.secret_store.get_secret(settings))
            self.status.set_state("warning" if not has_secret else "neutral", "Secret missing" if not has_secret else "Configured")
        except SecureStorageUnavailable:
            self.status.set_state("error", "Secure storage unavailable")

    def _settings_from_form(self) -> GraphSettings:
        return GraphSettings(self.tenant_id.text().strip(), self.client_id.text().strip(), self.stale_days.value())

    def save_configuration(self) -> None:
        settings = self._settings_from_form()
        if not settings.is_configured:
            QMessageBox.warning(self, "Microsoft Graph", "Tenant ID and Client ID are required.")
            return
        try:
            if self.client_secret.text().strip():
                self.secret_store.set_secret(settings, self.client_secret.text().strip())
                self.client_secret.clear()
            elif not self.secret_store.get_secret(settings):
                QMessageBox.warning(self, "Microsoft Graph", "Client Secret is required the first time you save.")
                return
            self.config_store.save(settings)
            self.status.set_state("neutral", "Saved")
        except SecureStorageUnavailable as exc:
            self.status.set_state("error", "Secure storage unavailable")
            QMessageBox.critical(self, "Microsoft Graph", exc.user_message)

    def clear_configuration(self) -> None:
        settings = self.config_store.load()
        if settings:
            try:
                self.secret_store.delete_secret(settings)
            except SecureStorageUnavailable:
                pass
        self.config_store.clear()
        self.tenant_id.clear()
        self.client_id.clear()
        self.client_secret.clear()
        self.stale_days.setValue(7)
        self.status.set_state("neutral", "Not configured")
        self.diagnostics.clear()

    def test_connection(self) -> None:
        settings = self._settings_from_form()
        try:
            secret = self.client_secret.text().strip() or self.secret_store.get_secret(settings)
        except SecureStorageUnavailable as exc:
            self._task_failed(exc.user_message)
            return
        if not settings.is_configured or not secret:
            QMessageBox.warning(self, "Microsoft Graph", "Tenant ID, Client ID and Client Secret are required.")
            return

        def task() -> GraphRequestLog:
            auth = ClientCredentialsAuth(settings, secret)
            service = IntuneDeviceInspectorService(GraphReadOnlyClient(auth), stale_device_days=settings.stale_device_days)
            return service.test_connection()

        self._start_task(task, self._connection_tested, self._task_failed)

    def _connection_tested(self, result: object) -> None:
        log = result  # type: ignore[assignment]
        self.status.set_state("success", "Connected")
        self.diagnostics.setPlainText(
            f"Endpoint: {log.url}\nHTTP status: {log.status_code}\nDuration: {log.duration_ms} ms\nObjects returned: {log.object_count}"
        )

    def _task_failed(self, message: str) -> None:
        self.status.set_state("error", "Graph Error")
        QMessageBox.critical(self, "Microsoft Graph", message)
        self.diagnostics.setPlainText(message)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Endpoint Toolbox")
        self.resize(1440, 900)
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)
        self.setCentralWidget(central)
        self.setStyleSheet(APP_STYLESHEET)
        self.nav.setCurrentRow(0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 18, 12, 12)
        brand = QLabel("Endpoint Toolbox")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        self.nav.setIconSize(self.style().standardIcon(QStyle.SP_ComputerIcon).actualSize(self.nav.iconSize()))
        layout.addWidget(self.nav, 1)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName("pageHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        self.header_title = QLabel("Home")
        self.header_title.setObjectName("pageTitle")
        self.graph_status = StatusBadge()
        header_layout.addWidget(self.header_title, 1)
        header_layout.addWidget(self.graph_status)
        layout.addWidget(header)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.pages: dict[str, QWidget] = {}
        self._add_page("Home", HomePage(self.navigate), QStyle.SP_DirHomeIcon)
        self._add_page("Intune", make_scroll_page(IntunePage()), QStyle.SP_ComputerIcon)
        self._add_page("Entra ID", make_scroll_page(PlaceholderPage("Entra ID", "Read-only inspectors will arrive in a later phase.")), QStyle.SP_FileDialogDetailedView)
        self._add_page("Autopilot", make_scroll_page(PlaceholderPage("Autopilot Inspector", "Coming soon.")), QStyle.SP_DriveHDIcon)
        self._add_page("Deployment Tools", make_scroll_page(DeploymentToolsPage()), QStyle.SP_FileDialogNewFolder)
        self._add_page("Settings", make_scroll_page(SettingsPage()), QStyle.SP_FileDialogContentsView)
        self.nav.currentRowChanged.connect(self._switch_page)
        return content

    def _add_page(self, name: str, page: QWidget, icon: QStyle.StandardPixmap) -> None:
        item = QListWidgetItem(self.style().standardIcon(icon), name)
        self.nav.addItem(item)
        self.stack.addWidget(page)
        self.pages[name] = page

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        item = self.nav.item(index)
        self.header_title.setText(item.text())
        self.refresh_graph_status()

    def navigate(self, page_name: str, mode: str | None = None) -> None:
        for index in range(self.nav.count()):
            if self.nav.item(index).text() == page_name:
                self.nav.setCurrentRow(index)
                page = self.pages[page_name]
                if isinstance(page, QScrollArea):
                    widget = page.widget()
                    if isinstance(widget, DeploymentToolsPage):
                        widget.activate_mode(mode)
                return

    def refresh_graph_status(self) -> None:
        settings = GraphConfigStore().load()
        if not settings:
            self.graph_status.set_state("neutral", "Graph Not configured")
            return
        try:
            has_secret = bool(GraphSecretStore().get_secret(settings))
        except SecureStorageUnavailable:
            self.graph_status.set_state("error", "Graph Error")
            return
        self.graph_status.set_state("success" if has_secret else "warning", "Graph Connected" if has_secret else "Graph Secret missing")


def run_app() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
