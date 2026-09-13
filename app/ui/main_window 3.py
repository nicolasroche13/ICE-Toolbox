from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pandas as pd
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
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
    QSpinBox,
    QStackedWidget,
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
from app.io.exporters import export_rings
from app.io.tables import load_table, preview_rows
from app.models.deployment import ExportOptions, RingDefinition, RingResult


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
        except Exception as exc:
            self.failed.emit(str(exc))


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setObjectName("pageSubtitle")
        note = QLabel("Module reserve pour une phase ulterieure. V1 Microsoft reste strictement read-only.")
        note.setObjectName("emptyState")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(note)
        layout.addStretch()


class DropZone(QFrame):
    fileDropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        layout = QVBoxLayout(self)
        title = QLabel("Glisser un CSV/XLSX/XLSM ici")
        title.setObjectName("dropTitle")
        subtitle = QLabel("ou selectionner un fichier depuis le bouton d'import")
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


class DeploymentToolsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dataframe: pd.DataFrame | None = None
        self.filtered_dataframe: pd.DataFrame | None = None
        self.result: RingResult | None = None
        self.source_path: Path | None = None
        self.thread: QThread | None = None
        self.worker: TaskWorker | None = None

        self.setAcceptDrops(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Deployment Tools")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Preparation locale de lots, rings progressifs, exclusions et pilotes representatifs.")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        self.status_label = QLabel("Pret")
        self.status_label.setObjectName("statusPill")
        header.addWidget(self.status_label)
        root.addLayout(header)

        top_grid = QGridLayout()
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 2)
        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self.load_file)
        top_grid.addWidget(self.drop_zone, 0, 0, 2, 1)

        file_actions = QHBoxLayout()
        load_button = QPushButton("Importer")
        load_button.clicked.connect(self.select_file)
        self.file_label = QLabel("Aucun fichier charge")
        self.file_label.setObjectName("infoBox")
        file_actions.addWidget(load_button)
        file_actions.addWidget(self.file_label, 1)
        top_grid.addLayout(file_actions, 0, 1)

        self.columns_list = QListWidget()
        self.columns_list.setObjectName("compactList")
        top_grid.addWidget(self.columns_list, 1, 1)
        root.addLayout(top_grid)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_simple_tab(), "Simple Split")
        self.tabs.addTab(self._build_progressive_tab(), "Progressive Rings")
        self.tabs.addTab(self._build_custom_tab(), "Custom Sizes")
        self.tabs.addTab(self._build_pilot_tab(), "Representative Pilot")
        root.addWidget(self.tabs)

        options = QHBoxLayout()
        self.shuffle_checkbox = QCheckBox("Melange deterministe")
        self.shuffle_checkbox.setChecked(True)
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 999999999)
        self.seed_input.setValue(DEFAULT_RANDOM_SEED)
        options.addWidget(self.shuffle_checkbox)
        options.addWidget(QLabel("Seed"))
        options.addWidget(self.seed_input)
        options.addWidget(QLabel("Stratification"))
        self.criteria_list = QListWidget()
        self.criteria_list.setObjectName("criteriaList")
        options.addWidget(self.criteria_list, 1)
        root.addLayout(options)

        exclusion_box = QGroupBox("Exclusions")
        exclusion_layout = QGridLayout(exclusion_box)
        self.identifier_column = QComboBox()
        self.exclusion_text = QPlainTextEdit()
        self.exclusion_text.setPlaceholderText("Coller une liste de devices/serials a exclure, un par ligne")
        self.exclusion_text.setMaximumHeight(72)
        exclusion_file_button = QPushButton("Charger une liste")
        exclusion_file_button.clicked.connect(self.load_exclusion_file)
        self.exclusion_report_label = QLabel("Aucune exclusion appliquee")
        self.exclusion_report_label.setObjectName("muted")
        exclusion_layout.addWidget(QLabel("Colonne identifiant"), 0, 0)
        exclusion_layout.addWidget(self.identifier_column, 0, 1)
        exclusion_layout.addWidget(exclusion_file_button, 0, 2)
        exclusion_layout.addWidget(self.exclusion_text, 1, 0, 1, 3)
        exclusion_layout.addWidget(self.exclusion_report_label, 2, 0, 1, 3)
        root.addWidget(exclusion_box)

        actions = QHBoxLayout()
        preview_button = QPushButton("Generer la preview")
        preview_button.setObjectName("primaryButton")
        preview_button.clicked.connect(self.generate_preview)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        actions.addWidget(preview_button)
        actions.addWidget(self.progress, 1)
        root.addLayout(actions)

        preview_split = QHBoxLayout()
        self.summary_table = QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(["Ring", "Devices", "%", "Criteres distincts"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table = QTableWidget(0, 0)
        self.preview_table.setObjectName("dataPreview")
        preview_split.addWidget(self.summary_table, 2)
        preview_split.addWidget(self.preview_table, 3)
        root.addLayout(preview_split, 1)

        export_box = QGroupBox("Export")
        export_layout = QHBoxLayout(export_box)
        self.export_dir = QLineEdit()
        self.export_prefix = QLineEdit("deployment")
        self.export_format = QComboBox()
        self.export_format.addItems(["xlsx", "csv"])
        self.export_global = QCheckBox("Global")
        self.export_global.setChecked(True)
        self.export_split = QCheckBox("Par ring")
        self.export_split.setChecked(True)
        choose_dir = QPushButton("Dossier")
        choose_dir.clicked.connect(self.select_export_dir)
        export_button = QPushButton("Exporter")
        export_button.clicked.connect(self.export_result)
        export_button.setObjectName("primaryButton")
        export_layout.addWidget(QLabel("Dossier"))
        export_layout.addWidget(self.export_dir, 2)
        export_layout.addWidget(choose_dir)
        export_layout.addWidget(QLabel("Prefixe"))
        export_layout.addWidget(self.export_prefix)
        export_layout.addWidget(self.export_format)
        export_layout.addWidget(self.export_global)
        export_layout.addWidget(self.export_split)
        export_layout.addWidget(export_button)
        root.addWidget(export_box)

    def _build_simple_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.simple_count = QSpinBox()
        self.simple_count.setRange(1, 50)
        self.simple_count.setValue(5)
        layout.addRow("Nombre de rings", self.simple_count)
        return page

    def _build_progressive_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.progressive_table = QTableWidget(5, 2)
        self.progressive_table.setHorizontalHeaderLabels(["Nom", "Pourcentage"])
        for row, values in enumerate([("Pilot", "2"), ("Ring 1", "8"), ("Ring 2", "20"), ("Ring 3", "30"), ("Broad", "40")]):
            self.progressive_table.setItem(row, 0, QTableWidgetItem(values[0]))
            self.progressive_table.setItem(row, 1, QTableWidgetItem(values[1]))
        self.progressive_total = QLabel("Total : 100%")
        add_button = QPushButton("Ajouter")
        add_button.clicked.connect(lambda: self.progressive_table.insertRow(self.progressive_table.rowCount()))
        remove_button = QPushButton("Supprimer")
        remove_button.clicked.connect(lambda: self.progressive_table.removeRow(max(0, self.progressive_table.currentRow())))
        self.progressive_table.itemChanged.connect(self.update_progressive_total)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addWidget(self.progressive_total)
        buttons.addStretch()
        layout.addWidget(self.progressive_table)
        layout.addLayout(buttons)
        return page

    def _build_custom_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.custom_table = QTableWidget(4, 3)
        self.custom_table.setHorizontalHeaderLabels(["Nom", "Taille", "Remaining"])
        for row, values in enumerate([("Pilot", "50", False), ("Ring 1", "200", False), ("Ring 2", "500", False), ("Broad", "", True)]):
            self.custom_table.setItem(row, 0, QTableWidgetItem(values[0]))
            self.custom_table.setItem(row, 1, QTableWidgetItem(values[1]))
            item = QTableWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if values[2] else Qt.Unchecked)
            self.custom_table.setItem(row, 2, item)
        add_button = QPushButton("Ajouter")
        add_button.clicked.connect(lambda: self.custom_table.insertRow(self.custom_table.rowCount()))
        remove_button = QPushButton("Supprimer")
        remove_button.clicked.connect(lambda: self.custom_table.removeRow(max(0, self.custom_table.currentRow())))
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addWidget(self.custom_table)
        layout.addLayout(buttons)
        return page

    def _build_pilot_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.pilot_size = QSpinBox()
        self.pilot_size.setRange(1, 1_000_000)
        self.pilot_size.setValue(100)
        self.pilot_summary_label = QLabel("Score disponible apres generation.")
        self.pilot_summary_label.setObjectName("muted")
        layout.addRow("Taille du pilote", self.pilot_size)
        layout.addRow("Score", self.pilot_summary_label)
        return page

    def select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selectionner un fichier", "", "Fichiers (*.csv *.xlsx *.xlsm)")
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        source = Path(path)
        self._start_task(lambda: load_table(source), self._file_loaded, f"Chargement de {source.name}...")
        self.source_path = source

    def _file_loaded(self, result: object) -> None:
        self.dataframe = result  # type: ignore[assignment]
        self.filtered_dataframe = self.dataframe
        self.result = None
        assert self.dataframe is not None
        self.file_label.setText(f"{self.source_path.name if self.source_path else 'source'} - {len(self.dataframe):,} lignes - {len(self.dataframe.columns)} colonnes")
        self.export_prefix.setText(self.source_path.stem if self.source_path else "deployment")
        self._populate_columns()
        self._fill_dataframe_preview(self.dataframe)
        self.status_label.setText("Fichier charge")

    def _populate_columns(self) -> None:
        self.columns_list.clear()
        self.criteria_list.clear()
        self.identifier_column.clear()
        if self.dataframe is None:
            return
        preferred_identifier = 0
        for index, column in enumerate(self.dataframe.columns):
            self.columns_list.addItem(f"{column} ({self.dataframe[column].dtype})")
            criteria_item = QListWidgetItem(str(column))
            criteria_item.setFlags(criteria_item.flags() | Qt.ItemIsUserCheckable)
            criteria_item.setCheckState(Qt.Unchecked)
            self.criteria_list.addItem(criteria_item)
            self.identifier_column.addItem(str(column))
            if str(column).casefold() in {"devicename", "hostname", "serial", "serialnumber"}:
                preferred_identifier = index
        self.identifier_column.setCurrentIndex(preferred_identifier)

    def load_exclusion_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Charger une liste d'exclusions", "", "Text/CSV (*.txt *.csv);;Tous (*.*)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="cp1252")
        self.exclusion_text.setPlainText(text)

    def generate_preview(self) -> None:
        if self.dataframe is None:
            QMessageBox.information(self, "Deployment Tools", "Importez d'abord un fichier.")
            return
        self._start_task(self._build_result, self._preview_ready, "Generation en cours...")

    def _build_result(self) -> RingResult:
        assert self.dataframe is not None
        exclusions = self._exclusion_values()
        base = self.dataframe
        excluded = pd.DataFrame()
        exclusion_report = None
        if exclusions:
            base, excluded, exclusion_report = apply_exclusions(base, self.identifier_column.currentText(), exclusions)
        criteria = self._selected_criteria()
        tab_index = self.tabs.currentIndex()
        seed = self.seed_input.value()
        shuffle = self.shuffle_checkbox.isChecked()
        if tab_index == 0:
            result = build_equal_rings(base, self.simple_count.value(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        elif tab_index == 1:
            result = build_progressive_rings(base, self._progressive_definitions(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        elif tab_index == 2:
            result = build_custom_size_rings(base, self._custom_definitions(), shuffle=shuffle, seed=seed, stratify_columns=criteria)
        else:
            result = build_representative_pilot(base, self.pilot_size.value(), criteria, seed=seed)
        result.excluded_dataframe = excluded
        result.exclusion_report = exclusion_report
        return result

    def _preview_ready(self, result: object) -> None:
        self.result = result  # type: ignore[assignment]
        assert self.result is not None
        self._fill_summary(self.result)
        self._fill_dataframe_preview(self.result.dataframe)
        self._fill_exclusion_report(self.result)
        self._fill_pilot_summary(self.result)
        self.status_label.setText("Preview prete")

    def _selected_criteria(self) -> list[str]:
        selected: list[str] = []
        for row in range(self.criteria_list.count()):
            item = self.criteria_list.item(row)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def _exclusion_values(self) -> list[str]:
        raw_lines = self.exclusion_text.toPlainText().replace(",", "\n").replace(";", "\n").splitlines()
        return [line.strip() for line in raw_lines if line.strip()]

    def _progressive_definitions(self) -> list[RingDefinition]:
        definitions: list[RingDefinition] = []
        for row in range(self.progressive_table.rowCount()):
            name_item = self.progressive_table.item(row, 0)
            pct_item = self.progressive_table.item(row, 1)
            if not name_item or not name_item.text().strip():
                continue
            definitions.append(RingDefinition(name=name_item.text().strip(), percentage=float(pct_item.text() if pct_item else 0)))
        return definitions

    def _custom_definitions(self) -> list[RingDefinition]:
        definitions: list[RingDefinition] = []
        for row in range(self.custom_table.rowCount()):
            name_item = self.custom_table.item(row, 0)
            size_item = self.custom_table.item(row, 1)
            rest_item = self.custom_table.item(row, 2)
            if not name_item or not name_item.text().strip():
                continue
            is_remaining = bool(rest_item and rest_item.checkState() == Qt.Checked)
            size = None if is_remaining or not size_item or not size_item.text().strip() else int(size_item.text())
            definitions.append(RingDefinition(name=name_item.text().strip(), size=size, is_remaining=is_remaining))
        return definitions

    def update_progressive_total(self) -> None:
        try:
            total = sum(float(self.progressive_table.item(row, 1).text()) for row in range(self.progressive_table.rowCount()) if self.progressive_table.item(row, 1))
            self.progressive_total.setText(f"Total : {total:g}%")
        except ValueError:
            self.progressive_total.setText("Total : invalide")

    def _fill_summary(self, result: RingResult) -> None:
        self.summary_table.setRowCount(len(result.summaries))
        for row, summary in enumerate(result.summaries):
            self.summary_table.setItem(row, 0, QTableWidgetItem(summary.name))
            self.summary_table.setItem(row, 1, QTableWidgetItem(str(summary.rows)))
            self.summary_table.setItem(row, 2, QTableWidgetItem(f"{summary.percentage:.2f}%"))
            details = ", ".join(f"{key}: {value}" for key, value in summary.distinct_values.items())
            self.summary_table.setItem(row, 3, QTableWidgetItem(details or "-"))

    def _fill_dataframe_preview(self, dataframe: pd.DataFrame) -> None:
        preview = preview_rows(dataframe, DEFAULT_PREVIEW_ROWS)
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels([str(column) for column in preview.columns])
        for row_index, (_, row) in enumerate(preview.iterrows()):
            for column_index, value in enumerate(row):
                self.preview_table.setItem(row_index, column_index, QTableWidgetItem("" if pd.isna(value) else str(value)))
        self.preview_table.resizeColumnsToContents()

    def _fill_exclusion_report(self, result: RingResult) -> None:
        report = result.exclusion_report
        if report is None:
            self.exclusion_report_label.setText("Aucune exclusion appliquee")
            return
        self.exclusion_report_label.setText(
            f"Demandes: {report.requested_count} - exclus: {report.excluded_count} - non trouves: {len(report.not_found)} - doublons source: {report.duplicate_rows}"
        )

    def _fill_pilot_summary(self, result: RingResult) -> None:
        summary = result.pilot_summary
        if summary is None:
            self.pilot_summary_label.setText("Score disponible apres generation.")
            return
        coverage = ", ".join(f"{column}: {value:.0f}%" for column, value in summary.coverage_by_column.items())
        self.pilot_summary_label.setText(f"Score {summary.representativity_score:.2f}/100 - couverture {coverage or 'n/a'}")

    def select_export_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier d'export")
        if directory:
            self.export_dir.setText(directory)

    def export_result(self) -> None:
        if self.result is None:
            QMessageBox.information(self, "Export", "Generez une preview avant export.")
            return
        if not self.export_dir.text().strip():
            self.select_export_dir()
        if not self.export_dir.text().strip():
            return
        options = ExportOptions(
            output_dir=Path(self.export_dir.text()),
            prefix=self.export_prefix.text().strip() or "deployment",
            file_format=self.export_format.currentText(),  # type: ignore[arg-type]
            split_by_ring=self.export_split.isChecked(),
            include_global=self.export_global.isChecked(),
        )
        exported = export_rings(self.result, options)
        QMessageBox.information(self, "Export termine", f"{len(exported.paths)} fichier(s) cree(s).")

    def _start_task(self, task: Callable[[], object], on_success: Callable[[object], None], status: str) -> None:
        self.status_label.setText(status)
        self.progress.show()
        self.thread = QThread(self)
        self.worker = TaskWorker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(on_success)
        self.worker.finished.connect(self._task_finished)
        self.worker.failed.connect(self._task_failed)
        self.thread.start()

    def _task_finished(self) -> None:
        self.progress.hide()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.thread = None
        self.worker = None

    def _task_failed(self, message: str) -> None:
        self.status_label.setText("Erreur")
        QMessageBox.critical(self, "Erreur", message)
        self._task_finished()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Endpoint Toolbox")
        self.resize(1440, 900)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(220)
        self.stack = QStackedWidget()

        sections = [
            ("Home", PlaceholderPage("Endpoint Toolbox", "Console desktop locale pour ingenieurs Endpoint et Microsoft 365.")),
            ("Intune", PlaceholderPage("Intune", "Device Inspector, politiques et sante parc arriveront apres le socle local.")),
            ("Entra ID", PlaceholderPage("Entra ID", "Exploration read-only des users, groupes et applications prevue en phase ulterieure.")),
            ("Autopilot", PlaceholderPage("Autopilot", "Analyse read-only de flotte et deploiement Autopilot prevue plus tard.")),
            ("Deployment Tools", DeploymentToolsPage()),
            ("Settings", PlaceholderPage("Settings", "Parametres locaux uniquement. Aucun secret ni tenant ID n'est stocke en dur.")),
        ]

        for name, page in sections:
            self.nav.addItem(QListWidgetItem(name))
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.setStyleSheet(APP_STYLESHEET)


APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #f5f6f8;
    color: #1f2933;
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
}
QListWidget {
    background: #17202a;
    color: #d9e2ec;
    border: none;
    padding: 12px 10px;
}
QListWidget::item {
    padding: 10px 12px;
    margin: 2px 0;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #2f80ed;
    color: white;
}
QLabel#pageTitle {
    font-size: 24px;
    font-weight: 700;
}
QLabel#pageSubtitle, QLabel#muted {
    color: #607080;
}
QLabel#emptyState, QLabel#infoBox {
    background: white;
    border: 1px solid #d7dde5;
    border-radius: 6px;
    padding: 12px;
}
QLabel#statusPill {
    background: #e8f1ff;
    color: #195bbf;
    border: 1px solid #b8d4ff;
    border-radius: 6px;
    padding: 6px 10px;
}
QFrame#dropZone {
    background: #ffffff;
    border: 1px dashed #9aa8b8;
    border-radius: 6px;
    min-height: 104px;
}
QLabel#dropTitle {
    font-size: 15px;
    font-weight: 600;
}
QPushButton {
    background: white;
    border: 1px solid #c8d1dc;
    border-radius: 6px;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #eef3f8;
}
QPushButton#primaryButton {
    background: #2f80ed;
    color: white;
    border: 1px solid #2f80ed;
}
QTableWidget, QPlainTextEdit, QLineEdit, QComboBox, QSpinBox, QTabWidget::pane, QGroupBox {
    background: white;
    border: 1px solid #d7dde5;
    border-radius: 6px;
}
QGroupBox {
    margin-top: 8px;
    padding: 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QHeaderView::section {
    background: #eef2f6;
    color: #344054;
    padding: 6px;
    border: none;
    border-right: 1px solid #d7dde5;
}
QListWidget#compactList, QListWidget#criteriaList {
    background: white;
    color: #1f2933;
    border: 1px solid #d7dde5;
    border-radius: 6px;
}
QListWidget#criteriaList {
    max-height: 86px;
}
"""


def run_app() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
