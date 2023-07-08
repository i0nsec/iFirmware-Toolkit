import requests, os, time, threading
from humanize import naturalsize
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal

app_version = 'v3.0-1220'
 
class DownloadManager(QtWidgets.QMainWindow):
    is_downloading = False
    all_signed = False
    finished = False
    urls = {}
    dest_folder = None
    skip_firmware = False
    total_all_to_download = 0
    download_combo = {}
    target_ios_version = ''

    def __init__(self) -> None:
        super(DownloadManager, self).__init__()
        uic.loadUi("UI\\_dm.ui", self)
        self.setFixedSize(660, 500)
        self.show()
        self.setWindowTitle(f'Download - {app_version}')
        pixmapi = QtWidgets.QStyle.SP_ArrowDown
        icon = self.style().standardIcon(pixmapi)
        self.setWindowIcon(icon)
    
        self.disable_skip_btn()
        self.cancel_btn.clicked.connect(self.stop)
        self.start.clicked.connect(lambda: self._start())
        pixmapi = QtWidgets.QStyle.SP_ArrowDown
        icon = self.style().standardIcon(pixmapi)
        self.start.setIcon(icon)

        self.skip.clicked.connect(lambda: self._skip())
        pixmapi = QtWidgets.QStyle.SP_ArrowForward
        icon = self.style().standardIcon(pixmapi)
        self.skip.setIcon(icon)

        pixmapi = QtWidgets.QStyle.SP_MessageBoxCritical
        icon = self.style().standardIcon(pixmapi)
        self.cancel_btn.setIcon(icon)

        self.dest_label.setText(f"Dest: {DownloadManager.dest_folder}")

        DownloadManager.is_downloading = True

    def progress_bar_update(self) -> None:
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(0)

    def _skip(self) -> None:
        DownloadManager.skip_firmware = True

    def _start(self) -> None:
        self.ios_combo.setDisabled(True)
        self.main_thread = threading.Thread(target=self.download_all_signed)
        self.main_thread.daemon = True
        self.main_thread.start()

    def closeEvent(self, event) -> None: 
        self.stop()

    def stop(self) -> None:
        try:
            self.th_download.terminate() # Terminate main download thread 
            self.th_download.file.close() # Close file

            # Delete file after terminating thread
            if os.path.isfile(self.th_download.destination):
                current_file_size = os.path.getsize(self.th_download.destination)

                if current_file_size != int(self.file_size):
                    os.remove(self.th_download.destination)

        except AttributeError as msg:
            # Need to implement this...
            self.close()

        finally:
            DownloadManager.is_downloading = False
            self.close()

    def list_items(self) -> None:
        for index, value in DownloadManager.urls.items():
            if value[3] == DownloadManager.target_ios_version:
                QtWidgets.QTreeWidgetItem(self.pc_tree, [value[0], value[3]])

    def download_all_signed(self) -> None:
        self.current_url = ''
        self.destination = DownloadManager.dest_folder
        self.full_destination = ''
        self.firmwares = len(DownloadManager.urls)
        self.downloaded = 1
        self.file_size = 0
        self.current_seconds = time.time()
        DownloadManager.all_signed = True
        self.disable_start_btn()
        self.skip.setEnabled(True)
        self.skip.setStyleSheet("""
            QPushButton {background-color: #24293B;border: 2px solid #313850;border-radius: 10px;color: #fff;}
            QPushButton:hover {background-color: #1E2230;}
            QToolTip { color: #fff; background-color: #000; border: none;}
                """)

        for index, value in DownloadManager.urls.items():
            if value[3] == DownloadManager.target_ios_version:
                DownloadManager.skip_firmware = False

                # Parse data passed from the main app
                self._name = value[0]
                self.current_url = value[1]
                self.sha1 = value[2]
                self.buildid = value[3]

                # Update headers 
                self.header.setText(f"Downloading {self.downloaded}/{self.firmwares}")
                self.header.setStyleSheet("color: #c2df04")

                # Get file size
                r = requests.get(self.current_url, stream=True)
                self.file_size = r.headers['Content-Length'] # Get firmware size

                self.got_data = 0
                self.full_destination = f"{self.destination}\\{self.current_url.split('/')[-1:][0]}"

                DownloadManager.finished = True
                self.top_header.setText(f"{self._name} - {self.buildid}")
                self.th_download = Downloader(url=self.current_url, destination=self.full_destination)
                self.th_download.send_header.connect(self.update_header)
                self.th_download.disable_cancel_btn.connect(self.disable_cancel_btn)
                self.th_download.start()
                self.wait_for_threads()
                self.downloaded += 1
                self.list_items()

    def set_target_ios_version(self, version) -> None:
        DownloadManager.target_ios_version = version
        self.top_header.setText(f"Total to be downloaded: {str(naturalsize(DownloadManager.download_combo[version]))}")
        self.pc_tree.clear()
        self.list_items()

    def get_download_estimate(self) -> None: 
        if len(DownloadManager.download_combo) == 0:
            self.progress_bar_update()
            self.header.setText("Estimating overall download size, please wait...")
            self.get_est_for_all = GetTotalDownloads()
            self.get_est_for_all.start()
            self.get_est_for_all.finished.connect(self.set_est_in_human_readable)
        else:
            self.set_est_in_human_readable()

    def set_est_in_human_readable(self) -> None:
        self.pbar.setMaximum(100)
        self.start.setEnabled(True)
        self.start.setStyleSheet("""
            QPushButton {background-color: #24293B;border: 2px solid #313850;border-radius: 10px;color: #fff;}
            QPushButton:hover {background-color: #1E2230;}
            QToolTip { color: #fff; background-color: #000; border: none;}
                """)
        self.ios_combo.currentTextChanged.connect(lambda: self.set_target_ios_version(self.ios_combo.currentText()))
        self.ios_combo.addItems(DownloadManager.download_combo)
        self.ios_combo.setStyleSheet("""
            * {
                color: #fff;
            }

            QComboBox {
                border: 2px solid #313850;
                border-radius: 10px;
                background-color: #24293B;
                padding: 1px 18px 1px 3px;
            }

            QComboBox:editable {
                    background-color: #24293B;
            }

            QComboBox:!editable, QComboBox::drop-down:editable {
                background-color: #24293B;
                color: #fff;
                border: 2px solid #313850;
                border-radius: 10px;
            }

            /* QComboBox gets the "on" state when the popup is open */
            QComboBox:!editable:on, QComboBox::drop-down:editable:on {
                background-color: #24293B;
            }

            QComboBox:on { /* shift the text when the popup opens */
                padding-top: 3px;
                padding-left: 4px;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;

                border-left-width: 0px;
                border-left-color: darkgray;
                border-left-style: solid; /* just a single line */
                border-top-right-radius: 3px; /* same radius as the QComboBox */
                border-bottom-right-radius: 3px;
            }
        
        """)
        self.header.clear()
        self.top_header.setText(f"Total to be downloaded: {str(naturalsize(DownloadManager.download_combo[DownloadManager.target_ios_version]))}")

    def wait_for_threads(self) -> None:
        while DownloadManager.finished:
            time.sleep(0.5)
            if not DownloadManager.finished:
                break

            if DownloadManager.skip_firmware:
                time.sleep(0.5)
                self.th_download.terminate() # Terminate main download thread 
                self.th_download.file.close() # Close file

                # Delete file after terminating thread
                if os.path.isfile(self.th_download.destination):
                        os.remove(self.th_download.destination)

                break

    def download_one_firmware(self, url, destination, device, version, firmwares=1, downloaded=1) -> None:

        self.start.setDisabled(True)
        self.start.setStyleSheet("""
            QPushButton {
                background-color: #000;
            }

            QPushButton:disabled {
                border: none;
                border-radius: 10px;
            }""")
        self.skip.setDisabled(True)
        self.url = url
        self.destination = destination
        self.firmwares = firmwares
        self.downloaded = downloaded
        self.file_size = 0
        self.current_seconds = time.time()
        DownloadManager.is_downloading = True

        # Update headers information
        self.header.setText(f"Downloading {self.downloaded}/{self.firmwares}")
        self.header.setStyleSheet("color: #c2df04")
        r = requests.get(self.url, stream=True)
        self.file_size = r.headers['Content-Length']

        QtWidgets.QTreeWidgetItem(self.pc_tree, [device, version])

        self.got_data = 0
        self.progress_bar_update()
        self.top_header.setText(device)
        self.th_download = Downloader(url=self.url, destination=self.destination)
        self.th_download.start()
        self.th_download.send_header.connect(self.update_header)
        self.th_download.disable_cancel_btn.connect(self.disable_cancel_btn)

    def disable_skip_btn(self) -> None:
        self.skip.setStyleSheet("""
            QPushButton {
                background-color: #000;
            }

            QPushButton:disabled {
                border: none;
                border-radius: 10px;
            }""")

        self.skip.setDisabled(True)

    def disable_start_btn(self) -> None:
        if DownloadManager.download_combo:
            return 
        self.start.setStyleSheet("""
            QPushButton {
                background-color: #000;
            }

            QPushButton:disabled {
                border: none;
                border-radius: 10px;
            }""")
        self.start.setDisabled(True)

    def disable_cancel_btn(self, val) -> None:
        self.cancel_btn.setDisabled(val)
        self.cancel_btn.setStyleSheet("background-color: #000")
        self.stop()

    def update_header(self, val) -> None:
        self.got_data += val
        self.header.setText(f"Downloading {self.downloaded}/{self.firmwares} {naturalsize(int(self.got_data))}/{naturalsize(int(self.file_size))}\nElapsed: {self.get_est(time.time() - self.current_seconds)}")

    def get_est(self, seconds) -> str:
        return time.strftime("%H:%M:%S", time.gmtime(seconds))

class Downloader(QThread):
    send_header = pyqtSignal(int)
    disable_cancel_btn = pyqtSignal(bool)

    def __init__(self, parent=None, url='', destination=''):
        QThread.__init__(self)
        self.url = url
        self.destination = destination

    def run(self):
        r = requests.get(self.url, stream=True)
        self.file = open(self.destination, 'wb')

        try:
            for data in r.iter_content(chunk_size=8192):
                self.file.write(data)
                self.send_header.emit(len(data))

        finally:
            self.file.close()
            if not DownloadManager.all_signed:
                self.disable_cancel_btn.emit(True)

            DownloadManager.finished = False

class GetTotalDownloads(QThread):

    def __init__(self, parent=None):
        QThread.__init__(self)
        self.total = 0
        self.current_ios_versions = set()

    def run(self):
        for url in DownloadManager.urls.items():
            self.current_ios_versions.add(url[1][3])

        DownloadManager.download_combo = DownloadManager.download_combo.fromkeys(self.current_ios_versions, 0)

        with requests.Session() as session:
            for url in DownloadManager.urls.items():
                for ios_version in DownloadManager.download_combo.keys():
                    if ios_version == url[1][3]:
                        r = session.get(url[1][1], stream=True)
                        DownloadManager.download_combo[ios_version] += int(r.headers['Content-Length'])