import requests
import os, sys
import hashlib
import time
import py7zr
import sqlite3
import json
import logging
from humanize import naturalsize
from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSignal, Qt, QThread
from PyQt5.QtWidgets import (
            QWidget, 
            QMainWindow,
            QApplication,
            QTextBrowser,
            QFileDialog,
            QMessageBox,
            QTreeWidgetItem,
            QMenu)

# Downloader module
import dm

__version__ = 'v1.0-0121b'
__dbversion__ = 'Not available'

# Get URL from config file
Server = ''
message_queue = [] # Used to display messages prior to launching iFTK. Will be used more in future versions
# The default destenation where firmwares will be downloaded
# Not changing this will make iTunes pick up a firmware easily
dest = f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates"
text_reset = '' # Clear the Live Log
download_urls = {}
relevant_version = 14 # Specific firmware version to display
relevant_only = True # Always show relevant firmwares only
no_update = False # Do not update QTreeWidget when checking for database update if there is no updates available
hash_ipsw = False # Whether to hash after a download is finished 
signed_only = True # Show signed firmwares only
force_continue = False # Force updating by checking for update again even  if SHA256 does not match
# Check if all required databases exist
dbs = [
        'DBs\\ios_devices.db',
        'DBs\\ipad_devices.db', 
        'DBs\\ipod_devices.db',
        'DBs\\macbook_devices.db',
        'DBs\\iTunes.db',
        'DBs\\other.db'
        ]

def CheckIntegrity(state):
    if state == 2:
        globals().update(hash_ipsw=True)
    else:
        globals().update(hash_ipsw=False)

def CheckDBS():
    for db in dbs:
        if not os.path.isfile(db):
            MainApp._signed_only.setDisabled(True)
            MainApp._show_relevant.setDisabled(True)
        else:
            MainApp._signed_only.setDisabled(False)
            MainApp._show_relevant.setDisabled(False)

def SingedOnly(state):
    if state == 2:
        globals().update(signed_only=True)
        window.reset_data()
        MainApp._show_relevant.setEnabled(True)
    else:
        globals().update(signed_only=False)
        window.reset_data()
        MainApp._show_relevant.setDisabled(True)

def ShowRelevant(state):
    if state == 2:
        globals().update(relevant_only=True)
        window.reset_data()
    else:
        globals().update(relevant_only=False)
        window.reset_data()

def DeleteFromDB(URL, current_index, name):

    window.log(f"Deleting {name} from database...")
    value = MessagedBox(
        "Delete",
        "icons/updated.png",
        "icons/Question.png",
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
                window.log(f"Deleted {name} from database")
        finally:
            window.reset_data()

    elif value == 1:
        window.log("Aborted by user.")
    
    else:
        print(value)
    

def MessagedBox(title, window_icon, icon, text, ok=True, copy=False, yes=False, no=False, abort=False):
    
    message = QMessageBox()

    # Title and icons
    message.setIconPixmap(QtGui.QPixmap(icon))
    message.setWindowIcon(QtGui.QIcon(window_icon))
    message.setWindowTitle(title)

    # Main message and styling
    message.setText(text)
    message.setStyleSheet("background-color:#212121; color: #fff; padding: 15px;")

    # Font for all
    font = QtGui.QFont()
    font.setPointSize(10)
    font.setFamily("Segoe UI Semibold")
    message.setFont(font)

    # Buttons 
    if ok:
        ok = message.addButton('Ok', message.ActionRole)
        ok.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        ok.setFont(font)
        ok.setStyleSheet("QPushButton {background-color: #0C632A;border: none;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #084D20;}")
    
    if copy:
        copy = message.addButton('Copy', message.ActionRole)
        copy.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        copy.setFont(font)
        copy.setStyleSheet("QPushButton {background-color: #0C632A;border: none;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #084D20;}")

    if yes:
        yes = message.addButton('Yes', message.ActionRole)
        yes.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        yes.setFont(font)
        yes.setStyleSheet("QPushButton {background-color: #0C632A;border: none;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #084D20;}")

    if no:
        no = message.addButton('No', message.ActionRole)
        no.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        no.setFont(font)
        no.setStyleSheet("QPushButton {background-color: #0C632A;border: none;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #084D20;}")

    if abort:
        abort = message.addButton('Abort', message.ActionRole)
        abort.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        abort.setFont(font)
        abort.setStyleSheet("QPushButton {background-color: #9a1717;border: none;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #801313;}")

    # Return value
    value = message.exec_()
    return value

class ShowOptionsUI(QWidget):
    
    def __init__(self):
        super(ShowOptionsUI, self).__init__()
        uic.loadUi("_config.ui", self)

    def closeEvent(self, event):
        self.stop()

    def stop(self):
        MainApp._options.setEnabled(True)

    def _show(self):
        self.show()
        self.setFixedSize(750, 200)

        # Reset line edit
        self.edit_line.clear()
        self.validate.clear()

        # Choose a file button
        self.edit_btn.clicked.connect(lambda: self.open_dialog())

        # Reset background color for the load button
        self.ok.setDisabled(True)
        self.ok.setStyleSheet("QPushButton {background-color: #777;border: none;color: #000;}QPushButton:hover {background-color: #084D20;}QToolTip { color: #fff; background-color: #000; border: none; }") 

    def open_dialog(self):

        # Pick a file
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
        if filename:

            # Show file name
            self.edit_line.setText(filename)
            try:
                created = filename.split("/")[-1].split("-")[1]
            except IndexError:
                created = None

            # Validate backup
            try:
                if float(created):
                    self.validate.setStyleSheet("color: #0b6c2d")
                    self.validate.setText(f"Validated: {time.ctime(float(created))}")

                    # Enable the load button
                    self.ok.setEnabled(True)
                    self.ok.setStyleSheet("QPushButton {background-color: #0C632A;border: none;color: #fff;}QPushButton:hover {background-color: #084D20;}QToolTip { color: #fff; background-color: #000; border: none; }") 
                    self.ok.clicked.connect(lambda: self.clean_and_refrush_ui(filename))
                    
            except TypeError:
                self.validate.setStyleSheet("color: #bf0000")
                self.validate.setText("ERROR: No file uploaded or invalid file type. Ex: DBs-[creation time in seconds]-.7z")

    def clean_and_refrush_ui(self, filename):
        try:
            if filename and filename[-2:] == '7z':
                
                # Delete old databases before restoring from a backup
                to_delete = [db for db in dbs if os.path.isfile(db)]
                if to_delete:
                    for db in to_delete:
                        os.remove(db)

                window.reset_data()

                extract = py7zr.SevenZipFile(filename)
                extract.extractall('.')
                extract.close()

        finally:
            window.load_data()
            window.reset_data()
            self.close()

class MainApp(QMainWindow):
    _signed_only = None
    _current_index = 0
    _show_relevant = None
    _options = None

    def __init__(self):
        super(MainApp, self).__init__()
        uic.loadUi("_iFTK.ui", self)
        self.show()

        # Change default destenation button
        self.location.clicked.connect(self.change_dir)

        # Open default destination button
        self.open_location.clicked.connect(lambda: self.open_folder())

        # Delete all firmwares 
        self.ipsw_delete.clicked.connect(self.delete_firmwares)

        # Verify local firmwares
        self.verify.clicked.connect(self.hash_local_firmwares)

        # Clear logs button
        self.clear_log.clicked.connect(self.reset_logger)

        # Check for database update button
        self._update.clicked.connect(self.database_update)

        # Delete all databases
        self.db_delete.clicked.connect(self.delete_datebases)
         
        # Backup databases 
        self.backup.clicked.connect(self.backup_databases)

        # Device search
        self.device_search.textChanged.connect(lambda: self.dev_search(self.device_search.text(), MainApp._current_index))

        # Model number lookup
        self.search_btn.clicked.connect(lambda: self.dev_lookup(self.search.text()))

        """CheckBoxes"""
        # Check integrity checkbox
        self.check_integrity.clicked.connect(lambda: CheckIntegrity(self.check_integrity.checkState()))
        # Show signed firmwares only
        self.show_signed.clicked.connect(lambda: SingedOnly(self.show_signed.checkState()))
        MainApp._signed_only = self.show_signed
        # Show relevant firmwares only. Only shows the devices that support that latest firmwares
        MainApp._show_relevant = self.show_relevant
        self.show_relevant.clicked.connect(lambda: ShowRelevant(self.show_relevant.checkState()))
        self.show_relevant.setChecked(True)

        # Config button
        self.op = ShowOptionsUI()
        self.options.clicked.connect(lambda: self.show_config())
        MainApp._options = self.options
        self.main_tab.setCurrentIndex(1)

        # Check for iFirmware updates button
        self.get_update.clicked.connect(self.update_btn_clicked)

        # Show current iFirmware version
        self.current_v.setText(__version__)

        # Main download button to download all signed firmwares for iPhones only
        self.main_download.clicked.connect(lambda: self.DownloadAllSigned(MainApp._current_index))

        # Export log 
        self.export_log.clicked.connect(self.export_logs)

    def export_logs(self):
        if not os.path.exists('.\\logs.txt'):
            return

        with open('./logs.txt', 'r') as file:
            _name = f"logs_{time.time()}.txt"
            
            with open(_name, 'w') as _file:
                _file.write(file.read())

            self.log(f"Exported logs to {_name}")

    def open_folder(self):
        try:
            os.startfile(dest)
        except FileNotFoundError:
            self.log("Directory does not exist.\niTunes is not installed, or it has not been initialized or used.")

    def show_config(self):
        self.options.setDisabled(True)
        self.op._show()

    def DownloadAllSigned(self, current_tab):

        if current_tab != 0:
            self.log("Only iOS is supported for this feature.")
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
                    if int(info[5].split('.')[0]) == relevant_version:
                        name = info[0]
                        #identifier = info[1] # Unused
                        sha1 = info[2]
                        url = info[3] 
                        buildid = info[6]
                        #version = info[5] # Unused
                        file_name = url.split('/')[-1:][0] # Get file name from URL
                        dest_folder = f"{dest}/{file_name}" # Full path with file name
                        download_urls[index] = [name, url, sha1, buildid]
                        index += 1
            
            self.enable_btns(True)
            dm.MainDownload.urls = download_urls
            dm.MainDownload.dest_folder = dest
            self.go_dm = dm.MainDownload()
            self.go_dm.list_items()

            self.disable_btns = DMButtonMngThreaded(dest_folder=dest_folder, hash_value=sha1)
            self.disable_btns.start()
            self.disable_btns.enable_btns.connect(self.enable_btns)
            self.disable_btns.send_to_log.connect(self.send_to_log)
            self.disable_btns.hash_file.connect(self.hash_file)

        else:
            self.log('No database was found.')

    def DownloadOneFirmware(self, dev_name, url, hash_value, buildid):

        # If the default directory for iTunes does not exist, create it
        if not os.path.exists(dest):
            os.makedirs(dest)

        self.log(f"Downloading: {dev_name} - {buildid}\n{hash_value}\n")

        value = MessagedBox("Download Firmware", 
                            "icons/updated.png",
                            "icons/Question.png",
                            f"Start downloading firmware for {dev_name}?",
                            ok=False,
                            yes=True,
                            no=True,
                            abort=False)

        if value == 0:
            file_name = url.split('/')[-1:][0] # Get file name from URL
            dest_folder = f"{dest}/{file_name}" # Full path with file name

            if os.path.isfile(dest_folder):
                self.log('Firmware already exists!')
                value = MessagedBox("Error", 
                                    "icons/updated.png",
                                    "icons/Question.png",
                                    "Firmware already exists, do you want to delete it and continue?",
                                    ok=False,
                                    yes=True,
                                    no=True)

                if value == 0:
                    os.remove(dest_folder)
                    self.log(f"Removed {dest_folder}")
                    self.enable_btns(True)
                    self.window = QMainWindow()
                    self.dm = dm.MainDownload()
                    self.dm.Download(url, dest_folder, dev_name)

                    self.disable_btns = DMButtonMngThreaded(dest_folder=dest_folder, hash_value=hash_value)
                    self.disable_btns.start()
                    self.disable_btns.enable_btns.connect(self.enable_btns)
                    self.disable_btns.send_to_log.connect(self.send_to_log)
                    self.disable_btns.hash_file.connect(self.hash_file)

                else:
                    self.log("Aborted by user.")
            else:
                self.enable_btns(True)
                self.dm = dm.MainDownload()
                self.dm.Download(url, dest_folder, dev_name)

                self.disable_btns = DMButtonMngThreaded(dest_folder=dest_folder, hash_value=hash_value)
                self.disable_btns.start()
                self.disable_btns.enable_btns.connect(self.enable_btns)
                self.disable_btns.send_to_log.connect(self.send_to_log)
                self.disable_btns.hash_file.connect(self.hash_file)

        elif value == 1:
            self.log(f"Skipping {dev_name}") 

    def database_update(self):

        # If hosts file does not exist, do not continue
        # Hosts file contains server information to connect to the server
        if not Server:
            self.log("No hosts file found.")
            return

        self.log("Checking for database update...")

        value = MessagedBox(
                            "Update", 
                            "icons/updated.png", 
                            "icons/database.png", 
                            "Check for database update?",
                            ok=False,
                            yes=True, 
                            no=True)

        if value == 0:
            self.db_thread = DatabaseUpdateThreaded()
            self.db_thread.start()
            # If no updates, show this window
            self.db_thread.no_update.connect(self.no_update)
            # Log all messages to live log
            self.db_thread.send_to_log.connect(self.send_to_log)
            # Update progress bar
            self.db_thread.progress_update.connect(self.update_progressbar)

            self.db_thread.refrush_ui.connect(self.reset_data)

        else:
            self.log('Aborted by user.')

    def dev_search(self, query, current_tab):

        self.worker_search = DeviceSearchThreaded(query=query, current_tab=current_tab)
        self.worker_search.start()
        # Log all messages
        self.worker_search.send_to_log.connect(self.send_to_log)
        # Reset live log when displaying results
        self.reset_logger()

    def dev_lookup(self, model):
        # Reset user input
        self.search.clear()

        self.worker_lookup = ModelLookupThreaded(model=model)
        self.worker_lookup.start()
        # Update progress bar
        self.worker_lookup.progress_update.connect(self.update_progressbar)
        # Log all messages to live log
        self.worker_lookup.send_to_log.connect(self.send_to_log)
        # Display results in a new window
        self.worker_lookup.show_in_ui.connect(self.show_in_ui)

    def hash_local_firmwares(self):
        self.hash_firmware = HashingThreaded(current_tab=MainApp._current_index)
        self.hash_firmware.start()
        self.hash_firmware.send_to_log.connect(self.send_to_log)
        self.hash_firmware.progress_update.connect(self.update_progressbar)

    def update_btn_clicked(self):

        # If hosts file does not exist, do not continue
        # Hosts file contains server information to connect to the server
        if not Server:
            self.log("No hosts file found.")
            return 

        self.up_thread = SoftwareUpdateThreaded()
        self.up_thread.start()
        self.up_thread.progress_update.connect(self.update_progressbar)
        self.up_thread.send_to_log.connect(self.send_to_log)
        self.up_thread.no_update.connect(self.no_update)
        self.up_thread.update_available.connect(self.update_available)

    def show_in_ui(self, val):

        data = f"Name: {val[0]}\nIdentifier: {val[1]}\nBoardconfig: {val[2]}\nPlatform: {val[3]}\nCPID: {val[4]}\n"

        value = MessagedBox("Search results",
                    "icons/Search1.png",
                    "icons/Info.png",
                    data, copy=True)

        if value == 0:
            pass
        elif value == 1:
            self.log("Copied results!")
            QApplication.clipboard().setText(data)

    def delete_datebases(self):

        to_delete = [db for db in dbs if os.path.isfile(db)]
        try:
            if to_delete:
                self.pbar.setValue(10)
                for db in to_delete:
                    self.log(f"Found {db}")

                self.log('Delete databases?')
                show_dbs = "\n".join([db for db in to_delete])

                value = MessagedBox("Delete", 
                            "icons/updated.png",
                            "icons/Question.png",
                            f"Delete databases?\n\n{show_dbs}",
                            yes=True, 
                            no=True,
                            ok=False)

                # Confirm deletion of all databases
                if value == 0:
                    for db in to_delete:
                        os.remove(db)

                    # Reset the config.cfg file that contains the databases version
                    if os.path.isfile('DBs\\config.cfg'):
                        os.remove('DBs\\config.cfg')

                    globals().update(__dbversion__='Not Available')
                    self.log("Deleted databases.")
                    self.pbar.setValue(100)

                    self.reset_data()
                else:
                    self.log('Aborted by user.')

            else:
                self.log('There are no databases to delete.')

        finally:
            self.pbar.setValue(100)

    def backup_databases(self):

        to_backup = [db for db in dbs if os.path.isfile(db)]
        try:
            if to_backup:
                self.pbar.setValue(10)

                get_dbs = os.listdir('DBs\\')
                self.log("Backing up...")
                self.log("Zipping...")
                file_name = f'DBs\\DBs-{time.time()}-.7z'
                with py7zr.SevenZipFile(file_name, 'w') as file:
                    for each in get_dbs:
                        if each[-3::] == '.db':
                            file.writeall(f'DBs\\{each}')

                if os.path.isfile(file_name):
                    self.log("Backed up databases.")
                    self.log(f"Backup: {file_name}")
                else:
                    self.log("Something went wrong, try again later")

            else:
                self.log('There are no databases to backup.')

        finally:
            self.pbar.setValue(100)

    def load_data(self):

        if no_update:
            return

        #==================================================
        #                 QTabWidget 
        #==================================================
        self.main_tab.currentChanged.connect(lambda: self.assign_index(self.main_tab.currentIndex()))
        self.main_tab.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.main_tab.setCurrentIndex(MainApp._current_index)

        #==================================================
        #               iOS Tab 
        #==================================================
        self.ios_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ios_tree.customContextMenuRequested.connect(self.context_menu)
        self.ios_tree.setHeaderLabels(['#', 'Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ios_devices.db'):
            conn = sqlite3.connect("DBs\\ios_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            num = 1
            for dev_info in get_data.fetchall():
                if signed_only:
                    if relevant_only:
                        if int(dev_info[2].split('.')[0]) == relevant_version:
                            if str(dev_info[8]) == '1':
                                parent = QTreeWidgetItem(self.ios_tree, 
                                    [
                                        str(num),
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                    )

                                parent.setText(0, f"{num}")
                                num += 1
                    else:
                        if str(dev_info[8]) == '1':
                            parent = QTreeWidgetItem(self.ios_tree, 
                                [
                                    str(num),
                                    str(dev_info[0]),
                                    str(dev_info[1]),
                                    str(dev_info[2]),
                                    str(dev_info[3]),
                                    str(dev_info[4]), 
                                    naturalsize(int(str(dev_info[5]))),
                                    str(dev_info[6]),
                                    str(dev_info[7])]
                                )

                            parent.setText(0, f"{num}")
                            num += 1
                else:
                    parent = QTreeWidgetItem(self.ios_tree, 
                        [
                            str(num),
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

                    parent.setText(0, f"{num}")
                    num += 1

        #==================================================
        #               iPad Tab 
        #==================================================
        self.ipad_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ipad_tree.customContextMenuRequested.connect(self.context_menu)
        self.ipad_tree.setHeaderLabels(['#', 'Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ipad_devices.db'):
            conn = sqlite3.connect("DBs\\ipad_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            num = 1
            for dev_info in get_data.fetchall():
                if signed_only:
                    if relevant_only:
                        if int(dev_info[2].split('.')[0]) == relevant_version:
                            if str(dev_info[8]) == '1':
                                parent = QTreeWidgetItem(self.ipad_tree, 
                                    [
                                        str(num),
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                        )

                                parent.setText(0, f"{num}")
                                num += 1
                    else:
                        if str(dev_info[8]) == '1':
                            parent = QTreeWidgetItem(self.ipad_tree, 
                            [
                                str(num),
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                                )

                            parent.setText(0, f"{num}")
                            num += 1
                else:
                    parent = QTreeWidgetItem(self.ipad_tree, 
                        [
                            str(num),
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

                    parent.setText(0, f"{num}")
                    num += 1
        
        #==================================================
        #               iPod Tab 
        #==================================================
        self.ipod_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ipod_tree.customContextMenuRequested.connect(self.context_menu)
        self.ipod_tree.setHeaderLabels(['#', 'Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\ipod_devices.db'):
            conn = sqlite3.connect("DBs\\ipod_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            num = 1
            for dev_info in get_data.fetchall():
                if signed_only:
                    if relevant_only:
                        if int(dev_info[2].split('.')[0]) == relevant_version:
                            if str(dev_info[8]) == '1':
                                parent = QTreeWidgetItem(self.ipod_tree, 
                                    [
                                        str(num),
                                        str(dev_info[0]),
                                        str(dev_info[1]),
                                        str(dev_info[2]),
                                        str(dev_info[3]),
                                        str(dev_info[4]), 
                                        naturalsize(int(str(dev_info[5]))),
                                        str(dev_info[6]),
                                        str(dev_info[7])]
                                        )

                                parent.setText(0, f"{num}")
                                num += 1
                    else:
                        if str(dev_info[8]) == '1':
                            parent = QTreeWidgetItem(self.ipod_tree, 
                                [
                                    str(num),
                                    str(dev_info[0]),
                                    str(dev_info[1]),
                                    str(dev_info[2]),
                                    str(dev_info[3]),
                                    str(dev_info[4]), 
                                    naturalsize(int(str(dev_info[5]))),
                                    str(dev_info[6]),
                                    str(dev_info[7])]
                                    )

                            parent.setText(0, f"{num}")
                            num += 1
                else:
                    parent = QTreeWidgetItem(self.ipod_tree, 
                        [
                            str(num),
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

                    parent.setText(0, f"{num}")
                    num += 1

        #==================================================
        #               MacBook Tab
        #==================================================
        self.mac_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mac_tree.customContextMenuRequested.connect(self.context_menu)
        self.mac_tree.setHeaderLabels(['#', 'Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\macbook_devices.db'):
            conn = sqlite3.connect("DBs\\macbook_devices.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE FROM devices")
            num = 1
            for dev_info in get_data.fetchall():
                parent = QTreeWidgetItem(self.mac_tree, 
                    [
                        str(num),
                        str(dev_info[0]),
                        str(dev_info[1]),
                        str(dev_info[2]),
                        str(dev_info[3]),
                        str(dev_info[4]), 
                        naturalsize(int(str(dev_info[5]))),
                        str(dev_info[6]),
                        str(dev_info[7])]
                        )

                parent.setText(0, f"{num}")
                num += 1

        #==================================================
        #               iTunes Tab 
        #==================================================
        self.itunes_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.itunes_tree.customContextMenuRequested.connect(self.context_menu)
        self.itunes_tree.setHeaderLabels(['#', 'Platform', 'Version', 'Datefound', 'URL32', 'URL64', 'Date'])
        if os.path.isfile('DBs\\iTunes.db'):
            conn = sqlite3.connect("DBs\\iTunes.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT PLATFORM, _VERSION, DATEFOUND, URL32, URL64, RELEASEDATE FROM devices")
            num = 1

            for dev_info in get_data.fetchall():
                parent = QTreeWidgetItem(self.itunes_tree, 
                    [
                        str(num),
                        str(dev_info[0]),
                        str(dev_info[1]),
                        str(dev_info[2]),
                        str(dev_info[3]),
                        str(dev_info[4]), 
                        str(dev_info[5])
                    ])

                parent.setText(0, f"{num}")
                num += 1

        #==================================================
        #               Other Tab 
        #==================================================
        self.other_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.other_tree.customContextMenuRequested.connect(self.context_menu)
        self.other_tree.setHeaderLabels(['#', 'Device', 'Identifier', 'Version', 'Buildid', 'SHA1', 'Size', 'URL', 'Date'])
        if os.path.isfile('DBs\\other.db'):
            conn = sqlite3.connect("DBs\\other.db")
            cur = conn.cursor()
            get_data = cur.execute("SELECT DEVICE_NAME, IDENTIFIER, IOS_VERSION, BUILDID, SHA1SUM, FILESIZE, URL, RELEASEDATE, SIGNED FROM devices")
            num = 1

            for dev_info in get_data.fetchall():
                if signed_only:
                    if str(dev_info[8]) == '1':
                        parent = QTreeWidgetItem(self.other_tree, 
                            [
                                str(num),
                                str(dev_info[0]),
                                str(dev_info[1]),
                                str(dev_info[2]),
                                str(dev_info[3]),
                                str(dev_info[4]), 
                                naturalsize(int(str(dev_info[5]))),
                                str(dev_info[6]),
                                str(dev_info[7])]
                                )

                        parent.setText(0, f"{num}")
                        num += 1
                else:
                    parent = QTreeWidgetItem(self.other_tree, 
                        [
                            str(num),
                            str(dev_info[0]),
                            str(dev_info[1]),
                            str(dev_info[2]),
                            str(dev_info[3]),
                            str(dev_info[4]), 
                            naturalsize(int(str(dev_info[5]))),
                            str(dev_info[6]),
                            str(dev_info[7])]
                            )

                    parent.setText(0, f"{num}")
                    num += 1

        CheckDBS()

    def reset_data(self):
        self.ios_tree.clear()
        self.ipad_tree.clear()
        self.ipod_tree.clear()
        self.mac_tree.clear()
        self.itunes_tree.clear()
        self.other_tree.clear()
        self.load_data()

    def no_update(self, val):

        # If databases are up to date
        if val == 'db':
            MessagedBox("Database Update", 
                        "icons/updated.png", 
                        "icons/Checkmark_1.png", 
                        f"Already up to date.\nDB Version: {__dbversion__}")
            return

        # If iFirnware Toolkit is up to date
        MessagedBox("iFirmware Update", 
                    "icons/updated.png", 
                    "icons/Checkmark_1.png", 
                    f"Already up to date.\nVersion: {__version__}")

    def hash_file(self, val):
        if val[2]:
            sha1 = hashlib.sha1()
            with open(val[0], 'rb') as file:
                sha1.update(file.read())
            
            hashed = sha1.hexdigest()
            if hashed == val[1]:
                self.log(f"SHA1 matched: {val[1]}")
            else:
                self.log(f"SHA1 mismatched: {val[1]}")

    def update_available(self, val):

        MessagedBox("iFirmware Update",
                    "icons/updated.png",
                    "icons/Information.png",
                    f"A new version is available.\nCurrent: {__version__}\nNew: {val}")

    def send_to_log(self, val):
        self.log(val)

    def update_progressbar(self, val):
        self.pbar.setValue(val)

    def change_dir(self):
    
        global dest
        new_dest = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        if not new_dest:
            return

        dest = new_dest
        self.log(f"New path: {dest}")
        self.location_value.setText(dest)

    def delete_firmwares(self):
        if os.path.isdir(dest):
            self.log("Delete firmwares?")
            files = os.listdir(dest)
            if files:
                to_delete = []
                for file in files:
                    if file[-5:] == '.ipsw':
                        to_delete.append(os.path.join(dest, file))
                        continue 

                if to_delete:
                    for ipsw in to_delete:
                        self.log(f"Found {ipsw}")

                    show_firmwares = "\n".join([file for file in files if file[-5:] == '.ipsw'])

                    value = MessagedBox("Delete", 
                                "icons/updated.png",
                                "icons/Question.png",
                                f"Are you sure you want to delete the following firmwares?\n\n{show_firmwares}",
                                ok=False,
                                yes=True,
                                no=True)

                    if value == 0:
                        for del_ipsw in to_delete:
                            os.remove(del_ipsw)
                            
                        self.log('Finished deleting.')

                    else:
                        self.log("Aborted by user.")
            else:
                self.log('There are no firmwares to delete.')

        else:
            self.log("Destenaton folder does not exist.")

    def log(self, new_log):
        # Live Log UI

        if new_log is not None:
            self.logger.info(new_log)

        with open('logs.txt', 'r') as logs:
                log = logs.read()
                self.text_log = QTextBrowser(self.logs)
                global text_reset
                text_reset = self.text_log
                font = QtGui.QFont()
                font.setFamily("Segoe UI Semibold")
                font.setPointSize(10)
                self.text_log.setFont(font)
                self.text_log.setObjectName("text_log")
                self.gridLayout_2.addWidget(self.text_log, 0, 0, 1, 2)
                self.text_log.setText(log)
                self.text_log.moveCursor(QtGui.QTextCursor.End)

    def init_logger(self):
        # Reset the log file before initializing a new logger
        # clear_log() uses this method to flush the log file
        if os.path.isfile('logs.txt'):
            with open('logs.txt', 'w') as file:
                pass
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        output = logging.FileHandler('logs.txt')
        self.logger.addHandler(output)

    def reset_logger(self):
        # clear_log() will flush out the logger and initialize a new one
        text_reset.setText('')
        self.logger.handlers[0].close()
        self.logger.removeHandler(self.logger.handlers[0])
        self.init_logger()
        self.log(f'DB Version: {__dbversion__}\n=================\n')

    def enable_btns(self, val):
        if val:
            self.main_download.setDisabled(val)
            self.ipsw_delete.setDisabled(val)
            self.verify.setDisabled(val)
            self.location.setDisabled(val)
            self.db_delete.setDisabled(val)
            self.options.setDisabled(val)
            return 
        
        self.main_download.setEnabled(True)
        self.ipsw_delete.setEnabled(True)
        self.verify.setEnabled(True)
        self.location.setEnabled(True)
        self.db_delete.setEnabled(True)
        self.options.setEnabled(True)

    def assign_index(self, currentIndex):
        # This method is used to determine the current tab being used
        self.getIndex = currentIndex

        if currentIndex == 0:
            MainApp._current_index = 0
            self.getIndex = self.ios_tree

        elif currentIndex == 1:
            MainApp._current_index = 1
            self.getIndex = self.ipad_tree

        elif currentIndex == 2:
            MainApp._current_index = 2
            self.getIndex = self.ipod_tree

        elif currentIndex == 3:
            MainApp._current_index = 3
            self.getIndex = self.mac_tree

        elif currentIndex == 4:
            MainApp._current_index = 4
            self.getIndex = self.itunes_tree

        elif currentIndex == 5:
            MainApp._current_index = 5
            self.getIndex = self.other_tree

    def context_menu(self, point):
        # Main context menu for QTabWidget
        
        index = self.getIndex.indexAt(point)
        if not index.isValid():
            return

        item = self.getIndex.itemAt(point)

        if MainApp._current_index == 4:
            name_all = item.text(1) # Name and version of selected device
            version_all = item.text(2) # Version number for current selected device 
            url32 = item.text(4) # URL for a 32Bit iTunes 
            url64 = item.text(5) # URL for a 64Bit iTunes

            menu = QMenu()

            copy = menu.addAction("Copy All")
            copy.setIcon(QtGui.QIcon("icons/Copy.png"))
            
            copy_url = menu.addAction("Copy URL - 32Bit")
            copy_url.setIcon(QtGui.QIcon("icons/CopyURL.png"))                

            copy_url = menu.addAction("Copy URL - 64Bit")
            copy_url.setIcon(QtGui.QIcon("icons/CopyURL.png"))

            menu.addSeparator()
            delete = menu.addAction("Delete All")
            delete.setIcon(QtGui.QIcon("icons/Delete.png"))

        else:
            name = item.text(1) # Name of current selected device
            identifier = item.text(2) # Identifier ID for current selected device 
            version = item.text(3) # Version of current selected device 
            build = item.text(4) # Build ID of current selected device 
            hash_ = item.text(5) # SHA1 value for current selected device 
            url = item.text(7) # URL of current selected device 

            # Context menu actions
            menu = QMenu()
            download = menu.addAction("Download")
            download.setIcon(QtGui.QIcon("icons/Download.png"))

            copy = menu.addAction("Copy")
            copy.setIcon(QtGui.QIcon("icons/Copy.png"))

            copy_hash = menu.addAction("Copy hash")
            copy_hash.setIcon(QtGui.QIcon("icons/CopyHash.png"))

            copy_url = menu.addAction("Copy URL")
            copy_url.setIcon(QtGui.QIcon("icons/CopyURL.png"))

            menu.addSeparator()
            delete = menu.addAction("Delete")
            delete.setIcon(QtGui.QIcon("icons/Delete.png"))

        value = menu.exec_(self.getIndex.mapToGlobal(point))

        try:
            if value.text() == 'Copy':
                QApplication.clipboard().setText(f"{name} - {identifier} - {version} - {build}")

            elif value.text() == 'Copy hash':
                QApplication.clipboard().setText(hash_)

            elif value.text() == 'Copy All':
                QApplication.clipboard().setText(f"{name_all} - {version_all}")

            elif value.text() == 'Copy URL - 32Bit':
                QApplication.clipboard().setText(url32)

            elif value.text() == 'Copy URL - 64Bit':
                QApplication.clipboard().setText(url64)

            elif value.text() == 'Copy URL':
                QApplication.clipboard().setText(url)
            
            elif value.text() == 'Download':
                self.DownloadOneFirmware(name, url, hash_, build)
            
            elif value.text() == 'Delete':
                DeleteFromDB(url, MainApp._current_index, name)

            elif value.text() == 'Delete All':
                DeleteFromDB(url32, MainApp._current_index, name_all)

        except AttributeError:
            pass

class HashingThreaded(QThread):

    progress_update = pyqtSignal(int) # Update progress bar 
    send_to_log = pyqtSignal(str) # Log messages to main Live Log

    def __init__(self, parent=None, current_tab=int):
        QThread.__init__(self)
        self.current_tab = current_tab

    def run(self):
        if os.path.isdir(dest):
            files = os.listdir(dest)
            if files:
                to_hash = []
                for file in files:
                    if file[-5:] == '.ipsw': # Check that files found in the directory has the extension IPSW
                        to_hash.append(os.path.join(dest, file))

                if to_hash:
                    self.send_to_log.emit(f"Found {len(to_hash)} firmwares")
                    self.send_to_log.emit(f"Using SHA1 to hash...\n")

                    sha1 = hashlib.sha1()
                    num = 1
                    self.progress_update.emit(0)
                    for each_file in to_hash:
                        with open(each_file, 'rb') as file:
                            sha1.update(file.read())

                        each_file = each_file.split('\\')[-1::][0]
                        self.send_to_log.emit(f"{each_file}\nSHA1: {sha1.hexdigest()}")
                        self.progress_update.emit(num)
                        num = num + len(to_hash) % 100

                    self.progress_update.emit(100)
            else:
                self.send_to_log.emit('There are no firmwares to verify.')

class SoftwareUpdateThreaded(QThread):

    send_to_log = pyqtSignal(str)
    update_available = pyqtSignal(str)
    no_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        try:
            self.progress_update.emit(10)
            self.send_to_log.emit('Checking for update...')
            from_url = f"{Server}/verval.txt"
            get_update = requests.get(from_url)
            if get_update.ok:
                is_up_to_date = get_update.text.rstrip()
                if is_up_to_date == __version__:
                    self.no_update.emit('Already up to date.')
                    self.send_to_log.emit('Already up to date.')
                else:
                    self.update_available.emit(f'{is_up_to_date}')
                    self.send_to_log.emit('Update available.')
                    self.send_to_log.emit(f'New: {is_up_to_date}')

        except requests.exceptions.ConnectionError:
            self.send_to_log.emit('Server is offline.\nOr check your internet connection.')

        finally:
            self.progress_update.emit(100)

class DatabaseUpdateThreaded(QThread):

    send_to_log = pyqtSignal(str)
    no_update = pyqtSignal(str)
    refrush_ui = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(bool)

    def run(self):
        try:
            self.progress_update.emit(10)
            DB_Url = f"{Server}/updates/verval.txt"
            db_get = requests.get(DB_Url)

            if db_get.ok:
                with open('DBs\\config.cfg', 'w') as cfg:
                    cfg.write(str(db_get.json()))

                with open('DBs\\config.cfg', 'r') as cfg:
                    cfg = cfg.read()
                    cfg = cfg.replace("'", '"')
                    data = json.loads(cfg)

                up_to_date = data['date']
                relevant_only = int(data['relevant'])
                globals().update(relevant_version=relevant_only)

                # Check if remote version is up to date
                if up_to_date == __dbversion__:
                    self.no_update.emit('db')
                    self.send_to_log.emit('Already up to date.')
                    self.progress_update.emit(100)
                
                # If new version is available...
                else:
                    self.progress_update.emit(10)
                    self.send_to_log.emit(f'New version is available.\nCurrent: {__dbversion__}\nNew: {up_to_date}')
                    self.send_to_log.emit('Getting database file...')
                    
                    Url = f"{Server}/updates/DBs.7z"
                    get_data = requests.get(Url)

                    if get_data.ok:
                        self.progress_update.emit(20)
                        with open('DBs.7z', 'wb') as db_file:
                            db_file.write(get_data.content)

                        self.progress_update.emit(10)
                        self.send_to_log.emit('Finished downloading.')
                        self.send_to_log.emit('Checking SHA256...')

                        # Check sha1sum and verify files
                        sha256 = hashlib.sha256()
                        with open('DBs.7z', 'rb') as db_file:
                            sha256.update(db_file.read())

                        hashed = sha256.hexdigest()
                        self.send_to_log.emit(f"SHA256: {hashed}")
                        self.progress_update.emit(20)
                        
                        Url = f"{Server}/updates/sha256sum.txt"
                        get_data = requests.get(Url)
                        online_hash = 'Unavailable'

                        if get_data.ok:
                            self.progress_update.emit(10)
                            online_hash = get_data.text.rstrip().lower()

                        if hashed == online_hash or force_continue:
                            self.progress_update.emit(10)
                            if not force_continue:
                                self.send_to_log.emit('SHA256 matched.')
                            
                            self.send_to_log.emit('Extracting files...')
                            extract = py7zr.SevenZipFile('DBs.7z')
                            extract.extractall('DBs\\')
                            extract.close()
                            
                            self.send_to_log.emit('Cleaning...')
                            os.remove('DBs.7z')
                            self.send_to_log.emit('Refrushing UI... ')
                            self.refrush_ui.emit(True)
                            self.progress_update.emit(20)
                            globals().update(__dbversion__=up_to_date)

                        else:
                            self.send_to_log.emit('SHA1 mismatched.')
                            self.send_to_log.emit('Run update again to continue anyway.')
                            globals().update(force_continue=True)

                    else:
                        self.send_to_log.emit(f'Something went wrong...\nCODE:{get_data.status_code}')
                            
        except requests.exceptions.ConnectionError:
            self.send_to_log.emit('Server is offline.\nOr check your internet connection.')

        finally:
            self.progress_update.emit(100)
            self.finished.emit(True)

class ModelLookupThreaded(QThread):
    send_to_log = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    show_in_ui = pyqtSignal(list)

    def __init__(self, parent=None, model=''):
        QThread.__init__(self)
        self.model = model

    def run(self):
        if not self.model.strip():
            self.send_to_log.emit('Type in a model number to lookup')
        else:
            self.send_to_log.emit(f"Looking up {self.model}...")
            if self.model[:1].upper() == 'A':
                try:
                    device_lookup = f"https://api.ipsw.me/v4/model/{self.model}" # Lookup a device using its model number
                    get_info = requests.get(device_lookup)
                    if get_info.ok:
                        url = f"https://api.ipsw.me/v4/device/{get_info.json()['identifier']}"
                        get_data = requests.get(url)
                        name = get_data.json()['name']
                        identifier = get_data.json()['identifier']
                        boardconfig = get_data.json()['boardconfig']
                        platform = get_data.json()['platform']
                        cpid = get_data.json()['cpid']
                        self.show_in_ui.emit([name, identifier, boardconfig, platform, cpid])
                        self.send_to_log.emit(f'Results for {self.model}')
                        self.send_to_log.emit(f"Name: {name}\nIdentifier: {identifier}\nBoardconfig: {boardconfig}\nPlatform: {platform}\nCPID: {cpid}\n=================\n")
                    else:
                        self.send_to_log.emit('Server response: Unknown model number')
                except requests.exceptions.ConnectionError:
                        self.send_to_log.emit("Server unavailable, try again later.")
            else:
                self.send_to_log.emit('Invalid model number')

class DMButtonMngThreaded(QThread):

    enable_btns = pyqtSignal(bool)
    send_to_log = pyqtSignal(str)
    hash_file = pyqtSignal(list)

    def __init__(self, parent=None, dest_folder='', hash_value=''):
        QThread.__init__(self)
        self.dest_folder = dest_folder
        self.hash_value = hash_value

    def run(self):
        while dm.MainDownload.is_downloading:
            time.sleep(0.01)
            if not dm.MainDownload.is_downloading:
                self.send_to_log.emit("Downloader stopped successfully.")
                if hash_ipsw:
                    self.send_to_log.emit('Hashing...')
                    self.hash_file.emit([self.dest_folder, self.hash_value, True])

                self.enable_btns.emit(False)

class DeviceSearchThreaded(QThread):
    send_to_log = pyqtSignal(str)

    def __init__(self, parent=None, query='', current_tab=''):
        QThread.__init__(self)
        self.query = query
        self.current_tab = current_tab
    
    def run(self):
        self.send_to_log.emit(f"Searching for {self.query}...")
        to_download = dbs[self.current_tab]
        if os.path.isfile(to_download):
            try:
                conn = sqlite3.connect(to_download)
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM devices where DEVICE_NAME='{self.query}' OR IDENTIFIER='{self.query}' OR BUILDID='{self.query}'")
                data = cur.fetchall()
                if data:
                    for device in data:
                        name = device[0]
                        identifier = device[1]
                        version = device[3]
                        buildid = device[4]
                        date = device[8]
                        self.send_to_log.emit(f"Name: {name}\nIdentifier: {identifier}\nVersion: {version}\nBuildID: {buildid}\nRelease Date: {date}")
                        self.send_to_log.emit("----------------------")

            except sqlite3.OperationalError:
                pass

if __name__ == '__main__':

    # Check if hosts file exists
    if not os.path.exists('.hosts'):
        message_queue.append("Hosts file does not exist.\nCheck out online documentation for more information")
    elif os.path.exists('.hosts'):
        with open('.hosts', 'r') as file:
            data = json.loads(file.read().rstrip())
            Server = data['Server1']

    # Create database directory if it doesn't exist
    if not os.path.isdir('DBs'):
        os.mkdir('DBs')

    # Contains app version, and relevent version to determine what version of firmwares to show
    if os.path.isfile('DBs\\config.cfg'):
        with open('DBs\\config.cfg', 'r') as cfg:
            cfg = cfg.read()
            cfg = cfg.replace("'", '"')
            data = json.loads(cfg)
            __dbversion__ = data['date']
            relevant_version = int(data['relevant'])

    app = QApplication(sys.argv)
    window = MainApp()

    # Initialize the logger 
    window.init_logger()

    # Display firmwares if databases exist
    window.load_data()

    window.log(f'DB Version: {__dbversion__}\n=================\n')

    # Display error messages if there is any. Will be used more often un future versions.
    if message_queue:
        for each in message_queue:
            window.log(f"{each}")

    app.exec_()