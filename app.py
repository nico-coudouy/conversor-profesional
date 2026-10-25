import sys
import os
import subprocess

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QComboBox, QProgressBar, QListWidget, QPushButton, QMessageBox,
    QFileDialog, QTextEdit, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from worker import ConvertWorker

VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mts", ".mxf"}


class DropWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conversor Profesional")
        self.setFixedSize(750, 700)
        self.setAcceptDrops(True)
        self.output_folder = ""

        # ======== Tema oscuro y estilos ========
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #f0f0f0; font-family: 'Segoe UI'; }
            QPushButton { background-color: #0078d7; color: white; border-radius: 6px; padding: 2px 10px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:disabled { background-color: #444; color: #888; }
            QProgressBar { border: 1px solid #555; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #00bfff; border-radius: 6px; }
            QComboBox, QLineEdit, QTextEdit { background-color: #2e2e2e; border: 1px solid #555; border-radius: 4px; color: #ffffff; padding: 2px 6px; }
            QLabel { font-size: 10pt; }
        """)

        main_layout = QVBoxLayout()

        # ======== Archivos ========
        files_group = QGroupBox("📂 Archivos / Links")
        files_layout = QVBoxLayout()

        self.select_files_button = QPushButton("📁 Seleccionar archivos")
        self.select_files_button.clicked.connect(self.select_files)

        self.label = QLabel("Arrastrá archivos aquí")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed #888; padding: 40px; font-size: 12pt;")

        self.video_link = QLineEdit()
        self.video_link.setPlaceholderText("Pegar link de YouTube / Instagram / etc.")

        self.download_button = QPushButton("📥 Descargar / Convertir")
        self.download_button.clicked.connect(self.handle_video_link)

        self.quality_box = QComboBox()
        self.quality_box.addItems(["⚡ Proxy", "▶️ YouTube", "🎞️ Alta calidad", "💾 Liviano"])

        files_layout.addWidget(self.select_files_button)
        files_layout.addWidget(self.label)
        files_layout.addWidget(QLabel("🎚️ Calidad:"))
        files_layout.addWidget(self.quality_box)
        files_layout.addWidget(self.video_link)
        files_layout.addWidget(self.download_button)
        files_group.setLayout(files_layout)

        # ======== Carpeta destino ========
        folder_group = QGroupBox("📁 Carpeta de salida")
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Carpeta actual: carpeta del programa")
        self.folder_button = QPushButton("Elegir carpeta")
        self.folder_button.clicked.connect(self.select_output_folder)
        self.open_folder_button = QPushButton("Abrir carpeta")
        self.open_folder_button.clicked.connect(self.open_output_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_button)
        folder_layout.addWidget(self.open_folder_button)
        folder_group.setLayout(folder_layout)

        # ======== Progreso ========
        progress_group = QGroupBox("📊 Progreso")
        progress_layout = QVBoxLayout()
        self.progress_file = QProgressBar()
        self.progress_total = QProgressBar()
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(QLabel("Archivo actual:"))
        progress_layout.addWidget(self.progress_file)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(QLabel("Total:"))
        progress_layout.addWidget(self.progress_total)
        progress_group.setLayout(progress_layout)

        # ======== Logs ========
        log_group = QGroupBox("📝 Actividad")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)

        # ======== Cancelar ========
        self.cancel_button = QPushButton("🛑 Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_conversion)

        # ======== Convertidos ========
        converted_group = QGroupBox("✅ Archivos convertidos")
        converted_layout = QVBoxLayout()
        self.converted_list = QListWidget()
        converted_layout.addWidget(self.converted_list)
        converted_group.setLayout(converted_layout)

        # ======== Layout principal ========
        main_layout.addWidget(files_group)
        main_layout.addWidget(folder_group)
        main_layout.addWidget(progress_group)
        main_layout.addWidget(log_group)
        main_layout.addWidget(self.cancel_button)
        main_layout.addWidget(converted_group)
        self.setLayout(main_layout)

    # ======== Funciones ========
    def log(self, message):
        self.log_text.append(message)

    def cancel_conversion(self):
        if hasattr(self, 'worker'):
            self.worker.cancel()
            self.progress_label.setText("⛔ Cancelado")
            self.cancel_button.setEnabled(False)

    def open_output_folder(self):
        folder = self.output_folder if self.output_folder else os.getcwd()
        if not os.path.exists(folder):
            QMessageBox.warning(self, "Error", "La carpeta no existe")
            return
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar videos", "", "Videos (*.mp4 *.mkv *.avi *.mov)"
        )
        if files:
            self.start_conversion(files)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if folder:
            self.output_folder = folder
            self.folder_label.setText(f"Carpeta actual: {folder}")

    def handle_video_link(self):
        link = self.video_link.text().strip()
        if not link:
            QMessageBox.warning(self, "Aviso", "Pegá un link primero")
            return

        choice = QMessageBox.question(
            self,
            "Descarga completa",
            "¿Querés convertir el video a MP4 (H.264) después de descargarlo?",
            QMessageBox.Yes | QMessageBox.No
        )
        convert = choice == QMessageBox.Yes

        self.start_conversion([], video_link=link, convert_after_download=convert)

    def start_conversion(self, files, video_link=None, convert_after_download=True):
        if not files and not video_link:
            return
        self.cancel_button.setEnabled(True)

        self.worker = ConvertWorker(
            files=files,
            youtube_link=video_link,
            convert_after_download=convert_after_download,
            output_folder=self.output_folder,
            quality_preset=self.quality_box.currentIndex()
        )

        self.worker.status.connect(self.progress_label.setText)
        self.worker.progress_file.connect(self.progress_file.setValue)
        self.worker.progress_global.connect(self.progress_total.setValue)
        self.worker.finished.connect(lambda f, r: self.converted_list.addItem(f"{f} → {r}"))
        self.worker.error.connect(lambda f, m: self.log(f"❌ {f}: {m}"))
        self.worker.finished.connect(lambda *_: self.cancel_button.setEnabled(False))
        self.worker.error.connect(lambda *_: self.cancel_button.setEnabled(False))
        self.worker.start()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.start_conversion(files)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DropWindow()
    window.show()
    sys.exit(app.exec())
