import os
import sys
import time
from collections import defaultdict
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, QTimer, pyqtSignal

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.inputLayout = QtWidgets.QHBoxLayout()
        self.inputLayout.setObjectName("inputLayout")
        self.directoryLabel = QtWidgets.QLabel(self.centralwidget)
        self.directoryLabel.setObjectName("directoryLabel")
        self.inputLayout.addWidget(self.directoryLabel)
        self.directoryLineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.directoryLineEdit.setObjectName("directoryLineEdit")
        self.inputLayout.addWidget(self.directoryLineEdit)
        self.browseButton = QtWidgets.QPushButton(self.centralwidget)
        self.browseButton.setObjectName("browseButton")
        self.inputLayout.addWidget(self.browseButton)
        self.scanButton = QtWidgets.QPushButton(self.centralwidget)
        self.scanButton.setEnabled(False)
        self.scanButton.setObjectName("scanButton")
        self.inputLayout.addWidget(self.scanButton)
        self.stopButton = QtWidgets.QPushButton(self.centralwidget)
        self.stopButton.setEnabled(False)
        self.stopButton.setObjectName("stopButton")
        self.inputLayout.addWidget(self.stopButton)
        self.verticalLayout.addLayout(self.inputLayout)
        self.treeWidget = QtWidgets.QTreeWidget(self.centralwidget)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "Имя файла")
        self.treeWidget.headerItem().setText(1, "Размер")
        self.treeWidget.headerItem().setText(2, "Папка")
        self.treeWidget.headerItem().setText(3, "Путь")
        self.verticalLayout.addWidget(self.treeWidget)
        self.statusLayout = QtWidgets.QVBoxLayout()
        self.statusLayout.setObjectName("statusLayout")
        self.statusbar1 = QtWidgets.QLabel(self.centralwidget)
        self.statusbar1.setObjectName("statusbar1")
        self.statusLayout.addWidget(self.statusbar1)
        self.statusbar2 = QtWidgets.QLabel(self.centralwidget)
        self.statusbar2.setObjectName("statusbar2")
        self.statusLayout.addWidget(self.statusbar2)
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setVisible(False)
        self.statusLayout.addWidget(self.progressBar)
        self.verticalLayout.addLayout(self.statusLayout)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Сканер дубликатов файлов"))
        self.directoryLabel.setText(_translate("MainWindow", "Директория:"))
        self.browseButton.setText(_translate("MainWindow", "Обзор"))
        self.scanButton.setText(_translate("MainWindow", "Сканировать"))
        self.stopButton.setText(_translate("MainWindow", "Стоп"))

class ScanThread(QThread):
    update_progress = QtCore.pyqtSignal(int)
    scan_complete = QtCore.pyqtSignal(defaultdict)

    def __init__(self, directory, parent=None):
        self.directory = directory
        super(ScanThread, self).__init__(parent)

    def run(self):
        file_sizes = defaultdict(list)
        total_files = sum([len(files) for r, d, files in os.walk(self.directory)])
        current_file = 0
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_sizes[file_size].append((file_path, os.path.basename(root), file))
                current_file += 1
                progress = (current_file / total_files) * 100
                self.update_progress.emit(progress)
                if self.isInterruptionRequested():
                    return

        self.scan_complete.emit(file_sizes)

class ProgressThread(QThread):
    update_progress = pyqtSignal(int)

    def run(self):
        for i in range(100):
            time.sleep(0.1)
            self.update_progress.emit(i)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.progress_value = 0
        self.scan_thread = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_ui)
        self.timer.start(100)

        self.browseButton.clicked.connect(self.browse)
        self.scanButton.clicked.connect(self.scan)
        self.stopButton.clicked.connect(self.stop_scan)
        self.directoryLineEdit.textChanged.connect(self.enable_scan_button)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите директорию")
        if directory:
            self.directoryLineEdit.setText(directory)
            self.scanButton.setEnabled(True)

    def enable_scan_button(self):
        directory = self.directoryLineEdit.text()
        self.scanButton.setEnabled(bool(directory))

    def update_progress_ui(self):
        self.progressBar.setValue(self.progress_value)

    def store_progress_value(self, value):
        self.progress_value = value

    def on_update_progress(self, value):
        self.progressBar.setValue(value)

    def on_scan_complete(self, file_sizes):
        self.progressBar.setValue(100)
        self.progressBar.setVisible(False)
        self.stopButton.setEnabled(False)
        self.scanButton.setEnabled(True)

        for size, files in file_sizes.items():
            if len(files) > 1:
                size_item = QTreeWidgetItem(self.treeWidget, ["", f"{size} кбайт", "", ""])
                for file_path, folder, file_name in files:
                    file_item = QTreeWidgetItem(size_item, [file_name, f"{size} кбайт", folder, file_path])
                    size_item.addChild(file_item)

        self.statusbar1.setText("Сканирование завершено")
        self.statusbar2.setText(f"Найдено дубликатов: {len(file_sizes)}")

    def stop_scan(self):
        if self.scan_thread:
            self.scan_thread.requestInterruption()
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.scan_thread = None
            self.progressBar.setValue(0)
            self.progressBar.setVisible(False)
            self.stopButton.setEnabled(False)
            self.scanButton.setEnabled(True)
            self.statusbar1.setText("Сканирование прервано")
            self.statusbar2.setText("")

    def scan(self):
        directory = self.directoryLineEdit.text()
        if directory:
            self.treeWidget.clear()
            self.statusbar1.clear()
            self.statusbar2.clear()
            self.progressBar.setMaximum(100)
            self.progressBar.setValue(0)
            self.progressBar.setVisible(True)
            self.scan_thread = ScanThread(directory)
            self.scan_thread.update_progress.connect(self.store_progress_value)
            self.scan_thread.scan_complete.connect(self.on_scan_complete)

            self.progress_thread = ProgressThread()
            self.progress_thread.update_progress.connect(self.on_update_progress)

            self.scan_thread.start()
            self.progress_thread.start()

            self.scanButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            self.statusbar1.setText("Сканирование...")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
