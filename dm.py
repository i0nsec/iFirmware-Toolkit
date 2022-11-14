import requests, os, time, threading
from humanize import naturalsize
from PyQt5 import QtGui, QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal

__version__ = 'v1.0-1114'

class MainDownload(QtWidgets.QMainWindow):
    is_downloading = False
    all_signed = False
    finished = False
    urls = {}
    dest_folder = None
    skip_firmware = False

    def __init__(self): 
        super(MainDownload, self).__init__()
        uic.loadUi("_dm.ui", self)
        self.setFixedSize(560, 500)
        self.show()
        self.setWindowTitle(f'Download - v1.0-1322')
        pixmapi = QtWidgets.QStyle.SP_ArrowDown
        icon = self.style().standardIcon(pixmapi)
        self.setWindowIcon(icon)
        MainDownload.is_downloading = True
        
        self.disable_skip_btn()
        self.cancel_btn.clicked.connect(self.stop)
        self.start.clicked.connect(lambda: self._start())
        self.header.setText("Hit Start to begin downloading")
        self.skip.clicked.connect(lambda: self._skip())

    def progress_bar_update(self):
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(0)

    def _skip(self):
        MainDownload.skip_firmware = True

    def _start(self):
        self.main_thread = threading.Thread(target=self.DownloadAllSigned)
        self.main_thread.daemon = True
        self.main_thread.start()

    def closeEvent(self, event): 
        self.stop()

    def stop(self):
        try:
            self.th_download.terminate() # Terminate main download thread 
            self.th_download.file.close() # Close file

            # Delete file after terminating thread
            if os.path.isfile(self.th_download.destination):
                current_file_size = os.path.getsize(self.th_download.destination)

                if current_file_size != int(self.file_size):
                    os.remove(self.th_download.destination)

        except AttributeError as msg:
            self.close()

        finally:
            MainDownload.is_downloading = False
            self.close()

    def list_items(self):
        for index, value in MainDownload.urls.items():
            QtWidgets.QTreeWidgetItem(self.pc_tree, [str(index), value[0], value[3]])

    def DownloadAllSigned(self):
        self.current_url = ''
        self.destination = MainDownload.dest_folder
        self.full_destination = ''
        self.firmwares = len(MainDownload.urls)
        self.downloaded = 1
        self.file_size = 0
        self.current_seconds = time.time()
        MainDownload.all_signed = True
        self.disable_start_btn()
        self.skip.setEnabled(True)
        self.skip.setStyleSheet("""
            QPushButton {
                background-color: #c3a315;
                border: none;
                border-radius: 10px;
                color: #fff;
            }

            QPushButton:disabled {
                border: none;
                border: 2px solid #0C632A;
                border-radius: 10px;
            }

            QPushButton:hover {
                background-color: #b39614;
            }
            
            QToolTip {
                color: #fff;
                background-color: #000;
                border: none;
            }""")

        for index, value in MainDownload.urls.items():
            MainDownload.skip_firmware = False

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

            MainDownload.finished = True
            self.top_header.setText(f"{self._name} - {self.buildid}")
            self.th_download = Downloader(url=self.current_url, destination=self.full_destination)
            self.th_download.send_header.connect(self.update_header)
            self.th_download.disable_cancel_btn.connect(self.disable_cancel_btn)
            self.th_download.start()
            self.wait_for_threads()
            self.downloaded += 1
            self.list_items()

    def wait_for_threads(self):
        while MainDownload.finished:
            time.sleep(0.5)
            if not MainDownload.finished:
                break

            if MainDownload.skip_firmware:
                time.sleep(0.5)
                self.th_download.terminate() # Terminate main download thread 
                self.th_download.file.close() # Close file

                # Delete file after terminating thread
                if os.path.isfile(self.th_download.destination):
                        os.remove(self.th_download.destination)

                break

    def Download(self, url, destination, device, firmwares=1, downloaded=1, version=None):
        self.setFixedSize(560, 300)
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
        MainDownload.is_downloading = True

        # Update headers information
        self.header.setText(f"Downloading {self.downloaded}/{self.firmwares}")
        self.header.setStyleSheet("color: #c2df04")
        r = requests.get(self.url, stream=True)
        self.file_size = r.headers['Content-Length']

        QtWidgets.QTreeWidgetItem(self.pc_tree, ["1", device, str(naturalsize(int(self.file_size)))])

        self.got_data = 0
        self.progress_bar_update()
        self.top_header.setText(device)
        self.th_download = Downloader(url=self.url, destination=self.destination)
        self.th_download.start()
        self.th_download.send_header.connect(self.update_header)
        self.th_download.disable_cancel_btn.connect(self.disable_cancel_btn)

    def disable_skip_btn(self):
        self.skip.setStyleSheet("""
            QPushButton {
                background-color: #000;
            }

            QPushButton:disabled {
                border: none;
                border-radius: 10px;
            }""")

        self.skip.setDisabled(True)

    def disable_start_btn(self):
        self.start.setStyleSheet("""
            QPushButton {
                background-color: #000;
            }

            QPushButton:disabled {
                border: none;
                border-radius: 10px;
            }""")
        self.start.setDisabled(True)

    def disable_cancel_btn(self, val):
        self.cancel_btn.setDisabled(val)
        self.cancel_btn.setStyleSheet("background-color: #000")
        self.stop()

    def update_header(self, val):
        self.got_data += val
        self.header.setText(f"Downloading {self.downloaded}/{self.firmwares} {naturalsize(int(self.got_data))}/{naturalsize(int(self.file_size))}\nElapsed: {self.get_est(time.time() - self.current_seconds)}")

    def get_est(self, seconds):
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
            if not MainDownload.all_signed:
                self.disable_cancel_btn.emit(True)

            MainDownload.finished = False