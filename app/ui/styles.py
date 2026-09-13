APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #f4f6f8;
    color: #1f2937;
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background: #101827;
}
QLabel#brand {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
}
QListWidget#navList {
    background: transparent;
    color: #cbd5e1;
    border: none;
    outline: none;
}
QListWidget#navList::item {
    padding: 11px 12px;
    margin: 3px 8px;
    border-radius: 8px;
}
QListWidget#navList::item:selected {
    background: #2563eb;
    color: white;
}
QFrame#pageHeader {
    background: #f4f6f8;
    border-bottom: 1px solid #e1e7ef;
}
QLabel#pageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
}
QLabel#pageSubtitle, QLabel#muted, QLabel[objectName="muted"] {
    color: #6b7280;
}
QLabel#sectionTitle {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
}
QFrame#card, QFrame#statCard, QFrame#emptyState, QFrame#collapsible {
    background: #ffffff;
    border: 1px solid #dbe3ec;
    border-radius: 10px;
}
QFrame#clickCard {
    background: #ffffff;
    border: 1px solid #dbe3ec;
    border-radius: 10px;
}
QLabel#cardTitle {
    color: #111827;
    font-size: 14px;
    font-weight: 700;
}
QLabel#emptyTitle {
    color: #111827;
    font-size: 17px;
    font-weight: 700;
}
QLabel#statValue {
    color: #111827;
    font-size: 26px;
    font-weight: 800;
}
QLabel#statusBadge {
    border-radius: 12px;
    padding: 5px 10px;
    font-weight: 600;
}
QLabel#statusBadge[state="success"] {
    background: #ecfdf3;
    color: #027a48;
}
QLabel#statusBadge[state="warning"] {
    background: #fffaeb;
    color: #b54708;
}
QLabel#statusBadge[state="error"] {
    background: #fef3f2;
    color: #b42318;
}
QLabel#statusBadge[state="neutral"] {
    background: #eef2f6;
    color: #475467;
}
QPushButton {
    background: #ffffff;
    color: #344054;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton:hover {
    background: #f8fafc;
}
QPushButton#primaryButton {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
    font-weight: 700;
}
QPushButton#secondaryButton {
    background: #ffffff;
}
QPushButton#modeButton {
    text-align: left;
    min-height: 54px;
    padding: 10px 12px;
    border: 1px solid #dbe3ec;
    background: #ffffff;
}
QPushButton#modeButton:checked {
    border: 2px solid #2563eb;
    background: #eff6ff;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 9px;
}
QLineEdit#searchBox {
    min-height: 38px;
    font-size: 15px;
    padding: 9px 12px;
}
QProgressBar {
    border: none;
    background: #e5eaf1;
    border-radius: 4px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 4px;
}
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    background: transparent;
    color: #667085;
    padding: 9px 12px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #2563eb;
    border-bottom: 2px solid #2563eb;
}
QTableWidget {
    background: #ffffff;
    border: 1px solid #dbe3ec;
    border-radius: 8px;
    gridline-color: #eef2f6;
}
QHeaderView::section {
    background: #f8fafc;
    color: #475467;
    border: none;
    border-bottom: 1px solid #e5eaf1;
    padding: 8px;
}
QFrame#dropZone {
    background: #ffffff;
    border: 1px dashed #9aa8b8;
    border-radius: 12px;
    min-height: 156px;
}
QFrame#compactRow {
    background: #f8fafc;
    border: 1px solid #e5eaf1;
    border-radius: 8px;
}
QFrame#issueCritical {
    background: #fef3f2;
    border: 1px solid #fecdca;
    border-radius: 10px;
}
QFrame#issueWarning {
    background: #fffaeb;
    border: 1px solid #fedf89;
    border-radius: 10px;
}
QFrame#issueInfo {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
}
QFrame#barTrack {
    background: #eef2f6;
    border-radius: 4px;
}
QFrame#barFill {
    background: #2563eb;
    border-radius: 4px;
}
QFrame#collapsibleHeader {
    background: transparent;
}
QToolButton {
    border: none;
    background: transparent;
    color: #475467;
    font-weight: 700;
}
"""
