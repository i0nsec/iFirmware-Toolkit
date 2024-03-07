import requests
import os
import sys
import hashlib
import webbrowser
import time
import py7zr
import sqlite3
import json
import pyqtcss
import logging
import validators
from humanize import naturalsize
from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSignal, Qt, QThread
from PyQt5.QtWidgets import (QMainWindow,
                            QApplication,
                            QTextBrowser,
                            QFileDialog,
                            QMessageBox,
                            QTreeWidgetItem,
                            QMenu,
                            QStyle,
                            QToolButton,
                            QTableWidgetItem,
                            QDialog)
from ssl import SSLZeroReturnError, SSLEOFError
from pymobiledevice3 import usbmux
from pymobiledevice3 import lockdown as lockdown_
from pymobiledevice3.services import (diagnostics, 
                                      mobile_activation,
                                      mobilebackup2)
from pymobiledevice3 import exceptions
import dm # dm.py - main downloader

_s = "#91c881" # Green - for success
_w = "#ffffff" # White - for normal message output
_d = "#DEDE00" # Red - for errors
_y = "#9EBB00" # Yellow - for warnings

pyqtcss.get_style("dark_blue")
app_version = 'v3.3-1229' # App version
download_urls = {} # Used to pass URLs to the downloader module  
no_update = False # Do not update QTreeWidget when checking for database update, if there is no updates available
dbs = [
    'DBs\\ios_devices.db',
    'DBs\\ipad_devices.db',
    'DBs\\ipod_devices.db',
    'DBs\\macbook_devices.db',
    'DBs\\iTunes.db',
    'DBs\\other.db'
]

def delete_from_database(URL, current_index, name):
    window.log(f"Deleting {name} from database...")
    value = messaged_box(
        "Delete",
        "UI/icons/updated.png",
        "UI/icons/Question.png",
       f"Are you sure you want to delete {name} from database?", 
       ok=False,
       yes=True,
       no=True)

    if value == 0:
        delete_from = dbs[current_index]

        try:
            if os.path.isfile(delete_from):
                conn = sqlite3.connect(delete_from)
                cur = conn.cursor()

                if current_index == 4:
                    cur.execute(f"""DELETE FROM devices WHERE URL32='{URL}'""")
                else:
                    cur.execute(f"""DELETE FROM devices WHERE URL='{URL}'""")

                conn.commit()
                conn.close()
                window.log(f"Deleted {name} from {delete_from} database")
        finally:
            window.reset_data()

        return 0

    elif value == 1:
        window.log("Aborted by user.")

def messaged_box(title, 
                 window_icon, 
                 icon, 
                 text, 
                 ok=True, 
                 copy=False, 
                 yes=False, 
                 no=False, 
                 abort=False, 
                 get=False):
    message = QMessageBox()
    message.setIconPixmap(QtGui.QPixmap(icon))
    message.setWindowIcon(QtGui.QIcon(window_icon))
    message.setWindowTitle(title)
    message.setText(text)
    message.setStyleSheet("""
            background-color:rgb(18, 18, 18); 
            color: #fff; 
            padding: 15px;""")

    font = QtGui.QFont()
    font.setPointSize(10)
    font.setBold(True)
    font.setFamily("Segoe UI Semibold")
    message.setFont(font)
    styles = """
        QPushButton {
            background-color: #3700B3;
            border: none;
            color: #fff;
            padding-left: 15px;
            padding-right: 15px;
        }

        QPushButton:hover {
            background-color: #270080;
        }"""

    if ok:
        ok = message.addButton('Ok', message.ActionRole)
        ok.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        ok.setFont(font)
        ok.setIcon(ok.style().standardIcon(QStyle.SP_DialogApplyButton))
        ok.setStyleSheet(styles)

    if get:
        get = message.addButton('Get', message.ActionRole)
        get.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        get.setFont(font)
        get.setIcon(get.style().standardIcon(QStyle.SP_ArrowDown))
        get.setStyleSheet(styles)

    if copy:
        copy = message.addButton('Copy', message.ActionRole)
        copy.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        copy.setFont(font)
        copy.setIcon(copy.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        copy.setStyleSheet(styles)

    if yes:
        yes = message.addButton('Yes', message.ActionRole)
        yes.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        yes.setFont(font)
        yes.setIcon(yes.style().standardIcon(QStyle.SP_DialogApplyButton))
        yes.setStyleSheet(styles)

    if no:
        no = message.addButton('No', message.ActionRole)
        no.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        no.setFont(font)
        no.setIcon(no.style().standardIcon(QStyle.SP_DialogCancelButton))
        no.setStyleSheet(styles)

    if abort:
        abort = message.addButton('Abort', message.ActionRole)
        abort.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        abort.setFont(font)
        abort.setIcon(abort.style().standardIcon(QStyle.SP_MessageBoxCritical))
        abort.setStyleSheet(styles)

    return message.exec_()

class Options(QDialog):
    NEW_DEST: str = ''
    ALWAYS_HASH: bool = False
    ALWAYS_UNSIGNED: bool = False
    AUTO_CHECK_UPDATE: bool = False
    hide_columns = True

    def __init__(self):
        super(Options, self).__init__()
        uic.loadUi("UI\\_config.ui", self)
        self.filename = "DBs/settings.json"

        if os.path.exists(self.filename):
            with open(self.filename, 'r') as setting:
                settings = json.load(setting)
                Options.NEW_DEST = settings['dest']
                self.change_dir_line.setText(Options.NEW_DEST)

                Options.ALWAYS_HASH = settings['always_hash']
                if Options.ALWAYS_HASH:
                    self.always_hash.setChecked(True)
                elif not Options.ALWAYS_HASH:
                    self.always_hash.setChecked(False)

                Options.ALWAYS_UNSIGNED = settings['always_unsigned']
                if Options.ALWAYS_UNSIGNED:
                    self.always_unsigned.setChecked(True)
                elif not Options.ALWAYS_UNSIGNED:
                    self.always_unsigned.setChecked(False)

                Options.AUTO_CHECK_UPDATE = settings['auto_update']
                if Options.AUTO_CHECK_UPDATE:
                    self.auto_check_update.setChecked(True)
                elif not Options.AUTO_CHECK_UPDATE:
                    self.auto_check_update.setChecked(False)

                Options.hide_columns = settings['hide_columns']
                if Options.hide_columns:
                    self.hide_column.setChecked(True)
                elif not Options.hide_columns:
                    self.hide_column.setChecked(False)

        # Reset line edit
        self.edit_line.clear()

        # Choose a file button
        self.edit_btn.clicked.connect(lambda: self.open_dialog())

        # Change directory
        self.change_dir.clicked.connect(lambda: self.change_dirs())

        self.always_hash.clicked.connect(lambda: self.set_always_hash(self.always_hash.checkState()))
        self.always_unsigned.clicked.connect(lambda: self.set_always_unsigned(self.always_unsigned.checkState()))
        self.auto_check_update.clicked.connect(lambda: self.set_always_auto_check(self.auto_check_update.checkState()))
        self.hide_column.clicked.connect(lambda: self.set_hide_column(self.hide_column.checkState()))

        self.save_config.clicked.connect(lambda: self.save_changes())
        self.reset.clicked.connect(lambda: self.reset_default_directory())

        # Reset background color for the load button
        self.ok.setDisabled(True)
        self.ok.setStyleSheet("QPushButton {background-color: #777;border: none;color: #000;}QPushButton:disabled {border: none;}QPushButton:hover {background-color: #084D20;}QToolTip { color: #fff; background-color: #000; border: none; }") 

    def closeEvent(self, event):
        self.stop()

    def stop(self):
        MainApp.options.setEnabled(True)

    def reset_default_directory(self):
        Options.NEW_DEST = f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates"
        self.change_dir_line.setText(Options.NEW_DEST)
        self.save_changes()

    def save_changes(self):
        with open(self.filename, "w") as config:
            json.dump({
                'dest': Options.NEW_DEST,
                'always_hash': Options.ALWAYS_HASH,
                'always_unsigned': Options.ALWAYS_UNSIGNED,
                'auto_update': Options.AUTO_CHECK_UPDATE,
                'hide_columns': Options.hide_columns
                }, config)

        window.log("Successfully saved settings.", _s)
        messaged_box("Settings", 
                        "UI/icons/settings.png", 
                        "UI/icons/Checkmark_1.png", 
                        f"Successfully saved settings. Please restart iFTK.")

    def set_always_hash(self, state):
        if state == 2:
            Options.ALWAYS_HASH = True
        else:
            Options.ALWAYS_HASH = False

    def set_always_unsigned(self, state):
        if state == 2:
            Options.ALWAYS_UNSIGNED = True
        else:
            Options.ALWAYS_UNSIGNED = False

    def set_always_auto_check(self, state):
        if state == 2:
            Options.AUTO_CHECK_UPDATE = True
        else:
            Options.AUTO_CHECK_UPDATE = False

    def set_hide_column(self, state):
        if state == 2:
            Options.hide_columns = True
        else:
            Options.hide_columns = False

    def change_dirs(self):
        new_dest = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        Options.NEW_DEST = new_dest
        window.log(f"Setting new default path: {Options.NEW_DEST}", _s)
        self.change_dir_line.setText(Options.NEW_DEST)

    def open_dialog(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","7z Files (*.7z)", options=options)
        if filename:
            self.edit_line.setText(filename)

            try:
                created = filename.split("/")[-1].split("-")[1]
            except IndexError:
                created = None

            try:
                if float(created):
                    self.header.setText(f"Restore a database backup\nValidated: {time.ctime(float(created))}")

                    # Enable the load button
                    self.ok.setEnabled(True)
                    self.ok.setStyleSheet("""
                            QPushButton {
                                background-color: #3700B3;
                                border: none;
                                color: #fff;
                                padding: 10px;
                            }

                            QPushButton:hover {
                                background-color: #270080;
                            }""") 
                    self.ok.clicked.connect(lambda: self.clean_and_refrush_ui(filename))
                    
            except TypeError:
                self.validate.setStyleSheet("color: #bf0000")
                self.validate.setText("ERROR: No file uploaded or invalid file type. Ex: DBs-[creation time in seconds]-.7z")
        
    def clean_and_refrush_ui(self, filename):
        window.log(f"Importing database from backup, {filename}...")
        try:
            if filename and filename[-2:] == '7z':
                
                # Delete old databases before restoring from a backup
                to_delete = [db for db in dbs if os.path.isfile(db)]
                if to_delete:
                    for db in to_delete:
                        try:
                            os.remove(db)
                        except PermissionError:
                            window.log(f"Unable to remove database {db}")
                            break

                window.reset_data()

                extract = py7zr.SevenZipFile(filename)
                extract.extractall('.')
                extract.close()
                window.log("Finished importing databases from backup.", _s)

        finally:
            window.load_data()
            window.reset_data()
            self.close()

class MainApp(QMainWindow):
    hide_columns = True
    server_address = ""
    database_version = 'Not available' # Database version
    relevant_version = 16
    ios_combo = [] # Choose a signed version of iOS to download
    signed_only = True # Show signed only
    hash_firmware = False # Whether to hash after a download is finished 
    show_relevant = True # Always show relevant only
    current_index = 0
    options = None
    this_pc = []
    current_device = {}
    notified = True
    connected = False
    safari_session = True
    safari_tabs = []
    udid = ""
    ls = list
    text_reset = None
    dest = f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates"
    ACTUAL_DEST = f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates"
    force_continue = False # Force updating even when SHA256 mismatched 
    
    def __init__(self):
        super(MainApp, self).__init__()
        uic.loadUi("UI\\_iFTK.ui", self)
        self.show()
        self.init_logger()
        self.log(f"iFTK version: {app_version}", _s)
        
        # Check if hosts file exists
        if not os.path.exists('.hosts'):
            self.log("Hosts file does not exist.", _d)

        elif os.path.exists('.hosts'):
            with open('.hosts', 'r') as file:
                data = json.loads(file.read().rstrip())
                MainApp.server_address = data['host_address']

        # Create database directory if it doesn't exist
        if not os.path.isdir('DBs'):
            os.mkdir('DBs')

        if os.path.isfile('DBs\\config.cfg'):
            with open('DBs\\config.cfg', 'r') as cfg:
                cfg = cfg.read()
                cfg = cfg.replace("'", '"')
                data = json.loads(cfg)
                MainApp.database_version = data['date']
                MainApp.relevant_version = int(data['relevant'])

        # Set database version
        self.toolBox.setItemText(1, f"Database - Version: {MainApp.database_version}")

        # Open default destination button
        self.open_location.clicked.connect(lambda: self.open_folder())

        # Delete all IPSWs in the current destination folder
        self.ipsw_delete.clicked.connect(self.delete_firmwares)

        # Hash IPSWs in the current destination folder
        self.verify.clicked.connect(self.verify_firmware)

        # Check for database update button
        self._update.clicked.connect(self.database_update)

        # Delete all databases
        self.db_delete.clicked.connect(self.delete_datebases)

        # Backup databases
        self.backup.clicked.connect(self.backup_databases)

        # Search for a device in a database
        self.device_search.textChanged.connect(lambda: self.device_lookup(self.device_search.text(), MainApp.current_index))
        self.device_search.findChild(QToolButton).triggered.connect(lambda: self.device_search_close())
        
        # CheckBoxes:
        # Hash IPSW after the download has finished
        self.check_integrity.clicked.connect(lambda: self.check_integrity_box(self.check_integrity.checkState()))
        # Show signed IPSWs only
        self.show_signed.clicked.connect(lambda: self.show_singed_only(self.show_signed.checkState()))
        # Show most relevant IPSWs versions only
        self.show_relevant.clicked.connect(lambda: self.show_relevant_box(self.show_relevant.checkState()))
        self.show_relevant.setChecked(True)
        self.show_signed.setChecked(True)

        if os.path.exists("DBs/settings.json"):
            with open("DBs/settings.json", "r") as setting:
                try:
                    settings = json.load(setting)
                    NEW_DEST = settings['dest']
                    ALWAYS_UNSIGNED = settings['always_unsigned']
                    ALWAYS_HASH = settings['always_hash']
                    HIDE_COLUMNS = settings['hide_columns']
                    AUTO_CHECK_UPDATE = settings['auto_update']

                    if NEW_DEST:
                        MainApp.dest = NEW_DEST

                    if ALWAYS_HASH:
                        self.check_integrity.setChecked(True)
                    elif not ALWAYS_HASH:
                        self.check_integrity.setChecked(False)

                    if HIDE_COLUMNS:
                        MainApp.hide_columns = True
                    elif not ALWAYS_HASH:
                        MainApp.hide_columns = False

                    if ALWAYS_UNSIGNED:
                        self.show_signed.setChecked(False)
                        MainApp.signed_only = False
                    elif not ALWAYS_UNSIGNED:
                        self.show_signed.setChecked(True)
                        MainApp.signed_only = True

                    if AUTO_CHECK_UPDATE:
                        self.db_thread = DatabaseUpdate()
                        self.db_thread.start()
                        self.db_thread.send_to_log.connect(self.send_to_log)

                        self.up_thread = AppUpdate()
                        self.up_thread.start()
                        self.up_thread.send_to_log.connect(self.send_to_log)

                except KeyError:
                    setting.close()
                    if os.path.exists("DBs//settings.json"):
                        os.remove("DBs//settings.json")
                        
                    self.log("Unable to load settings.json.", _d)
                    self.log("Deleting settings.json...", _y)
                    self.log("Your settings have been reset.", _s)
        self.load_data()

        # Show options menu
        self.op = Options()
        self.options.clicked.connect(lambda: self.show_config())
        MainApp.options = self.options
        self.main_tab.setCurrentIndex(1)
        self.main_tab.setCurrentIndex(0)

        # Check for iFTK update button
        self.get_update.clicked.connect(self.update_btn_clicked)

        # Main download button
        # Download all signed IPSWs - for iOS only
        self.main_download.clicked.connect(lambda: self.download_all_signed(MainApp.current_index))

        # Link to GitHub's repo
        self.git_link.clicked.connect(lambda: webbrowser.open("https://github.com/i0nsec/iFirmware-Toolkit"))

        self.pbar.setStyleSheet("""
            QProgressBar {
                min-height: 12px;
                max-height: 12px;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: #24293B;
            }
        """)
        self.check_if_device_connected()
        self.enter_recovery.clicked.connect(lambda: self.enter_recovery_())
        self.poweroff.clicked.connect(lambda: self.shutdown())
        self.reboot.clicked.connect(lambda: self.restart())
        self.erase_btn.clicked.connect(lambda: self.erase())
        self.export_device.clicked.connect(lambda: self.export_device_info())
        self.activate_device.clicked.connect(lambda: self.activate_this_device())

    @classmethod
    def check_integrity_box(cls, state):
        if state == 2:
            cls.hash_firmware = True
        else:
            cls.hash_firmware = False

    @classmethod
    def show_relevant_box(cls, state):
        if state == 2:
            cls.show_relevant = True
            window.reset_data()
        else:
            cls.show_relevant = False
            window.reset_data()

    def check_databases(self):
        for db in dbs:
            if not os.path.exists(db):
                self.show_signed.setDisabled(True)
                self.show_relevant.setDisabled(True)
            else:
                self.show_signed.setDisabled(False)
                self.show_relevant.setDisabled(False)

    def show_singed_only(self, state):
        if state == 2:
            MainApp.signed_only = True
            self.reset_data()
            self.show_relevant.setEnabled(True)
        else:
            MainApp.signed_only = False
            self.reset_data()
            self.show_relevant.setDisabled(True)

    def progress_bar_update(self):
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(0)

    def open_folder(self):
        try:
            self.log(f"Opening folder: {MainApp.ACTUAL_DEST}")
            os.startfile(MainApp.dest)
        except FileNotFoundError:
            self.log("Directory does not exist.\niTunes is not installed, or it has not been initialized or used.", _d)

    def show_config(self):
        # Show options menu

        self.options.setDisabled(True)
        self.op.exec_()

    def download_all_signed(self, current_tab):

        if current_tab != 0:
            self.log("Only iOS is supported for this feature.", _y)
            return

        self.abort = False

        to_download = dbs[current_tab]
        if os.path.isfile(to_download):

            conn = sqlite3.connect(to_download)
            cur = conn.cursor()
            data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, SHA1SUM, URL, SIGNED, IOS_VERSION, BUILDID FROM devices")
            download_urls.clear()
            index = 0
            for info in data.fetchall():
                if self.abort:
                    break

                if info[4] == 1:
                    if int(info[5].split('.')[0]) == MainApp.relevant_version:
                        name = info[0]
                        #identifier = info[1] # Unused
                        sha1 = info[2]
                        url = info[3] 
                        # buildid = info[6] # Unused
                        version = info[5]
                        file_name = url.split('/')[-1:][0] # Get file name from URL
                        dest_folder = f"{MainApp.dest}/{file_name}" # Full path with file name
                        download_urls[index] = [name, url, sha1, version]
                        index += 1
            
            self.enable_btns(True)
            dm.DownloadManager.urls = download_urls
            dm.DownloadManager.dest_folder = MainApp.dest
            self.go_dm = dm.DownloadManager()
            self.go_dm.get_download_estimate()
            self.go_dm.disable_start_btn()

            self.disable_btns = DownloadManagerSignal(dest_folder=dest_folder, hash_value=sha1)
            self.disable_btns.start()
            self.disable_btns.enable_btns.connect(self.enable_btns)
            self.disable_btns.send_to_log.connect(self.send_to_log)
            self.disable_btns.hash_file.connect(self.hash_file)

        else:
            self.log('Could not find any databases.\nCheck for update first.', _d)

    def download_one_firmware(self, dev_name, url, hash_value, buildid, version):
        if not os.path.exists(MainApp.dest):
            os.makedirs(MainApp.dest)

        self.log(f"Downloading: {dev_name} - {buildid}\n{hash_value}\n")

        value = messaged_box("Download Firmware", 
                            "UI/UI/icons/updated.png",
                            "UI/UI/icons/Question.png",
                            f"Start downloading firmware for {dev_name}?",
                            ok=False,
                            yes=True,
                            no=True,
                            abort=False)

        if value == 0:
            dm.DownloadManager.dest_folder = MainApp.dest
            file_name = url.split('/')[-1:][0] # Get file name from URL
            dest_folder = f"{MainApp.dest}/{file_name}" # Full path with file name

            if os.path.isfile(dest_folder):
                
                self.log('Firmware already exists!')
                value = messaged_box("Error", 
                                    "UI/icons/updated.png",
                                    "UI/icons/Question.png",
                                    "Firmware already exists, do you want to delete it and continue?",
                                    ok=False,
                                    yes=True,
                                    no=True)

                if value == 0:
                    os.remove(dest_folder)
                    self.log(f"Removed {dest_folder}")
                    self.enable_btns(True)
                    self.window = QMainWindow()
                    self.dm = dm.DownloadManager()
                    self.dm.download_one_firmware(url, dest_folder, dev_name, version)

                    self.disable_btns = DownloadManagerSignal(dest_folder=dest_folder, hash_value=hash_value)
                    self.disable_btns.start()
                    self.disable_btns.enable_btns.connect(self.enable_btns)
                    self.disable_btns.send_to_log.connect(self.send_to_log)
                    self.disable_btns.hash_file.connect(self.hash_file)

                else:
                    self.log("Aborted by user.")
            else:
                self.enable_btns(True)
                self.dm = dm.DownloadManager()
                self.dm.download_one_firmware(url, dest_folder, dev_name, version)

                self.disable_btns = DownloadManagerSignal(dest_folder=dest_folder, hash_value=hash_value)
                self.disable_btns.start()
                self.disable_btns.enable_btns.connect(self.enable_btns)
                self.disable_btns.send_to_log.connect(self.send_to_log)
                self.disable_btns.hash_file.connect(self.hash_file)

        elif value == 1:
            self.log(f"Skipping {dev_name}")

    def database_update(self):
        # Connect to server and check for database update

        # Exit if hosts file does not exist
        if not MainApp.server_address:
            self.log("No hosts file found.", _d)
            return

        value = messaged_box(
                            "Update", 
                            "UI/icons/updated.png", 
                            "UI/icons/database.png", 
                            "Check for database update?",
                            ok=False,
                            yes=True, 
                            no=True)

        if value == 0:
            self.db_thread = DatabaseUpdate()
            self.db_thread.start()
            self.db_thread.no_update.connect(self.no_update)
            self.db_thread.send_to_log.connect(self.send_to_log)
            self.db_thread.progress_update.connect(self.progress_bar_update)
            self.db_thread.refrush_ui.connect(self.reset_data)
            self.db_thread.is_ready.connect(lambda: self.pbar.setMaximum(100))
            self.db_thread.set_version.connect(lambda: self.toolBox.setItemText(1, f"Database - Version: {MainApp.database_version}"))

        else:
            self.log('Aborted by user.', _d)

    def device_lookup(self, query, current_tab):
        if len(query) == 0:
            self.device_search_close()

        self.worker_search = DeviceSearch(query=query, current_tab=current_tab)
        self.worker_search.start()
        self.worker_search.send_to_log.connect(self.send_to_log)
        self.worker_search.change_device_view.connect(self.change_view)
        self.reset_logger()

    def device_search_close(self):
        self.ios_tree.clear()
        self.load_data(device=None)

    def change_view(self, val):
        self.worker_search = DeviceSearchTableView(query=val)
        self.worker_search.start()
        self.worker_search.send_to_view.connect(self.send_view_change_request)

    def send_view_change_request(self, val):
        self.ios_tree.clear()
        self.load_data(device=val)

    def verify_firmware(self):
        self.verify.setDisabled(True)
        self._verify = VerifyFirmware(current_tab=MainApp.current_index)
        self._verify.start()
        self._verify.send_to_log.connect(self.send_to_log)
        self._verify.progress_update.connect(self.progress_bar_update)
        self._verify.is_ready.connect(lambda: self.pbar.setMaximum(100))
        self._verify.enable_btn.connect(lambda: self.verify.setEnabled(True))

    def update_btn_clicked(self):
        # If hosts file does not exist, do not continue
        if not MainApp.server_address:
            self.log("Hosts file not exist.", _d)
            return 

        self.up_thread = AppUpdate()
        self.up_thread.start()
        self.up_thread.progress_update.connect(self.progress_bar_update)
        self.up_thread.send_to_log.connect(self.send_to_log)
        self.up_thread.no_update.connect(self.no_update)
        self.up_thread.update_available.connect(self.update_available)
        self.up_thread.is_ready.connect(lambda: self.pbar.setMaximum(100))

    def delete_datebases(self):
        to_delete = [db for db in dbs if os.path.isfile(db)]
        if to_delete:
            for db in to_delete:
                self.log(f"Found {db}", _y)

            self.log('Delete databases?', _y)
            show_dbs = ", ".join([db for db in ["iOS", "iPadOS", "iPod", "MacOS", "iTunes", "Other"]])

            value = messaged_box("Delete", 
                        "UI/icons/updated.png",
                        "UI/icons/Question.png",
                        f"Delete databases for the follwoing devices?\n\n{show_dbs}",
                        yes=True, 
                        no=True,
                        ok=False)

            # Confirm deletion of all databases
            if value == 0:
                for db in to_delete:
                    try:
                        os.remove(db)
                    except PermissionError:
                        self.log(f"An error occurred while deleting {db}")

                # Reset the config.cfg file that contains the databases version
                if os.path.isfile('DBs\\config.cfg'):
                    os.remove('DBs\\config.cfg')

                MainApp.database_version = 'Not Available'
                self.toolBox.setItemText(1, f"Database - Version: {MainApp.database_version}")
                self.log("Deleted databases.", _s)
                self.reset_data()
            else:
                self.log('Aborted by user.', _d)

        else:
            self.log('There are no databases to delete.')

    def backup_databases(self):
        # backup all databases to a zip file

        to_backup = [db for db in dbs if os.path.isfile(db)]
        if to_backup:
            get_dbs = os.listdir('DBs\\')
            self.log("Backing up databases...")
            self.log("Zipping...")
            file_name = f'DBs\\DBs-{time.time()}-.7z'
            with py7zr.SevenZipFile(file_name, 'w') as file:
                for each in get_dbs:
                    if each[-3::] == '.db':
                        file.writeall(f'DBs\\{each}')

            if os.path.isfile(file_name):
                self.log("Backed up databases.", _s)
                self.log(f"Backup: {file_name}", _s)
            else:
                self.log("Something went wrong, try again later.", _d)

        else:
            self.log('There are no databases to backup.', _y)

    def hide_irrelevant_columns(self, table):

        if MainApp.hide_columns:
            for column in [1, 3, 4, 6]:
                table.hideColumn(column)

        return 0

    def load_data(self, device=None):
        # Do not alter/update QTreeWidget when checking for database update, if there is no updates available
        if no_update:
            return

        #==================================================
        #                 QTabWidget 
        #==================================================
        self.main_tab.currentChanged.connect(lambda: self.assign_index(self.main_tab.currentIndex()))
        self.main_tab.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.main_tab.setCurrentIndex(MainApp.current_index)

        #==================================================
        #               iOS Tab 
        #==================================================
        self.ios_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ios_tree.customContextMenuRequested.connect(self.context_menu)
        self.ios_tree.setHeaderLabels(['Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ios_devices.db'):
            conn = sqlite3.connect("DBs\\ios_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            
            for dev_info in get_data.fetchall():
                if device is None:
                    if MainApp.signed_only:
                        if MainApp.show_relevant:
                            if int(dev_info[2].split('.')[0]) == MainApp.relevant_version:
                                if str(dev_info[8]) == '1':
                                    QTreeWidgetItem(self.ios_tree, 
                                        [
                                            str(dev_info[0]),
                                            str(dev_info[1]),
                                            str(dev_info[2]),
                                            str(dev_info[3]),
                                            str(dev_info[4]), 
                                            naturalsize(int(str(dev_info[5]))),
                                            str(dev_info[6]),
                                            str(dev_info[7])]
                                        )
                        else:
                            if str(dev_info[8]) == '1':
                                QTreeWidgetItem(self.ios_tree, 
                                    [
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                    )

                    else:
                        QTreeWidgetItem(self.ios_tree, 
                            [
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                                )
                else:
                    if device.lower() == dev_info[0].lower():
                        QTreeWidgetItem(self.ios_tree, 
                            [
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                            )
                        
            conn.close()

        self.hide_irrelevant_columns(self.ios_tree)

        #==================================================
        #               iPad Tab 
        #==================================================
        self.ipad_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ipad_tree.customContextMenuRequested.connect(self.context_menu)
        self.ipad_tree.setHeaderLabels(['Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ipad_devices.db'):
            conn = sqlite3.connect("DBs\\ipad_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            for dev_info in get_data.fetchall():
                if MainApp.signed_only:
                    if MainApp.show_relevant:
                        if int(dev_info[2].split('.')[0]) == MainApp.relevant_version:
                            if str(dev_info[8]) == '1':
                                parent = QTreeWidgetItem(self.ipad_tree, 
                                    [
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                        )
                    else:
                        if str(dev_info[8]) == '1':
                            parent = QTreeWidgetItem(self.ipad_tree, 
                            [
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                                )
                else:
                    parent = QTreeWidgetItem(self.ipad_tree, 
                        [
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

            conn.close()
        self.hide_irrelevant_columns(self.ipad_tree)

        #==================================================
        #               iPod Tab 
        #==================================================
        self.ipod_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ipod_tree.customContextMenuRequested.connect(self.context_menu)
        self.ipod_tree.setHeaderLabels(['Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ipod_devices.db'):
            conn = sqlite3.connect("DBs\\ipod_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            num = 1
            for dev_info in get_data.fetchall():
                if MainApp.signed_only:
                    if MainApp.show_relevant:
                        if int(dev_info[2].split('.')[0]) == MainApp.relevant_version:
                            if str(dev_info[8]) == '1':
                                parent = QTreeWidgetItem(self.ipod_tree, 
                                    [
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                        )
                    else:
                        if str(dev_info[8]) == '1':
                            parent = QTreeWidgetItem(self.ipod_tree, 
                                [
                                    str(dev_info[0]),
                                    str(dev_info[1]),
                                    str(dev_info[2]),
                                    str(dev_info[3]),
                                    str(dev_info[4]), 
                                    naturalsize(int(str(dev_info[5]))),
                                    str(dev_info[6]),
                                    str(dev_info[7])]
                                    )
                else:
                    parent = QTreeWidgetItem(self.ipod_tree, 
                        [
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

            conn.close()
        self.hide_irrelevant_columns(self.ipod_tree)

        #==================================================
        #               MacBook Tab
        #==================================================
        self.mac_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mac_tree.customContextMenuRequested.connect(self.context_menu)
        self.mac_tree.setHeaderLabels(['Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\macbook_devices.db'):
            conn = sqlite3.connect("DBs\\macbook_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE FROM devices")

            for dev_info in get_data.fetchall():
                parent = QTreeWidgetItem(self.mac_tree, 
                    [
                        str(dev_info[0]),
                        str(dev_info[1]),
                        str(dev_info[2]),
                        str(dev_info[3]),
                        str(dev_info[4]), 
                        naturalsize(int(str(dev_info[5]))),
                        str(dev_info[6]),
                        str(dev_info[7])]
                        )

            conn.close()
        self.hide_irrelevant_columns(self.mac_tree)

        #==================================================
        #               iTunes Tab 
        #==================================================
        self.itunes_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.itunes_tree.customContextMenuRequested.connect(self.context_menu)
        self.itunes_tree.setHeaderLabels(['Platform', 'Version', 'Date Found', 'URL32', 'URL64'])
        if os.path.isfile('DBs\\iTunes.db'):
            conn = sqlite3.connect("DBs\\iTunes.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT PLATFORM, _VERSION, DATEFOUND, URL32, URL64, RELEASEDATE FROM devices")
            for dev_info in get_data.fetchall():
                parent = QTreeWidgetItem(self.itunes_tree, 
                    [
                        str(dev_info[0]),
                        str(dev_info[1]),
                        str(dev_info[2]),
                        str(dev_info[3]),
                        str(dev_info[4])
                    ])
            if MainApp.hide_columns:
                self.itunes_tree.hideColumn(3)
                self.itunes_tree.hideColumn(4)

            conn.close()
        #==================================================
        #               Other Tab 
        #==================================================
        self.other_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.other_tree.customContextMenuRequested.connect(self.context_menu)
        self.other_tree.setHeaderLabels(['Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\other.db'):
            conn = sqlite3.connect("DBs\\other.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            for dev_info in get_data.fetchall():
                if MainApp.signed_only:
                    if str(dev_info[8]) == '1':
                        parent = QTreeWidgetItem(self.other_tree, 
                            [
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                                )
                else:
                    parent = QTreeWidgetItem(self.other_tree, 
                        [
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

            conn.close()
        self.hide_irrelevant_columns(self.other_tree)
        self.check_databases()

    def reset_data(self):
        self.ios_tree.clear()
        self.ipad_tree.clear()
        self.ipod_tree.clear()
        self.mac_tree.clear()
        self.itunes_tree.clear()
        self.other_tree.clear()
        self.load_data(device=None)

    def no_update(self, val):
        if val == 'db':
            messaged_box("Database Update", 
                        "UI/icons/updated.png", 
                        "UI/icons/Checkmark_1.png", 
                        f"Already up to date.\nDB Version: {MainApp.database_version}")
            return

        # If iFirnware Toolkit is up to date
        messaged_box("iFirmware Update", 
                    "UI/icons/updated.png", 
                    "UI/icons/Checkmark_1.png", 
                    f"Already up to date.\nVersion: {app_version}")

    def hash_file(self, val):
        if val[2]:
            sha1 = hashlib.sha1()
            with open(val[0], 'rb') as file:
                sha1.update(file.read())
            
            hashed = sha1.hexdigest()
            if hashed == val[1]:
                self.log(f"SHA1 matched: {val[1]}", _s)
            else:
                self.log(f"SHA1 mismatched: {val[1]}", _d)

    def update_available(self, val):
        value = messaged_box("iFTK Update",
                    "UI/icons/updated.png",
                    "UI/icons/Information.png",
                    f"A new version is available.\nCurrent: {app_version}\nNew: {val}", get=True)
                    
        if value == 1:
            url = "https://github.com/i0nsec/iFirmware-Toolkit/releases"
            self.log(f"Opening your default browser to download the new version\n{url}", _s)
            webbrowser.open(url)

    def send_to_log(self, val):
        self.log(val)

    def change_dir(self):
        new_dest = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        if not new_dest:
            return

        MainApp.dest = new_dest
        self.log(f"New path: {MainApp.dest}", _s)

    def delete_firmwares(self):
        if os.path.isdir(MainApp.dest):
            self.log("Delete firmware files?", _y)
            files = os.listdir(MainApp.dest)

            if files:
                to_delete = []
                for file in files:
                    if file[-5:] == '.ipsw':
                        to_delete.append(os.path.join(MainApp.dest, file))
                        continue 

                if to_delete:
                    for ipsw in to_delete:
                        self.log(f"Found {ipsw}")

                    show_ipsws = "\n".join([file for file in files if file[-5:] == '.ipsw'])

                    value = messaged_box("Delete", 
                                "UI/icons/updated.png",
                                "UI/icons/Question.png",
                                f"Delete the follwoing firmware files?\n\n{show_ipsws}",
                                ok=False,
                                yes=True,
                                no=True)

                    if value == 0:
                        for del_ipsw in to_delete:
                            os.remove(del_ipsw)

                        self.log('Finished deleting.', _s)

                    else:
                        self.log("Aborted by user.", _d)
            else:
                self.log('There are no firmware files to delete.')

        else:
            self.log("Destination folder does not exist.", _d)

    def custom_log_messages(self, log, category):
        if type(log) is list:
            return f"<p style=\"margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:\'Segoe UI\'; color:{log[1]};\">{log[0]}</span></p>\n"

        return f"<p style=\"margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:\'Segoe UI\'; color:{category};\">{log}</span></p>\n"

    def log(self, new_log, category=''):
        if new_log is not None:
            self.logger.info(self.custom_log_messages(new_log, category))

        with open('logs.txt', 'r') as logs:            
            log = logs.read()
            self.text_log = QTextBrowser(self.logs)
            font = QtGui.QFont()
            font.setFamily('Segoe UI Semibold')
            font.setPointSize(10)
            self.text_log.setFont(font)
            self.text_log.setObjectName("text_log")
            self.gridLayout_4.addWidget(self.text_log, 0, 0, 1, 2)
            self.text_log.setHtml(log)
            self.text_log.moveCursor(QtGui.QTextCursor.End)
            self.text_log.setStyleSheet("border: none;")

    def init_logger(self):
        # Reset the log file before initializing a new logger
        # clear_log() uses this method to flush the log file

        if os.path.exists('logs.txt'):
            with open('logs.txt', 'w') as file:
                pass

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        output = logging.FileHandler('logs.txt')
        self.logger.addHandler(output)

    def reset_logger(self):
        self.text_log.setText('')
        self.logger.handlers[0].close()
        self.logger.removeHandler(self.logger.handlers[0])
        self.init_logger()

    def enable_btns(self, val):
        if val:
            self.main_download.setDisabled(val)
            self.ipsw_delete.setDisabled(val)
            self.verify.setDisabled(val)
            self.db_delete.setDisabled(val)
            self.options.setDisabled(val)
            return 
        
        self.main_download.setEnabled(True)
        self.ipsw_delete.setEnabled(True)
        self.verify.setEnabled(True)
        self.db_delete.setEnabled(True)
        self.options.setEnabled(True)

    def assign_index(self, currentIndex):
        self.getIndex = currentIndex

        if currentIndex == 0:
            MainApp.current_index = 0
            self.getIndex = self.ios_tree

        elif currentIndex == 1:
            MainApp.current_index = 1
            self.getIndex = self.ipad_tree

        elif currentIndex == 2:
            MainApp.current_index = 2
            self.getIndex = self.ipod_tree

        elif currentIndex == 3:
            MainApp.current_index = 3
            self.getIndex = self.mac_tree

        elif currentIndex == 4:
            MainApp.current_index = 4
            self.getIndex = self.itunes_tree

        elif currentIndex == 5:
            MainApp.current_index = 5
            self.getIndex = self.other_tree

    def context_menu(self, point):

        index = self.getIndex.indexAt(point)
        if not index.isValid():
            return

        item = self.getIndex.itemAt(point)
        menu = QMenu()
        menu.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setFamily("Segoe UI Semibold")
        menu.setFont(font)
        menu.setStyleSheet("""
            QMenu {
                background-color: #3700B3;
                color: #fff;
            }

            QMenu::item:selected {
                margin: 2px;
            }

            QMenu::icon:checked {
                background: gray;
                border: 1px inset gray;
                position: absolute;
                top: 1px;
                right: 1px;
                bottom: 1px;
                left: 1px;
            }

            QMenu::separator {
                height: 1px;
                background: lightblue;
                margin: 10px;
            }

            QMenu::indicator {
                width: 13px;
                height: 13px;
            }
            """)

        if MainApp.current_index == 4:
            name_all = item.text(0) # Name and version of selected device
            version_all = item.text(1) # Version number for current selected device 
            url32 = item.text(3) # URL for a 32Bit iTunes 
            url64 = item.text(4) # URL for a 64Bit iTunes

            copy = menu.addAction("Copy All")
            copy.setIcon(QtGui.QIcon("UI/icons/Copy.png"))
            copy_url = menu.addAction("Copy URL:32Bit")
            copy_url.setIcon(QtGui.QIcon("UI/icons/CopyURL.png"))
            copy_url = menu.addAction("Copy URL:64Bit")
            copy_url.setIcon(QtGui.QIcon("UI/icons/CopyURL.png"))
            menu.addSeparator()
            delete = menu.addAction("Delete All")
            delete.setIcon(QtGui.QIcon("UI/icons/Delete.png"))

        else:
            name = item.text(0) # Name of current selected device
            identifier = item.text(1) # Identifier ID for current selected device 
            version = item.text(2) # Version of current selected device 
            build = item.text(3) # Build ID of current selected device 
            hash_ = item.text(4) # SHA1 value for current selected device 
            url = item.text(6) # URL of current selected device 

            download = menu.addAction("Download")
            download.setIcon(QtGui.QIcon("UI/icons/Download.png"))
            copy = menu.addAction("Copy")
            copy.setIcon(QtGui.QIcon("UI/icons/Copy.png"))
            copy_hash = menu.addAction("Copy SHA1")
            copy_hash.setIcon(QtGui.QIcon("UI/icons/CopyHash.png"))
            copy_url = menu.addAction("Copy URL")
            copy_url.setIcon(QtGui.QIcon("UI/icons/CopyURL.png"))
            menu.addSeparator()
            delete = menu.addAction("Delete")
            delete.setIcon(QtGui.QIcon("UI/icons/Delete.png"))

        value = menu.exec_(self.getIndex.mapToGlobal(point))

        try:
            if value.text() == 'Copy':
                QApplication.clipboard().setText(f"{name} - {identifier} - {version} - {build}")

            elif value.text() == 'Copy SHA1':
                QApplication.clipboard().setText(hash_)

            elif value.text() == 'Copy All':
                QApplication.clipboard().setText(f"{name_all} - {version_all}")

            elif value.text() == 'Copy URL:32Bit':
                QApplication.clipboard().setText(url32)

            elif value.text() == 'Copy URL:64Bit':
                QApplication.clipboard().setText(url64)

            elif value.text() == 'Copy URL':
                QApplication.clipboard().setText(url)
            
            elif value.text() == 'Download':
                self.download_one_firmware(name, url, hash_, build, version)
            
            elif value.text() == 'Delete':
                delete_from_database(url, MainApp.current_index, name)

            elif value.text() == 'Delete All':
                delete_from_database(url32, MainApp.current_index, name_all)

        except AttributeError:
            return 1

    def check_if_device_connected(self):
        self.check_conn = CheckConnection()
        self.check_conn.start()
        self.check_conn.is_connected.connect(self.print_to_label)
        self.check_conn.not_connected.connect(self.clear_print_to_label)

    def clear_print_to_label(self):
        if not MainApp.notified:
            self.toolBox.setItemText(0, "iDevice - Not Connected.")
            self.idevice_restore.clearContents()
            MainApp.notified = True
            MainApp.connected = False

    def print_to_label(self):

        if MainApp.connected:
            return

        if MainApp.notified:
            MainApp.notified = False
            return

        try:
            lockdown = lockdown_.create_using_usbmux()
        except exceptions.PasswordRequiredError:
            self.toolBox.setItemText(0, f"iDevice - Password Required. Unlock Device and Hit Trust.")
            return
        except (exceptions.UserDeniedPairingError, ConnectionAbortedError, exceptions.NoDeviceConnectedError, SSLZeroReturnError):
            self.toolBox.setItemText(0, f"iDevice - User Denied Pairing.")
            return
        except (TypeError, SSLEOFError):
            self.toolBox.setItemText(0, f"iDevice - Something went wrong.")
            return

        current_device = {
            "DeviceName": '',
            "DisplayName": '',
            "ProductType": '',
            "com.apple.mobile.battery": '',
            "ActivationState": '',
            "fm-activation-locked": '',
            "Blacklisted": '',
            "InternationalMobileEquipmentIdentity": '',
            "InternationalMobileEquipmentIdentity2": '',
            "ecid": '',
            "SerialNumber": '',
            "ProductVersion": '',
            "BuildVersion": '',
            "SIMStatus": '',
            "SIMTrayStatus": '',
            "IntegratedCircuitCardIdentity": '',
            "InternationalMobileSubscriberIdentity": '',
            "CarrierBundleInfoArray": '',
            "PhoneNumber": '',
            "UniqueDeviceID": '',
            "WiFiAddress": '',
            "BluetoothAddress": '',
            "CPUArchitecture": '',
            "FirmwareVersion": '',
        }
        for key in current_device:
            try:
                if key == "ProductVersion":
                    MainApp.current_device[key] = lockdown.get_value(key="ProductVersion")

                    if os.path.exists('DBs\\ios_devices.db'):
                        conn = sqlite3.connect('DBs\\ios_devices.db')
                        cur = conn.cursor()
                        cur.execute(f"SELECT * FROM devices where IDENTIFIER='{MainApp.current_device['ProductType']}'")
                        data = cur.fetchall()
                        if data:
                            for device in data:
                                version = device[3]
                                if version == MainApp.current_device["ProductVersion"]:
                                    MainApp.current_device["ProductVersion"] = f"{lockdown.get_value(key='ProductVersion')} - Latest version."
                                else:
                                    MainApp.current_device["ProductVersion"] = f"{lockdown.get_value(key='ProductVersion')} - Update available ({version})."
                                break
                    continue

                if key == 'fm-activation-locked':
                    try:
                        result = lockdown.get_value(key='NonVolatileRAM')['fm-activation-locked'].decode('utf8')
                        if result == 'NO':
                            MainApp.current_device[key] = 'OFF'
                        else:
                            MainApp.current_device[key] = 'ON'
                    except (KeyError, TypeError):
                        MainApp.current_device[key] = 'Not available.'
                    
                    continue

                if key == 'CarrierBundleInfoArray':
                    result = lockdown.get_value(key="CarrierBundleInfoArray")
                    if not result:
                        MainApp.current_device[key] = 'Not available.'
                    else:
                        MainApp.current_device[key] = result

                    continue

                if key == 'com.apple.mobile.battery':
                    result = lockdown.get_value('com.apple.mobile.battery')['BatteryCurrentCapacity']
                    if result:
                        MainApp.current_device[key] = f"{result}%"
                    else:
                        MainApp.current_device[key] = 'Not available.'

                    continue

                if key == 'SIMStatus':
                    result = lockdown.get_value(key="SIMStatus")
                    if result == 'kCTSIMSupportSIMStatusNotInserted':
                        MainApp.current_device[key] = 'No SIM.'
                    else:
                        MainApp.current_device[key] = 'SIM is inserted.'

                    continue

                if key == 'SIMTrayStatus':
                    result = lockdown.get_value(key="SIMTrayStatus")
                    if result == 'kCTSIMSupportSIMTrayAbsent':
                        MainApp.current_device[key] = 'SIM Tray is not inserted.'
                    else:
                        MainApp.current_device[key] = 'SIM Tray is inserted.'

                    continue

                if key == 'DisplayName':
                    result = lockdown.display_name
                    if result:
                        MainApp.current_device[key] = result
                    else:
                        MainApp.current_device[key] = 'Not available.'

                    continue
                
                if key == 'ecid':
                    result = lockdown.ecid
                    if result:
                        MainApp.current_device[key] = str(result)
                    else:
                        MainApp.current_device[key] = 'Not available.'

                    continue
                
                if key == 'InternationalMobileSubscriberIdentity':
                    result = lockdown.get_value()["InternationalMobileSubscriberIdentity"]
                    if result:
                        MainApp.current_device[key] = result
                    else:
                        MainApp.current_device[key] = "Not available."

                    continue

                MainApp.current_device[key] = lockdown.get_value(key=key)

            except (exceptions.MissingValueError, KeyError):
                 MainApp.current_device[key] = "Not available."
                 continue
            except ConnectionAbortedError:
                self.log("Lost connection to device.", _d)
                return 

        device = MainApp.current_device.values()
        carrires = []

        for index, value in enumerate(device):
            try:
                if type(value) is list:
                    for xcarrier in value:
                        if "Verizon" in xcarrier['CFBundleIdentifier']:
                            carrires.append(f"Verizon Wireless:{xcarrier['CFBundleVersion']}")
                            continue

                        if "TMobile" in xcarrier['CFBundleIdentifier']:
                            carrires.append(f"T-Mobile:{xcarrier['CFBundleVersion']}")
                            continue

                        if "ATT" in xcarrier['CFBundleIdentifier']:
                            carrires.append(f"AT&T:{xcarrier['CFBundleVersion']}")
                            continue
    
                        carrires.append(xcarrier['CFBundleIdentifier'])
                    item = QTableWidgetItem(', '.join(carrires))
                    font = QtGui.QFont()
                    font.setBold(True)
                    item.setFont(font)
                    self.idevice_restore.setItem(index, 0, item)
                    continue
                
                self.item = QTableWidgetItem(str(value))
                font = QtGui.QFont()
                font.setPointSize(11)
                font.setFamily("Segoe UI Semibold")
                self.item.setFont(font)

                if value == "OFF" or value == "Activated":
                    self.item.setForeground(QtGui.QBrush(QtGui.QColor(145, 200, 129)))
                    self.idevice_restore.setItem(index, 0,  self.item)
                    continue

                if value == "ON" or value == "Unactivated":
                    self.item.setForeground(QtGui.QBrush(QtGui.QColor(150, 0, 0)))
                    self.idevice_restore.setItem(index, 0,  self.item)
                    continue

                self.idevice_restore.setItem(index, 0,  self.item)

            except (exceptions.NoDeviceConnectedError, exceptions.MissingValueError, exceptions.LockdownError) as msg:
                continue    

        MainApp.connected = True
        MainApp.udid = lockdown.get_value(key='UniqueDeviceID')
        with open('.devices.txt', 'a') as device_udids:
            device_udids.write(f"{time.asctime()};; {MainApp.udid}\n")

        self.toolBox.setItemText(0, f"iDevice - Connected: {MainApp.udid}")
        self.log(f"New device connected, {MainApp.current_device['DisplayName']}", _s)

    def enter_recovery_(self):
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return
        
        value = messaged_box("Enter Recovery", 
                            "UI/icons/updated.png",
                            "UI/icons/Question.png",
                            f"Reboot device into recovery mode?",
                            ok=False,
                            yes=True,
                            no=True)
        
        if value == 1:
            return

        try:
            self.log("Device is entering recovery mode...", _y)
            lockdown = lockdown_.create_using_usbmux()
            lockdown.enter_recovery()
        except exceptions.NoDeviceConnectedError as error_msg:
            pass

    def shutdown(self):
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return
        
        value = messaged_box("Shutdown", 
                            "UI/icons/updated.png",
                            "UI/icons/Question.png",
                            f"Shutdown device?",
                            ok=False,
                            yes=True,
                            no=True)
        
        if value == 1:
            return
        
        try:
            self.log("Device is shutting down...", _y)
            lockdown = lockdown_.create_using_usbmux()
            do_shutdown = diagnostics.DiagnosticsService(lockdown=lockdown)
            do_shutdown.shutdown()

        except exceptions.NoDeviceConnectedError as error_msg:
            pass

    def restart(self):
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return
        
        value = messaged_box("Restart", 
                            "UI/icons/updated.png",
                            "UI/icons/Question.png",
                            f"Restart device?",
                            ok=False,
                            yes=True,
                            no=True)
        
        if value == 1:
            return

        try:
            self.log("Device is restarting...", _y)
            lockdown = lockdown_.create_using_usbmux()
            do_shutdown = diagnostics.DiagnosticsService(lockdown=lockdown)
            do_shutdown.restart()

        except exceptions.NoDeviceConnectedError as error_msg:
            pass

    def erase(self):
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return
        
        value = messaged_box("Erase", 
                            "UI/icons/updated.png",
                            "UI/icons/clean-code-small.png",
                            f"WARNING: ALL CONTENT AND SETTINGS WILL BE ERASED, THIS ACTION CANNOT BE UNDONE.\n\nErase device?",
                            ok=False,
                            yes=True,
                            no=True)
        
        if value == 1:
            return

        lockdown = lockdown_.create_using_usbmux()
        self.erase_threaded = Erase(lockdown=lockdown)
        self.erase_threaded.start()
        self.erase_threaded.log.connect(self.log)
        self.erase_threaded.pbar.connect(self.progress_bar_update)
        self.erase_threaded.is_finished.connect(lambda: self.pbar.setMaximum(100))

    def activate_this_device(self):
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return
        
        value = messaged_box("Activate", 
                            "UI/icons/updated.png",
                            "UI/icons/Question.png",
                            f"Activate device?",
                            ok=False,
                            yes=True,
                            no=True)
        
        if value == 1:
            return

        self.all_device_buttons(True)
        lockdown = lockdown_.create_using_usbmux()
        self.activate_threaded = Activate(lockdown=lockdown)
        self.activate_threaded.start()
        self.activate_threaded.log.connect(self.log)
        self.activate_threaded.pbar.connect(self.progress_bar_update)
        self.activate_threaded.is_finished.connect(lambda: self.pbar.setMaximum(100))
        self.activate_threaded.reset.connect(lambda: self.all_device_buttons(False))

    def export_device_info(self):
        self.log("Exporting device information to a file...")
        if not MainApp.connected:
            self.log("Device is not connected.", _d)
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save File",  f"{MainApp.current_device['DeviceName']}.txt", '.txt', )
        if not file_name:
            return
        
        with open(file_name, 'w') as file:
            for category, device_value in MainApp.current_device.items():
                file.write(f"{category}: {device_value}\n")
            
            file.write(f"\n==============================\nTime: {time.asctime()}")

        self.log(f"Exported data to {file_name}", _s)

    def all_device_buttons(self, val):
        if val:
            self.activate_device.setDisabled(True)
            self.enter_recovery.setDisabled(True)
            self.erase_btn.setDisabled(True)
            self.pull_all_reports.setDisabled(True)
            self.clear_reports.setDisabled(True)
            self.flush_reports.setDisabled(True)
            self.deactivate_device.setDisabled(True)
            self.reboot.setDisabled(True)
            self.poweroff.setDisabled(True)
            self.show_tabs.setDisabled(True)
            self.start_url.setDisabled(True)
            return
        
        self.activate_device.setEnabled(True)
        self.enter_recovery.setEnabled(True)
        self.erase_btn.setEnabled(True)
        self.pull_all_reports.setEnabled(True)
        self.clear_reports.setEnabled(True)
        self.flush_reports.setEnabled(True)
        self.deactivate_device.setEnabled(True)
        self.reboot.setEnabled(True)
        self.poweroff.setEnabled(True)
        self.show_tabs.setEnabled(True)
        self.start_url.setEnabled(True)

class VerifyFirmware(QThread):
    progress_update = pyqtSignal(int)
    send_to_log = pyqtSignal(str)
    is_ready = pyqtSignal(bool)
    enable_btn = pyqtSignal(bool)

    def __init__(self, parent=None, current_tab=int):
        QThread.__init__(self)
        self.current_tab = current_tab

    def run(self):
        if os.path.isdir(MainApp.dest):
            files = os.listdir(MainApp.dest)
            if files:
                to_hash = []
                for file in files:
                    if file[-5:] == '.ipsw':
                        to_hash.append(os.path.join(MainApp.dest, file))

                if to_hash:
                    self.send_to_log.emit(f"Found {len(to_hash)} to be verified")
                    self.send_to_log.emit("Using SHA1 to hash...\n")
                    self.progress_update.emit(1)

                    for each_file in to_hash:
                        sha1 = hashlib.sha1()
                        with open(each_file, 'rb') as file:
                            while True:
                                chunk = file.read(sha1.block_size)
                                if not chunk:
                                    break

                                sha1.update(chunk)

                            hash_sum = sha1.hexdigest()
                            each_file = each_file.split('\\')[-1::][0]
                            self.send_to_log.emit("_"*len(each_file))
                            self.send_to_log.emit(f"|{each_file}")
                            self.send_to_log.emit(f"|_SHA1: {hash_sum}")
                            self.verify_in_db(hash_sum)

                    self.is_ready.emit(True)
                    self.enable_btn.emit(True)
            else:
                self.send_to_log.emit('There are no firmware files in the current directory to verify.')
                self.enable_btn.emit(True)

    def verify_in_db(self, hash_value):
        for db in [
                'DBs\\ios_devices.db',
                'DBs\\ipad_devices.db',
                'DBs\\ipod_devices.db',
                'DBs\\macbook_devices.db',
                'DBs\\other.db']:
            with sqlite3.connect(db) as db_conn:
                db_cursor = db_conn.cursor()
                get_data = db_cursor.execute("SELECT SHA1SUM FROM devices WHERE SHA1SUM=?", (hash_value,))

                try:
                    db_sha1 = get_data.fetchall()[0][0]

                    if db_sha1 == hash_value:
                        self.send_to_log.emit(f"|__SHA1 has been verified.")
                        self.send_to_log.emit(f"|___DB:{db_sha1}")
                        return

                except IndexError:
                    pass
        else:
            self.send_to_log.emit("|__SHA1 did not match!")

class AppUpdate(QThread):
    send_to_log = pyqtSignal(list)
    update_available = pyqtSignal(str)
    no_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    is_ready = pyqtSignal(bool)

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        try:
            self.progress_update.emit(1)
            self.send_to_log.emit(['Checking for iFTK updates...', _w])
            from_url = f"{MainApp.server_address}/verval.txt"
            get_update = requests.get(from_url)
            if get_update.ok:
                is_up_to_date = get_update.text.rstrip()
                if is_up_to_date == app_version:
                    self.no_update.emit('Already up to date.')
                    self.send_to_log.emit(['Already up to date.', _s])
                else:
                    self.update_available.emit(f'{is_up_to_date}')
                    self.send_to_log.emit(['Update available.', _y])
                    self.send_to_log.emit([f'New: {is_up_to_date}', _y])

        except requests.exceptions.ConnectionError:
            self.send_to_log.emit(['Server is offline.\nOr check your internet connection.', _d])

        finally:
            self.is_ready.emit(True)

class DatabaseUpdate(QThread):
    send_to_log = pyqtSignal(list)
    no_update = pyqtSignal(str)
    refrush_ui = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    is_ready = pyqtSignal(bool)
    set_version = pyqtSignal(bool)

    def run(self):
        try:
            self.send_to_log.emit([f"Checking for database update...", _w])
            self.progress_update.emit(1)
            db_url = f"{MainApp.server_address}/updates/verval.txt"
            db_get = requests.get(db_url)

            if db_get.ok:
                with open('DBs\\config.cfg', 'w') as cfg:
                    cfg.write(str(db_get.json()))

                with open('DBs\\config.cfg', 'r') as cfg:
                    cfg = cfg.read()
                    cfg = cfg.replace("'", '"')
                    data = json.loads(cfg)

                up_to_date = data['date']
                MainApp.relevant_version = int(data['relevant'])

                # Check if remote version is up to date
                if up_to_date == MainApp.database_version:
                    self.no_update.emit('db')
                    self.send_to_log.emit(['Already up to date.', _s])
                    self.is_ready.emit(True)
                
                # If new version is available...
                else:
                    self.send_to_log.emit([f'New version is available.\nCurrent: {MainApp.database_version}\nNew: {up_to_date}', _y])
                    self.send_to_log.emit(['Getting database file...', _w])
                    
                    Url = f"{MainApp.server_address}/updates/DBs.7z"
                    get_data = requests.get(Url)

                    if get_data.ok:
                        with open('DBs.7z', 'wb') as db_file:
                            db_file.write(get_data.content)

                        self.send_to_log.emit(['Finished downloading.', _s])
                        self.send_to_log.emit(['Checking SHA256...', _y])

                        # Check sha1sum and verify files
                        sha256 = hashlib.sha256()
                        with open('DBs.7z', 'rb') as db_file:
                            sha256.update(db_file.read())

                        hashed = sha256.hexdigest()
                        self.send_to_log.emit([f"SHA256: {hashed}", _w])
                        
                        Url = f"{MainApp.server_address}/updates/sha256sum.txt"
                        get_data = requests.get(Url)
                        online_hash = 'Unavailable'

                        if get_data.ok:
                            online_hash = get_data.text.rstrip().lower()

                        if hashed == online_hash or MainApp.force_continue:
                            if not MainApp.force_continue:
                                self.send_to_log.emit(['SHA256 matched.', _s])
                            
                            self.send_to_log.emit(['Extracting files...', _w])
                            extract = py7zr.SevenZipFile('DBs.7z')
                            extract.extractall('DBs\\')
                            extract.close()
                            
                            self.send_to_log.emit(['Cleaning...', _w])
                            os.remove('DBs.7z')
                            self.send_to_log.emit(['Refrushing UI... ', _w])
                            self.refrush_ui.emit(True)
                            MainApp.database_version = up_to_date 

                        else:
                            self.send_to_log.emit(['SHA1 mismatched.', _d])
                            self.send_to_log.emit(['Run update again to continue anyway.', _d])
                            MainApp.force_continue = True

                    else:
                        self.send_to_log.emit([f'Something went wrong...\nCODE:{get_data.status_code}', _d])
                            
        except requests.exceptions.ConnectionError:
            self.send_to_log.emit(['Server is offline.\nOr check your internet connection.', _d])

        finally:
            self.is_ready.emit(True)
            self.set_version.emit(True)

class DownloadManagerSignal(QThread):
    enable_btns = pyqtSignal(bool)
    send_to_log = pyqtSignal(list)
    hash_file = pyqtSignal(list)

    def __init__(self, parent=None, dest_folder='', hash_value=''):
        QThread.__init__(self)
        self.dest_folder = dest_folder
        self.hash_value = hash_value

    def run(self):
        while dm.DownloadManager.is_downloading:
            time.sleep(0.01)
            if not dm.DownloadManager.is_downloading:
                self.send_to_log.emit(["Successfully stopped downloader.", _s])
                if MainApp.hash_firmware:
                    self.send_to_log.emit(['Hashing...', _w])
                    self.hash_file.emit([self.dest_folder, self.hash_value, True])

                self.enable_btns.emit(False)

class DeviceSearch(QThread):
    send_to_log = pyqtSignal(list)
    change_device_view = pyqtSignal(str)
    is_finished = pyqtSignal(bool)

    def __init__(self, parent=None, query='', current_tab=''):
        QThread.__init__(self)
        self.query = query
        self.current_tab = current_tab
        self.name = ''
    
    def run(self):
        self.send_to_log.emit([f"{self.query}", _w])
        to_download = dbs[self.current_tab]
        if os.path.isfile(to_download):
            try:
                conn = sqlite3.connect(to_download)
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM devices where DEVICE_NAME='{self.query}' COLLATE NOCASE OR IDENTIFIER='{self.query}' COLLATE NOCASE OR BUILDID='{self.query}' COLLATE NOCASE")
                data = cur.fetchall()
                if data:
                    for device in data:
                        try:
                            name = device[0]
                            identifier = device[1]
                            version = device[3]
                            buildid = device[4]
                            date = device[8]
                            self.send_to_log.emit([f"Name: {name}\nIdentifier: {identifier}\nVersion: {version}\nBuildID: {buildid}\nRelease Date: {date}\n------------------\n", _s])
                        finally:
                            self.change_device_view.emit(self.query)
            except sqlite3.OperationalError:
                pass
        
        self.is_finished.emit(True)

class DeviceSearchTableView(QThread):
    send_to_view = pyqtSignal(str)

    def __init__(self, parent=None, query=''):
        QThread.__init__(self)
        self.query = query

    def run(self):
        self.send_to_view.emit(self.query)

class CheckConnection(QThread):
    is_connected: bool = pyqtSignal(bool)
    not_connected: bool = pyqtSignal(bool)
    log = pyqtSignal(list)

    def __init__(self, parent=None):
        QThread.__init__(self)

    def run(self):
        while True:
            try:
                get_device = usbmux.list_devices()
            except OSError:
                get_device = None

            if not get_device:
                self.not_connected.emit(True)
            else:
                self.is_connected.emit(True)

            try:
                self.lockdown = lockdown_.create_using_usbmux(get_device[0].serial)
                self.lockdown.pair()
            except (exceptions.UserDeniedPairingError, ConnectionAbortedError, exceptions.PasswordRequiredError, exceptions.ConnectionFailedError):
                self.log.emit(["Connection to device was interrupted.", _d])
            except (IndexError, OSError, TypeError, KeyError):
                pass
            
            del get_device
            time.sleep(0.01)

class Erase(QThread):
    pbar = pyqtSignal(bool)
    is_finished = pyqtSignal(bool)
    log = pyqtSignal(list)

    def __init__(self, parent=None, lockdown=None):
        QThread.__init__(self)
        self.lockdown = lockdown

    def run(self):
        try:
            self.pbar.emit(True)
            self.log.emit(["Erasing...", _y])
            erase_it = mobilebackup2.Mobilebackup2Service(self.lockdown)
            erase_it.erase_device()
            self.is_finished.emit(True)
        except ConnectionAbortedError:
            self.log.emit(["Device has been erased.", _s])
        except exceptions.InvalidServiceError:
            self.log.emit(["Unable to erase device. Possibly because it's locked with an Apple ID.", _d])
        finally:
            self.is_finished.emit(True)

class Activate(QThread):
    pbar = pyqtSignal(bool)
    is_finished = pyqtSignal(bool)
    reset = pyqtSignal(bool)
    log = pyqtSignal(list)

    def __init__(self, parent=None, lockdown=None, full_path=None):
        QThread.__init__(self)
        self.lockdown = lockdown

    def run(self):
        try:
            self.pbar.emit(True)
            self.log.emit(["Activating device...", _y])
            activate_it = mobile_activation.MobileActivationService(self.lockdown)
            activate_it.activate()
            self.log.emit(["Device has been activated!", _s])
            MainApp.connected = False
        except AssertionError:
            self.log.emit(["Device seems to be already activated.", _d])
        except KeyError:
            self.log.emit(["Unable to activate device. Possibly because it's locked with an Apple ID.", _d])
        finally: 
            self.is_finished.emit(True)
            self.reset.emit(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainApp()
    app.exec_()