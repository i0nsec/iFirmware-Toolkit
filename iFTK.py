import requests
import os, sys
import hashlib
import webbrowser
import time
import pathlib
import py7zr
import sqlite3
import json
import logging
from getpass import getuser
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

# dm.py - main downloader
# Still in beta and may crash occasionally
import dm

__version__ = 'v2.4-1107' # Application version
__dbversion__ = 'Not available' # Database version

Server = '' # Server address to download updates
message_queue = [] # Used to display messages prior to launching iFTK. Will be used more in future versions.
download_urls = {} # Used to pass URLs to the downloader module  
relevant_version = 15 # Specific firmware version to display
relevant_only = True # Always show relevant firmware files only
no_update = False # Do not update QTreeWidget, when checking for database update, if there is no updates available
hash_ipsw = False # Whether to hash after a download is finished 
signed_only = True # Show signed firmware files only
force_continue = False # Force updating by checking for update again even if SHA256 does not match
# Default location for database files
# Used to check if all required databases exist
dbs = [
    'DBs\\ios_devices.db',
    'DBs\\ipad_devices.db', 
    'DBs\\ipod_devices.db',
    'DBs\\macbook_devices.db',
    'DBs\\iTunes.db',
    'DBs\\other.db'
]

def check_integrity(state):
    # CheckBox for hashing a firmware

    if state == 2:
        globals().update(hash_ipsw=True)
    else:
        globals().update(hash_ipsw=False)

def check_databases():
    # Check if all required databases exists

    for db in dbs:
        if not os.path.isfile(db):
            MainApp.SIGNED_ONLY.setDisabled(True)
            MainApp.SHOW_RELEVANT.setDisabled(True)
        else:
            MainApp.SIGNED_ONLY.setDisabled(False)
            MainApp.SHOW_RELEVANT.setDisabled(False)

def show_singed_only(state):
    # Show signed only 

    if state == 2:
        globals().update(signed_only=True)
        window.reset_data()
        MainApp.SHOW_RELEVANT.setEnabled(True)
    else:
        globals().update(signed_only=False)
        window.reset_data()
        MainApp.SHOW_RELEVANT.setDisabled(True)

def show_relevant(state):
    # Show the most relevant versions only
    
    if state == 2:
        globals().update(relevant_only=True)
        window.reset_data()
    else:
        globals().update(relevant_only=False)
        window.reset_data()

def delete_from_database(URL, current_index, name):
    # Delete a firmware version from the selected database

    window.log(f"Deleting {name} from database...")

    # Display a message to the user making sure before deleting the firmware
    value = messaged_box(
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
                conn.close()
                window.log(f"Deleted {name} from database")
        finally:
            window.reset_data()

    elif value == 1:
        window.log("Aborted by user.")
    
def messaged_box(title, window_icon, icon, text, ok=True, copy=False, yes=False, no=False, abort=False, get=False):
    # This function will be used to create a custom message for the user 
    
    message = QMessageBox()

    # Title and icons
    message.setIconPixmap(QtGui.QPixmap(icon))
    message.setWindowIcon(QtGui.QIcon(window_icon))
    message.setWindowTitle(title)

    # Main message and styling
    message.setText(text)
    message.setStyleSheet("""
            background-color:#212121; 
            color: #fff; 
            padding: 15px;""")

    # Font for all
    font = QtGui.QFont()
    font.setPointSize(10)
    font.setFamily("Segoe UI Semibold")
    message.setFont(font)

    # All available buttons
    if ok:
        ok = message.addButton('Ok', message.ActionRole)
        ok.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        ok.setFont(font)
        ok.setStyleSheet("""
            QPushButton {
                background-color: #0C632A;
                border: 2px solid #0C632A;
    	        border-radius: 10px;
                color: #fff; 
                width: 50%;
                padding: 8px
                }

            QPushButton:hover {
                background-color: #084D20;
            }""")

    if get:
        get = message.addButton('Get', message.ActionRole)
        get.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        get.setFont(font)
        get.setStyleSheet("""
            QPushButton {
                background-color: #0C632A;
                border: 2px solid #0C632A;
    	        border-radius: 10px;
                color: #fff; 
                width: 50%;
                padding: 8px
                }
                
            QPushButton:hover {
                background-color: #084D20;
            }""")
    
    if copy:
        copy = message.addButton('Copy', message.ActionRole)
        copy.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        copy.setFont(font)
        copy.setStyleSheet("""
            QPushButton {
                background-color: #0C632A;
                border: 2px solid #0C632A;
    	        border-radius: 10px;
                color: #fff; 
                width: 50%;
                padding: 8px
                }
                
            QPushButton:hover {
                background-color: #084D20;
            }""")

    if yes:
        yes = message.addButton('Yes', message.ActionRole)
        yes.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        yes.setFont(font)
        yes.setStyleSheet("""
            QPushButton {
                background-color: #0C632A;
                border: 2px solid #0C632A;
    	        border-radius: 10px;
                color: #fff; 
                width: 50%;
                padding: 8px
                }
                
            QPushButton:hover {
                background-color: #084D20;
            }""")

    if no:
        no = message.addButton('No', message.ActionRole)
        no.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        no.setFont(font)
        no.setStyleSheet("""
            QPushButton {
                background-color: #0C632A;
                border: 2px solid #0C632A;
    	        border-radius: 10px;
                color: #fff; 
                width: 50%;
                padding: 8px
                }
                
            QPushButton:hover {
                background-color: #084D20;
            }""")

    if abort:
        abort = message.addButton('Abort', message.ActionRole)
        abort.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        abort.setFont(font)
        abort.setStyleSheet("QPushButton {background-color: #9a1717;border: 2px solid #0C632A;border-radius: 10px;color: #fff; width: 50%;padding: 8px}  QPushButton:hover {background-color: #801313;}")

    # Return value
    return message.exec_()

class ShowOptionsUI(QWidget):
    """
        Show options menu to restore a database backup
    """

    def __init__(self):
        super(ShowOptionsUI, self).__init__()
        uic.loadUi("_config.ui", self)

    def closeEvent(self, event):
        self.stop()

    def stop(self):
        MainApp.OPTIONS.setEnabled(True)

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
        self.ok.setStyleSheet("QPushButton {background-color: #777;border: none;color: #000;}QPushButton:disabled {border: none;border-radius: 10px;}QPushButton:hover {background-color: #084D20;}QToolTip { color: #fff; background-color: #000; border: none; }") 

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
                    self.ok.setStyleSheet("QPushButton {background-color: #0C632A;border: none;border-radius: 10px;color: #fff;}QPushButton:hover {background-color: #084D20;}QToolTip { color: #fff; background-color: #000; border: none; }") 
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
    SIGNED_ONLY = None
    CURRENT_INDEX = 0
    SHOW_RELEVANT = None
    OPTIONS = None
    THIS_PC = []
    TEXT_RESET = '' # Clear the Live Log
    # The default destination where firmware files will be downloaded
    # Not changing this will make iTunes pick up a firmware easily
    DEST: str = f"C:\\Users\\{os.getlogin()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates"

    def __init__(self):
        super(MainApp, self).__init__()
        uic.loadUi("_iFTK.ui", self)
        self.show()
        self.show_in_current_folder()

        # Change default destination button
        self.location.clicked.connect(self.change_dir)

        # Open default destination button
        self.open_location.clicked.connect(lambda: self.open_folder())

        # Delete all IPSWs in the current destination folder
        self.ipsw_delete.clicked.connect(self.delete_firmwares)

        # Hash IPSWs in the current destination folder
        self.verify.clicked.connect(self.hash_local_firmwares)

        # Clear logs button
        #self.clear_log.clicked.connect(self.reset_logger)

        # Check for database update button
        self._update.clicked.connect(self.database_update)

        # Delete all databases
        self.db_delete.clicked.connect(self.delete_datebases)

        # Backup databases
        # A backup database can be used to restore access
        self.backup.clicked.connect(self.backup_databases)

        # Search for a device in a database
        # ex: iPhone 12, A1287, etc
        self.device_search.textChanged.connect(lambda: self.device_lookup(self.device_search.text(), MainApp.CURRENT_INDEX))

        # Device model number lookup
        self.search_btn.clicked.connect(lambda: self.dev_lookup(self.search.text()))

        # CheckBoxes:
        # Hash IPSW after the download has finished
        self.check_integrity.clicked.connect(lambda: check_integrity(self.check_integrity.checkState()))
        # Show signed IPSWs only
        self.show_signed.clicked.connect(lambda: show_singed_only(self.show_signed.checkState()))
        MainApp.SIGNED_ONLY = self.show_signed
        # Show most relevant IPSWs versions only
        MainApp.SHOW_RELEVANT = self.show_relevant
        self.show_relevant.clicked.connect(lambda: show_relevant(self.show_relevant.checkState()))
        self.show_relevant.setChecked(True)

        # Show options menu
        self.op = ShowOptionsUI()
        self.options.clicked.connect(lambda: self.show_config())
        MainApp.OPTIONS = self.options
        self.main_tab.setCurrentIndex(1)

        # Check for iFTK update button
        self.get_update.clicked.connect(self.update_btn_clicked)

        # Set current iFTK version
        self.current_v.setText(__version__)

        # Main download button
        # Download all signed IPSWs - for iPhone only
        self.main_download.clicked.connect(lambda: self.download_all_signed(MainApp.CURRENT_INDEX))

        # Scan PC for IPSWs
        # It will check in the these places only:
        #   - var=MainApp.DEST (iTunes default destination),
        #   - C:\\,
        #   - C:\\Users\\[USER],
        #   - C:\\Users\\[USER]\\Downloads',
        #   - C:\\Users\\[USER]\\Desktop'
        #   - C:\\Users\\[USER]\\3uTools'
        self.scan_pc.clicked.connect(self.scanpc)

        # Context manager for This PC needs some more work
        # self.pc_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.pc_tree.customContextMenuRequested.connect(self.context_menu_this_pc)

        # Delete all IPSWs when button is clicked
        # Will only work when a scan has finished
        self.delete_all.clicked.connect(self.delete_all_ipsws)

        self.pbar.setStyleSheet("""
            QProgressBar {
                min-height: 12px;
                max-height: 12px;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: #0C632A;
            }
        """)

    def progress_bar_update(self):
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(0)

    def open_folder(self):
        try:
            os.startfile(MainApp.DEST)
        except FileNotFoundError:
            self.log("Directory does not exist.\niTunes is not installed, or it has not been initialized or used.")

    def show_config(self):
        # Show options menu

        self.options.setDisabled(True)
        self.op._show()

    def download_all_signed(self, current_tab):
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
                        dest_folder = f"{MainApp.DEST}/{file_name}" # Full path with file name
                        download_urls[index] = [name, url, sha1, buildid]
                        index += 1
            
            self.enable_btns(True)
            dm.MainDownload.urls = download_urls
            dm.MainDownload.dest_folder = MainApp.DEST
            self.go_dm = dm.MainDownload()
            self.go_dm.list_items()

            self.disable_btns = DMButtonMngThreaded(dest_folder=dest_folder, hash_value=sha1)
            self.disable_btns.start()
            self.disable_btns.enable_btns.connect(self.enable_btns)
            self.disable_btns.send_to_log.connect(self.send_to_log)
            self.disable_btns.hash_file.connect(self.hash_file)

        else:
            self.log('Could not find any databases.\nCheck for update first')

    def download_one_firmware(self, dev_name, url, hash_value, buildid):
        # Single firmware download. Only triggered from context menu 
        
        # If the default directory for iTunes does not exist, create it
        if not os.path.exists(MainApp.DEST):
            os.makedirs(MainApp.DEST)

        self.log(f"Downloading: {dev_name} - {buildid}\n{hash_value}\n")

        value = messaged_box("Download Firmware", 
                            "icons/updated.png",
                            "icons/Question.png",
                            f"Start downloading firmware for {dev_name}?",
                            ok=False,
                            yes=True,
                            no=True,
                            abort=False)

        if value == 0:
            file_name = url.split('/')[-1:][0] # Get file name from URL
            dest_folder = f"{MainApp.DEST}/{file_name}" # Full path with file name

            if os.path.isfile(dest_folder):
                self.log('Firmware already exists!')
                value = messaged_box("Error", 
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
        # Connect to server and check for database update

        # Exit if hosts file does not exist
        if not Server:
            self.log("No hosts file found.")
            return

        self.log("Checking for database update...")

        value = messaged_box(
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
            self.db_thread.no_update.connect(self.no_update)
            self.db_thread.send_to_log.connect(self.send_to_log)
            self.db_thread.progress_update.connect(self.progress_bar_update)
            self.db_thread.refrush_ui.connect(self.reset_data)
            self.db_thread.is_ready.connect(lambda: self.pbar.setMaximum(100))

        else:
            self.log('Aborted by user.')

    def device_lookup(self, query, current_tab):
        # Lookup a device in the database

        self.worker_search = DeviceSearchThreaded(query=query, current_tab=current_tab)
        self.worker_search.start()
        self.worker_search.send_to_log.connect(self.send_to_log)
        # Reset live log when displaying new results
        self.reset_logger()

    def dev_lookup(self, model):
        self.search.clear() # Reset user input
        self.worker_lookup = ModelLookupThreaded(model=model)
        self.worker_lookup.start()
        self.worker_lookup.progress_update.connect(self.update_progressbar)
        self.worker_lookup.send_to_log.connect(self.send_to_log)
        self.worker_lookup.show_in_ui.connect(self.show_in_ui)

    def hash_local_firmwares(self):
        self.hash_firmware = HashingThreaded(current_tab=MainApp.CURRENT_INDEX)
        self.hash_firmware.start()
        self.hash_firmware.send_to_log.connect(self.send_to_log)
        self.hash_firmware.progress_update.connect(self.update_progressbar)

    def update_btn_clicked(self):
        # If hosts file does not exist, do not continue
        if not Server:
            self.log("No hosts file found.")
            return 

        self.up_thread = SoftwareUpdateThreaded()
        self.up_thread.start()
        self.up_thread.progress_update.connect(self.progress_bar_update)
        self.up_thread.send_to_log.connect(self.send_to_log)
        self.up_thread.no_update.connect(self.no_update)
        self.up_thread.update_available.connect(self.update_available)
        self.up_thread.is_ready.connect(lambda: self.pbar.setMaximum(100))

    def scanpc(self):
        self.this_pc_total = 0
        self.scan = ScanPC()
        self.scan.start()
        self.scan.send_to_log.connect(self.send_to_log)
        self.scan.finished.connect(self.update_this_pc)
        self.scan.update_progress.connect(self.update_progressbar)

    def update_this_pc(self):
        for get_size in MainApp.THIS_PC:
            self.this_pc_total += os.path.getsize(get_size)

        self.found_label.setText(f"Found: {len(MainApp.THIS_PC)}")
        self.total_label.setText(f"Total: {naturalsize(self.this_pc_total)}")

        self.pc_tree.clear()
        for other_files in MainApp.THIS_PC:
            QTreeWidgetItem(self.pc_tree, 
                            [str(other_files), naturalsize(os.path.getsize(os.path.join(MainApp.DEST, str(other_files))))])

    def show_in_current_folder(self):
        get_files = os.listdir(MainApp.DEST)

        self.pc_tree.clear()
        for files in get_files:
            QTreeWidgetItem(self.pc_tree,
                                [files, naturalsize(os.path.getsize(os.path.join(MainApp.DEST, files)))])

    def delete_all_ipsws(self):
        get_locals = os.listdir(MainApp.DEST)
        if MainApp.THIS_PC or get_locals:
            value = messaged_box(
                            "Delete All", 
                            "icons/Question.png", 
                            "icons/Question.png", 
                            f"Are you sure you want to delete all?\n{' '.join([x for x in get_locals])}\n{' '.join([str(x) for x in MainApp.THIS_PC])}",
                            yes=True,
                            no=True,
                            ok=False)
            if value == 0:
                try:
                    if get_locals:
                        for file in get_locals:
                            os.remove(os.path.join(MainApp.DEST, file))
                
                    if MainApp.THIS_PC:
                        for file in MainApp.THIS_PC:
                            os.remove(file)

                except FileNotFoundError:
                    pass
                        
                self.scanpc()
        else:
            value = messaged_box(
                                "Delete All",
                                "icons/Info.png",
                                "icons/Info.png",
                                "Could not find any firmware to delete.",
                                ok=True)

    def show_in_ui(self, val):
        data = f"Name: {val[0]}\nIdentifier: {val[1]}\nBoardconfig: {val[2]}\nPlatform: {val[3]}\nCPID: {val[4]}\n"
        value = messaged_box("Search results",
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
        if to_delete:
            for db in to_delete:
                self.log(f"Found {db}")

            self.log('Delete databases?')
            show_dbs = "\n".join([db for db in to_delete])

            value = messaged_box("Delete", 
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

                self.reset_data()
            else:
                self.log('Aborted by user.')

        else:
            self.log('There are no databases to delete.')

    def backup_databases(self):
        # backup all databases to a zip file

        to_backup = [db for db in dbs if os.path.isfile(db)]
        if to_backup:
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

    def load_data(self):
        # Main method for displaying the IPSWs information

        # Do not update QTreeWidget, when checking for database update, if there is no updates available
        if no_update:
            return

        #==================================================
        #                 QTabWidget 
        #==================================================
        self.main_tab.currentChanged.connect(lambda: self.assign_index(self.main_tab.currentIndex()))
        self.main_tab.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.main_tab.setCurrentIndex(MainApp.CURRENT_INDEX)

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

        check_databases()

    def reset_data(self):
        self.ios_tree.clear()
        self.ipad_tree.clear()
        self.ipod_tree.clear()
        self.mac_tree.clear()
        self.itunes_tree.clear()
        self.other_tree.clear()
        self.load_data()

    def no_update(self, val):
        if val == 'db':
            messaged_box("Database Update", 
                        "icons/updated.png", 
                        "icons/Checkmark_1.png", 
                        f"Already up to date.\nDB Version: {__dbversion__}")
            return

        # If iFirnware Toolkit is up to date
        messaged_box("iFirmware Update", 
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
        value = messaged_box("iFirmware Update",
                    "icons/updated.png",
                    "icons/Information.png",
                    f"A new version is available.\nCurrent: {__version__}\nNew: {val}", get=True)
        if value == 1:
            url = "https://github.com/i0nsec/iFirmware-Toolkit/releases"
            self.log(f"Opening your default browser to download the new version\n{url}")
            webbrowser.open(url)

    def send_to_log(self, val):
        self.log(val)

    def update_progressbar(self, val):
        self.pbar.setValue(val)

    def change_dir(self):
        new_dest = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        if not new_dest:
            return

        MainApp.DEST = new_dest
        self.log(f"New path: {MainApp.DEST}")
        self.location_value.setText(MainApp.DEST)

    def delete_firmwares(self):
        if os.path.isdir(MainApp.DEST):
            self.log("Delete firmware files?")
            files = os.listdir(MainApp.DEST)

            if files:
                to_delete = []

                for file in files:
                    if file[-5:] == '.ipsw':
                        to_delete.append(os.path.join(MainApp.DEST, file))
                        continue 

                if to_delete:
                    for ipsw in to_delete:
                        self.log(f"Found {ipsw}")

                    show_ipsws = "\n".join([file for file in files if file[-5:] == '.ipsw'])

                    value = messaged_box("Delete", 
                                "icons/updated.png",
                                "icons/Question.png",
                                f"Are you sure you want to delete the following IPSWs?\n\n{show_ipsws}",
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
                self.log('There are no firmware files to delete.')

        else:
            self.log("Destination folder does not exist.")

    def log(self, new_log):
        if new_log is not None:
            self.logger.info(new_log)

        with open('logs.txt', 'r') as logs:
            log = logs.read()
            self.text_log = QTextBrowser(self.logs)
            MainApp.TEXT_RESET = self.text_log
            font = QtGui.QFont()
            font.setFamily("Segoe UI Semibold")
            font.setPointSize(11)
            font.setBold(True)
            self.text_log.setFont(font)
            self.text_log.setObjectName("text_log")
            self.gridLayout_4.addWidget(self.text_log, 0, 0, 1, 2)
            self.text_log.setText(log)
            self.text_log.moveCursor(QtGui.QTextCursor.End)
            self.text_log.setStyleSheet("background-color: rgb(52, 52, 52);")

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
        MainApp.TEXT_RESET.setText('')
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
        self.getIndex = currentIndex

        if currentIndex == 0:
            MainApp.CURRENT_INDEX = 0
            self.getIndex = self.ios_tree

        elif currentIndex == 1:
            MainApp.CURRENT_INDEX = 1
            self.getIndex = self.ipad_tree

        elif currentIndex == 2:
            MainApp.CURRENT_INDEX = 2
            self.getIndex = self.ipod_tree

        elif currentIndex == 3:
            MainApp.CURRENT_INDEX = 3
            self.getIndex = self.mac_tree

        elif currentIndex == 4:
            MainApp.CURRENT_INDEX = 4
            self.getIndex = self.itunes_tree

        elif currentIndex == 5:
            MainApp.CURRENT_INDEX = 5
            self.getIndex = self.other_tree

    def context_menu(self, point):

        index = self.getIndex.indexAt(point)
        if not index.isValid():
            return

        item = self.getIndex.itemAt(point)

        if MainApp.CURRENT_INDEX == 4:
            name_all = item.text(1) # Name and version of selected device
            version_all = item.text(2) # Version number for current selected device 
            url32 = item.text(4) # URL for a 32Bit iTunes 
            url64 = item.text(5) # URL for a 64Bit iTunes

            menu = QMenu()
            menu.setStyleSheet("""
            QMenu {
                background-color: #222;
                margin: 4px;
                color: #fff;
            }

            QMenu::item:selected {
                background: rgba(100, 100, 100, 150);
            }

            QMenu::icon:checked { /* appearance of a 'checked' icon */
                background: gray;
                border: 1px inset gray;
                position: absolute;
                top: 1px;
                right: 1px;
                bottom: 1px;
                left: 1px;
            }

            QMenu::separator {
                height: 2px;
                background: lightblue;
                margin-left: 10px;
                margin-right: 5px;
            }

            QMenu::indicator {
                width: 13px;
                height: 13px;
            }
            """)

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

            menu = QMenu()
            menu.setStyleSheet("""
            QMenu {
                background-color: #222;
                margin: 4px;
                color: #fff;
            }

            QMenu::item:selected {
                background: rgba(100, 100, 100, 150);
            }

            QMenu::icon:checked { /* appearance of a 'checked' icon */
                background: gray;
                border: 1px inset gray;
                position: absolute;
                top: 1px;
                right: 1px;
                bottom: 1px;
                left: 1px;
            }

            QMenu::separator {
                height: 2px;
                background: lightblue;
                margin-left: 10px;
                margin-right: 5px;
            }

            QMenu::indicator {
                width: 13px;
                height: 13px;
            }
            """)
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
                self.download_one_firmware(name, url, hash_, build)
            
            elif value.text() == 'Delete':
                delete_from_database(url, MainApp.CURRENT_INDEX, name)

            elif value.text() == 'Delete All':
                delete_from_database(url32, MainApp.CURRENT_INDEX, name_all)

        except AttributeError:
            pass

class HashingThreaded(QThread):
    progress_update = pyqtSignal(int)
    send_to_log = pyqtSignal(str)

    def __init__(self, parent=None, current_tab=int):
        QThread.__init__(self)
        self.current_tab = current_tab

    def run(self):
        if os.path.isdir(MainApp.DEST):
            files = os.listdir(MainApp.DEST)
            if files:
                to_hash = []
                for file in files:
                    if file[-5:] == '.ipsw': # Check that files found in the directory has the extension IPSW
                        to_hash.append(os.path.join(MainApp.DEST, file))

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
                self.send_to_log.emit('There are no firmware files in the current directory to verify.')

class SoftwareUpdateThreaded(QThread):
    send_to_log = pyqtSignal(str)
    update_available = pyqtSignal(str)
    no_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    is_ready = pyqtSignal(bool)

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        try:
            self.progress_update.emit(1)
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
            self.is_ready.emit(True)

class DatabaseUpdateThreaded(QThread):
    send_to_log = pyqtSignal(str)
    no_update = pyqtSignal(str)
    refrush_ui = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    is_ready = pyqtSignal(bool)

    def run(self):
        try:
            self.progress_update.emit(1)
            db_url = f"{Server}/updates/verval.txt"
            db_get = requests.get(db_url)

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
                    self.is_ready.emit(True)
                
                # If new version is available...
                else:
                    self.send_to_log.emit(f'New version is available.\nCurrent: {__dbversion__}\nNew: {up_to_date}')
                    self.send_to_log.emit('Getting database file...')
                    
                    Url = f"{Server}/updates/DBs.7z"
                    get_data = requests.get(Url)

                    if get_data.ok:
                        with open('DBs.7z', 'wb') as db_file:
                            db_file.write(get_data.content)

                        self.send_to_log.emit('Finished downloading.')
                        self.send_to_log.emit('Checking SHA256...')

                        # Check sha1sum and verify files
                        sha256 = hashlib.sha256()
                        with open('DBs.7z', 'rb') as db_file:
                            sha256.update(db_file.read())

                        hashed = sha256.hexdigest()
                        self.send_to_log.emit(f"SHA256: {hashed}")
                        
                        Url = f"{Server}/updates/sha256sum.txt"
                        get_data = requests.get(Url)
                        online_hash = 'Unavailable'

                        if get_data.ok:
                            online_hash = get_data.text.rstrip().lower()

                        if hashed == online_hash or force_continue:
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
            self.is_ready.emit(True)

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

class ScanPC(QThread):
    update_count = pyqtSignal(int)
    send_to_log = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    common_dirs = [MainApp.DEST,
                    'C:\\',
                   f'C:\\Users\\{getuser()}',
                   f'C:\\3uTools\\Firmware',
                   f'C:\\Users\\{getuser()}\\Downloads',
                   f'C:\\Users\\{getuser()}\\Desktop',
                   f'C:\\Users\\{getuser()}\\AppData\\Roaming\\Apple Computer\\iTunes\\iPhone Software Updates']

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        self.send_to_log.emit("Scan initiated")
        MainApp.THIS_PC.clear()
        
        self.update_progress.emit(10)

        for directory in self.common_dirs:
            for path_to_file in pathlib.Path(directory).glob('*.ipsw'):
                if path_to_file:
                    MainApp.THIS_PC.append(path_to_file)
                    self.update_progress.emit(1)
        
        self.update_progress.emit(100)
        self.send_to_log.emit(f"Finished scanning")
        self.send_to_log.emit(f"-----------------")
                
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

    # Initialize logger 
    window.init_logger()

    # Display firmware files if database exist
    window.load_data()
    window.log(f'Database Version: {__dbversion__}\n---------------------------------\n')

    # Display error messages if there is any. Will be used more in future versions
    if message_queue:
        for each in message_queue:
            window.log(f"{each}")

    app.exec_()