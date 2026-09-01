from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import format_size
from app.service import (
    analyze_system,
    clean_system,
    empty_recycle_bin,
)


class Worker(QObject):
    """Run backend operations outside the GUI thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        """Execute the requested operation."""
        try:
            result = self.operation(
                *self.args,
                **self.kwargs,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    """Main Clean Master window."""

    def __init__(self):
        super().__init__()

        self.analysis_result = None
        self.thread = None
        self.worker = None

        self.setWindowTitle("Clean Master")
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._apply_style()

        self.update_stats_empty()
        self.update_clean_button()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build the main interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title_layout = QVBoxLayout()

        self.title_label = QLabel("Clean Master")
        self.title_label.setObjectName("title")

        self.subtitle_label = QLabel(
            "Analiza y limpia archivos innecesarios de forma segura."
        )
        self.subtitle_label.setObjectName("subtitle")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Statistics cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        self.temp_card = self._create_stat_card(
            "TEMPORALES",
            "0 B",
        )

        self.cache_card = self._create_stat_card(
            "CACHÉ",
            "0 B",
        )

        self.logs_card = self._create_stat_card(
            "LOGS",
            "0 B",
        )

        self.total_card = self._create_stat_card(
            "TOTAL",
            "0 B",
        )

        stats_layout.addWidget(self.temp_card["frame"])
        stats_layout.addWidget(self.cache_card["frame"])
        stats_layout.addWidget(self.logs_card["frame"])
        stats_layout.addWidget(self.total_card["frame"])

        main_layout.addLayout(stats_layout)

        # Summary
        summary_frame = QFrame()
        summary_frame.setObjectName("summary_frame")

        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(20, 15, 20, 15)

        summary_text_layout = QVBoxLayout()

        summary_title = QLabel("Espacio recuperable")
        summary_title.setObjectName("summary_title")

        self.recoverable_label = QLabel("0 B")
        self.recoverable_label.setObjectName("recoverable")

        summary_text_layout.addWidget(summary_title)
        summary_text_layout.addWidget(self.recoverable_label)

        summary_layout.addLayout(summary_text_layout)
        summary_layout.addStretch()

        self.files_label = QLabel("0 archivos detectados")
        self.files_label.setObjectName("files_info")

        summary_layout.addWidget(self.files_label)

        main_layout.addWidget(summary_frame)

        # Categories
        categories_frame = QFrame()
        categories_frame.setObjectName("panel")

        categories_layout = QVBoxLayout(categories_frame)
        categories_layout.setContentsMargins(20, 15, 20, 15)
        categories_layout.setSpacing(10)

        categories_title = QLabel("Qué limpiar")
        categories_title.setObjectName("section_title")

        categories_layout.addWidget(categories_title)

        self.temporary_checkbox = QCheckBox("Archivos temporales")
        self.cache_checkbox = QCheckBox("Caché")
        self.logs_checkbox = QCheckBox("Logs")
        self.recycle_bin_checkbox = QCheckBox("Vaciar Papelera de reciclaje")

        self.temporary_checkbox.setChecked(True)
        self.cache_checkbox.setChecked(True)
        self.logs_checkbox.setChecked(True)

        self.recycle_bin_checkbox.stateChanged.connect(
            self.update_clean_button
        )

        categories_layout.addWidget(self.temporary_checkbox)
        categories_layout.addWidget(self.cache_checkbox)
        categories_layout.addWidget(self.logs_checkbox)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("separator")

        categories_layout.addWidget(separator)
        categories_layout.addWidget(self.recycle_bin_checkbox)

        main_layout.addWidget(categories_frame)

        # Status
        self.status_label = QLabel("Listo para analizar.")
        self.status_label.setObjectName("status")

        main_layout.addWidget(self.status_label)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        main_layout.addWidget(self.progress_bar)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.analyze_button = QPushButton("Analizar sistema")
        self.analyze_button.setObjectName("analyze_button")

        self.clean_button = QPushButton("Limpiar")
        self.clean_button.setObjectName("clean_button")
        self.clean_button.setEnabled(False)

        self.analyze_button.clicked.connect(self.analyze)
        self.clean_button.clicked.connect(self.clean)

        buttons_layout.addWidget(self.analyze_button)
        buttons_layout.addWidget(self.clean_button)

        main_layout.addLayout(buttons_layout)

    def _create_stat_card(self, title: str, value: str) -> dict:
        """Create one statistics card."""
        frame = QFrame()
        frame.setObjectName("stat_card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName("card_title")

        value_label = QLabel(value)
        value_label.setObjectName("card_value")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return {
            "frame": frame,
            "value": value_label,
        }

    def _apply_style(self):
        """Apply the Clean Master dark theme."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0f172a;
            }

            QWidget {
                color: #e2e8f0;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#title {
                font-size: 28px;
                font-weight: 700;
                color: #e2e8f0;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #94a3b8;
                margin-top: 2px;
            }

            QFrame#stat_card {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }

            QLabel#card_title {
                font-size: 11px;
                font-weight: 700;
                color: #94a3b8;
            }

            QLabel#card_value {
                font-size: 21px;
                font-weight: 700;
                color: #38bdf8;
            }

            QFrame#summary_frame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }

            QLabel#summary_title {
                color: #94a3b8;
                font-size: 13px;
            }

            QLabel#recoverable {
                color: #38bdf8;
                font-size: 25px;
                font-weight: 700;
            }

            QLabel#files_info {
                color: #94a3b8;
                font-size: 13px;
            }

            QFrame#panel {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }

            QLabel#section_title {
                font-size: 16px;
                font-weight: 700;
                color: #e2e8f0;
            }

            QCheckBox {
                spacing: 10px;
                color: #e2e8f0;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }

            QCheckBox::indicator:unchecked {
                background-color: #0f172a;
                border: 1px solid #475569;
                border-radius: 4px;
            }

            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 4px;
            }

            QFrame#separator {
                background-color: #334155;
                max-height: 1px;
            }

            QLabel#status {
                color: #94a3b8;
                font-size: 13px;
            }

            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                height: 10px;
            }

            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 5px;
            }

            QPushButton {
                min-height: 42px;
                border-radius: 8px;
                font-weight: 700;
                padding-left: 18px;
                padding-right: 18px;
            }

            QPushButton#analyze_button {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #475569;
            }

            QPushButton#analyze_button:hover {
                background-color: #334155;
            }

            QPushButton#clean_button {
                background-color: #38bdf8;
                color: #0f172a;
                border: none;
            }

            QPushButton#clean_button:hover {
                background-color: #7dd3fc;
            }

            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
            }
            """
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def update_stats_empty(self):
        """Reset all displayed statistics."""
        self._set_card_value(self.temp_card, "0 B")
        self._set_card_value(self.cache_card, "0 B")
        self._set_card_value(self.logs_card, "0 B")
        self._set_card_value(self.total_card, "0 B")

        self.recoverable_label.setText("0 B")
        self.files_label.setText("0 archivos detectados")

    def update_clean_button(self):
        """Enable the clean button when there is something to do."""
        has_analysis = self.analysis_result is not None
        has_recycle_bin = self.recycle_bin_checkbox.isChecked()

        self.clean_button.setEnabled(
            has_analysis or has_recycle_bin
        )

    def _set_card_value(self, card: dict, value: str):
        """Update a statistics card."""
        card["value"].setText(value)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self):
        """Start system analysis."""
        if self.thread is not None:
            return

        self.analysis_result = None
        self.update_stats_empty()

        self.analyze_button.setEnabled(False)
        self.clean_button.setEnabled(False)

        self.status_label.setText(
            "Analizando el sistema..."
        )

        self.progress_bar.setRange(0, 0)

        self._start_worker(
            analyze_system,
            self.analysis_finished,
            self.operation_error,
        )

    def analysis_finished(self, result):
        """Handle completed system analysis."""
        self.analysis_result = result

        categories = result["categories"]

        self._set_card_value(
            self.temp_card,
            format_size(categories["temporary"]["size"]),
        )

        self._set_card_value(
            self.cache_card,
            format_size(categories["cache"]["size"]),
        )

        self._set_card_value(
            self.logs_card,
            format_size(categories["logs"]["size"]),
        )

        self._set_card_value(
            self.total_card,
            format_size(result["total"]["size"]),
        )

        self.recoverable_label.setText(
            format_size(result["total"]["size"])
        )

        self.files_label.setText(
            f'{result["total"]["files"]} archivos detectados'
        )

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        self.status_label.setText(
            "Análisis completado."
        )

        self.analyze_button.setEnabled(True)
        self.update_clean_button()

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean(self):
        """Start the selected cleanup operations."""
        selected_categories = []

        if self.temporary_checkbox.isChecked():
            selected_categories.append("temporary")

        if self.cache_checkbox.isChecked():
            selected_categories.append("cache")

        if self.logs_checkbox.isChecked():
            selected_categories.append("logs")

        empty_recycle_bin_selected = (
            self.recycle_bin_checkbox.isChecked()
        )

        if not selected_categories and not empty_recycle_bin_selected:
            QMessageBox.information(
                self,
                "Clean Master",
                "Seleccioná al menos una categoría para limpiar.",
            )
            return

        if empty_recycle_bin_selected:
            answer = QMessageBox.warning(
                self,
                "Vaciar Papelera",
                (
                    "La Papelera de reciclaje se vaciará "
                    "completamente y esta acción no se puede deshacer.\n\n"
                    "¿Querés continuar?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if answer != QMessageBox.Yes:
                self.recycle_bin_checkbox.setChecked(False)

                if not selected_categories:
                    self.update_clean_button()

                return

        self.analyze_button.setEnabled(False)
        self.clean_button.setEnabled(False)

        self.status_label.setText(
            "Limpiando el sistema..."
        )

        self.progress_bar.setRange(0, 0)

        self._start_clean_worker(
            selected_categories,
            empty_recycle_bin_selected,
        )

    def _start_clean_worker(
        self,
        selected_categories: list[str],
        empty_recycle_bin_selected: bool,
    ):
        """Start cleanup operations."""
        self.thread = QThread()
        self.worker = CleanWorker(
            self.analysis_result,
            selected_categories,
            empty_recycle_bin_selected,
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(
            self.clean_finished
        )

        self.worker.error.connect(
            self.operation_error
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.error.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self._worker_finished
        )

        self.thread.start()

    def clean_finished(self, result):
        """Handle completed cleanup."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        self.analysis_result = None

        deleted = result["cleanup"]["deleted"]
        freed = result["cleanup"]["freed"]
        skipped = result["cleanup"]["skipped"]
        errors = result["cleanup"]["errors"]

        message = (
            f"Archivos eliminados: {deleted}\n"
            f"Espacio liberado: {format_size(freed)}\n"
            f"Archivos omitidos: {skipped}\n"
            f"Errores: {errors}"
        )

        if result["recycle_bin"]:
            recycle_success = result["recycle_bin"]["success"]

            if recycle_success:
                message += "\n\nPapelera de reciclaje: vaciada."
            else:
                message += (
                    "\n\n"
                    "Papelera de reciclaje: no se pudo vaciar."
                )

        self.status_label.setText(
            "Limpieza completada."
        )

        self.analyze_button.setEnabled(True)
        self.recycle_bin_checkbox.setChecked(False)

        self.update_stats_empty()
        self.update_clean_button()

        QMessageBox.information(
            self,
            "Limpieza completada",
            message,
        )

    # ------------------------------------------------------------------
    # Worker infrastructure
    # ------------------------------------------------------------------

    def _start_worker(
        self,
        operation,
        success_callback,
        error_callback,
    ):
        """Start a generic worker thread."""
        self.thread = QThread()
        self.worker = Worker(operation)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.finished.connect(
            success_callback
        )

        self.worker.error.connect(
            error_callback
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.error.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self._worker_finished
        )

        self.thread.start()

    def _worker_finished(self):
        """Release worker references after thread completion."""
        self.thread.deleteLater()
        self.worker.deleteLater()

        self.thread = None
        self.worker = None

    def operation_error(self, message: str):
        """Handle backend errors."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label.setText(
            "Se produjo un error."
        )

        self.analyze_button.setEnabled(True)
        self.update_clean_button()

        QMessageBox.critical(
            self,
            "Error",
            f"No se pudo completar la operación:\n\n{message}",
        )


class CleanWorker(QObject):
    """Worker for system cleanup and optional recycle bin emptying."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        analysis_result,
        selected_categories,
        empty_recycle_bin_selected,
    ):
        super().__init__()

        self.analysis_result = analysis_result
        self.selected_categories = selected_categories
        self.empty_recycle_bin_selected = (
            empty_recycle_bin_selected
        )

    @Slot()
    def run(self):
        """Run cleanup operations."""
        try:
            cleanup_result = {
                "deleted": 0,
                "freed": 0,
                "skipped": 0,
                "errors": 0,
            }

            recycle_result = None

            if self.selected_categories and self.analysis_result:
                cleanup_result = clean_system(
                    self.analysis_result,
                    selected_categories=self.selected_categories,
                )

            if self.empty_recycle_bin_selected:
                recycle_result = empty_recycle_bin()

            self.finished.emit(
                {
                    "cleanup": cleanup_result,
                    "recycle_bin": recycle_result,
                }
            )

        except Exception as exc:
            self.error.emit(str(exc))

