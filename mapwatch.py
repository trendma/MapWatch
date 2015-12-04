import sys
import os
import re
import copy
import json
#import msvcrt
import sqlite3
import time
import datetime
import pyperclip
import pywinauto
import configparser
import webbrowser
import win32gui
import win32con

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, Qt, QThread
from PyQt5.QtWidgets import QFileDialog
from window import Ui_MainWindow
from confirm import Ui_Confirm
from preferences import Ui_Preferences

# TODOS:
### Create custom icons
### Create more HTML statistic files
### Sacrifice Fragments
### Atziri Maps
### 

class Map():
    TimeAdded = 0
    Name = 1
    Tier = 2
    IQ = 3
    BonusIQ = 4
    IR = 5
    PackSize = 6
    Rarity = 7
    Mod1 = 8
    Mod2 = 9
    Mod3 = 10
    Mod4 = 11
    Mod5 = 12
    Mod6 = 13
    Mod7 = 14
    Mod8 = 15
    Mod9 = 16 # Zana Mod

class Maps():
    Dropped = 0
    Ran = 1

class ZanaMod():
    Name = 0
    Cost = 1
    Level = 2
    IQ = 3
    Desc = 4

class MapWatchWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        # General Settings
        self.version = '0.2'
        self.appTitle = 'Map Watch (v'+self.version+')'
        self.setWindowIcon(QtGui.QIcon(r'images\\icon.ico'))
        self.firstClose = 1
        self.zana_mods = [ # TODO: maybe load from outside source? settings.ini?
            ['None', 'Free', 0, 0, ''],
            ['Item Quantity', 'Free', 1, 0, '+1% Quantity Per Master Level'],
            ['Rampage', '4x Chaos Orbs', 2, 0, 'Slaying enemies quickly grants Rampage bonuses'],
            ['Bloodlines', '4x Chaos Orb', 2, 15, 'Magic Monster Packs each have a Bloodline Mod'],
            ['Anarchy', '8x Chaos Orb', 3, 16, 'Area is inhabited by 4 additional Rogue Exiles'],
            ['Invasion', '8x Chaos Orb', 3, 16, 'Area is inhabited by 3 additional Invasion Bosses'],
            ['Domination', '10x Chaos Orb', 4, 0, 'Area Contains 5 Extra Shrines'],
            ['Onslaught', '8x Chaos Orb', 4, 30, '40% Increased Monster Cast & Attack Speed'],
            ['Torment', '8x Chaos Orb', 5, 12, 'Area spawns 3 extra Tormented Spirits (Stacks with any that naturally spawned)'],
            ['Beyond', '12x Chaos Orb', 5, 8, 'Slaying enemies close together can attract monsters from Beyond this realm'],
            ['Ambush', '12x Chaos Orb', 6, 0, 'Area contains 4 extra Strongboxes'],
            ['Nemesis', '1x Exalted Orb', 7, 0, 'One Rare Per Pack, Rare Monsters Each Have A Nemesis Mod'],
            ['Tempest', '3x Exalted Orb', 8, 16, 'Powerful Tempests can affect both Monsters and You'],
            ['Warbands', '3x Exalted Orb', 8, 16, 'Area is inhabited by 2 additional Warbands']
        ]
        # I don't know how to include some of these within the current map tier system, 0,-1,-2 ?
        # How would they compare in statistics? Not sure about this anymore.
        # self.fragments = [
        #     {Map.TimeAdded: 0, Map.Name: 'Sacrifice at Dusk', Map.Tier: 66, Map.Rarity: 'Unique'},
        #     ['Sacrifice at Dawn', 67],
        #     ['Sacrifice at Noon', 68],
        #     ['Sacrifice at Midnight', 69],
        #     ['Mortal Grief', 70],
        #     ['Mortal Rage', 71],
        #     ['Mortal Ignorance', 72],
        #     ['Mortal Hope', 73]
        # ]
        self.atziri_maps = [ #TODO
            {
                Map.TimeAdded: 0,
                Map.Name: 'The Apex of Sacrifice',
                Map.Tier: 3,
                Map.IQ: 0,
                Map.BonusIQ: 0,
                Map.IR: 0,
                Map.PackSize: 0,
                Map.Rarity: 'Unique'
            },
            {
                Map.TimeAdded: 0,
                Map.Name: 'The Alluring Abyss',
                Map.Tier: 13,
                Map.IQ: 200,
                Map.BonusIQ: 0,
                Map.IR: 0,
                Map.PackSize: 0,
                Map.Rarity: 'Unique',
                Map.Mod1: '100% Monsters Damage',
                Map.Mod2: '100% Monsters Life'
            }
        ]
        #self.settings = readSettings()
        # System Tray Icon
        self.sysTrayIcon = QtWidgets.QSystemTrayIcon()
        self.sysTrayIcon.setIcon(QtGui.QIcon(r'images\\icon.ico'))
        self.sysTrayIcon.show()
        self.sysTrayIcon.activated.connect(self.restore)
        # System Tray Context Menu
        menu = QtWidgets.QMenu(parent)
        icon = QtGui.QIcon(r'images\\icon.ico')
        restoreAction = QtWidgets.QAction(icon, '&Show Map Watch', self)
        restoreAction.triggered.connect(self.popup)
        menu.addAction(restoreAction)
        icon = QtGui.QIcon('')
        exitAction = QtWidgets.QAction(icon, '&Exit', self)
        exitAction.triggered.connect(self.closeApplication)
        menu.addAction(exitAction)
        self.sysTrayIcon.setContextMenu(menu)
        # This will do the Map Watching in a different thread
        self.thread = MapWatcher()
        self.thread.runLoop()
        self.thread.trigger.connect(self.updateUiMapSelected)  # Triggered when new map found
        # Configure UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFixedSize(471, 413)
        self.setWindowTitle(self.appTitle)
        self.ui_confirm = ConfirmDialog(self)
        self.ui_prefs = Preferences(self)
        self.setPrefs()
        self.addZanaMods()
        if not int(self.settings['AlwaysOnTop']):
            self.setWindowFlags(Qt.CustomizeWindowHint|Qt.WindowCloseButtonHint|Qt.X11BypassWindowManagerHint)
        else:
            self.setWindowFlags(Qt.CustomizeWindowHint|Qt.WindowCloseButtonHint|Qt.WindowStaysOnTopHint|Qt.X11BypassWindowManagerHint)  
        # Button Actions
        self.ui.ms_add_map.clicked.connect(self.addMap)
        self.ui.ms_remove_map.clicked.connect(self.removeMap)
        self.ui.mr_clear_map.clicked.connect(self.clearMap)
        self.ui.mr_run_map.clicked.connect(self.runMap)
        self.ui.mr_add_zana_mod.currentIndexChanged.connect(self.changeZanaMod)
        self.ui.mr_add_bonus_iq.valueChanged.connect(self.changeBonusIQ)
        # Menu Actions
        self.ui.menu_create_new_db.triggered.connect(lambda: self.setDBFile(True))
        self.ui.menu_load_db.triggered.connect(self.setDBFile)
        self.ui.menu_open_stats.triggered.connect(self.openStatFile)
        self.ui.menu_exit_app.triggered.connect(self.closeApplication)
        self.ui.menu_ms_add_map.triggered.connect(self.addMap)
        self.ui.menu_ms_add_unlinked_map.triggered.connect(lambda: self.addMap(True))
        self.ui.menu_ms_remove_map.triggered.connect(self.removeMap)
        self.ui.menu_mr_clear_map.triggered.connect(self.clearMap)
        self.ui.menu_mr_run_map.triggered.connect(self.runMap)
        self.ui.menu_preferences.triggered.connect(self.getPrefs)
        self.ui.menu_about.triggered.connect(self.about)
        # Keyboard Shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("A"), self, self.addMap)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+U"), self, lambda: self.addMap(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), self, self.removeMap)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+X"), self, self.clearMap)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+R"), self, self.runMap)
        QtWidgets.QShortcut(QtGui.QKeySequence("Z"), self, lambda: self.giveFocus('ZanaMod'))
        QtWidgets.QShortcut(QtGui.QKeySequence("Q"), self, lambda: self.giveFocus('BonusIQ'))
        QtWidgets.QShortcut(QtGui.QKeySequence("F1"), self, lambda: self.setDBFile(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("F2"), self, self.setDBFile)
        QtWidgets.QShortcut(QtGui.QKeySequence("F3"), self, self.openStatFile)
        QtWidgets.QShortcut(QtGui.QKeySequence("F4"), self, self.getPrefs)
        QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self, self.about)
        QtWidgets.QShortcut(QtGui.QKeySequence("F12"), self, self.closeApplication)
        # Setup Map Database
        self.map_data = None
        self.mapDB = MapDatabase(self)
        if int(self.settings['LoadLastOpenedDB']):
            if os.path.exists(self.settings['LastOpenedDB']):
                self.mapDB.setDBFile(self.settings['LastOpenedDB'])
                self.mapDB.setupDB('Checking DB Structure', True)
            else:
                self.mapDB.setupDB(self.settings['LastOpenedDB'])
        else:
            self.buttonAccess(False)
        self.updateWindowTitle()
        #Windows hwnd
        self._handle = None
        self.window = None

    def _window_enum_callback(self, hwnd, wildcard):
        '''Pass to win32gui.EnumWindows() to check all the opened windows'''
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
            self._handle = hwnd
            print('hwnd: '+str(self._handle))
        #print(str(win32gui.GetWindowText(hwnd)))

    def restore(self, action):
        if action == self.sysTrayIcon.DoubleClick:
            self.popup()

    def popup(self):
        self.showNormal()
        #self.show()
        self.activateWindow()
        if self._handle:
            win32gui.ShowWindow(self._handle, win32con.SW_RESTORE)
            win32gui.BringWindowToTop(self._handle)
            win32gui.SetWindowPos(self._handle,win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)  
            win32gui.SetWindowPos(self._handle,win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)  
            win32gui.SetWindowPos(self._handle,win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_SHOWWINDOW + win32con.SWP_NOMOVE + win32con.SWP_NOSIZE)
            self.window.SetFocus() #STEAL FOCUS! HAHA, fuck you Microsoft

    def giveFocus(self, widget):
        if widget is 'ZanaMod':
            self.ui.mr_add_zana_mod.setFocus(Qt.ShortcutFocusReason)
        elif widget is 'BonusIQ':
            self.ui.mr_add_bonus_iq.setFocus(Qt.ShortcutFocusReason)

    def updateUiMapSelected(self, map_data):
        print('UI Updated')
        self.popup()
        self.map_data = map_data
        # Clear those items that may not be updated with new map
        self.ui.ms_iq.setText('0%')
        self.ui.ms_ir.setText('0%')
        self.ui.ms_pack_size.setText('0%')
        self.ui.ms_mods.setText('None')
        # Get each piece of map info and update UI lables, etc
        if Map.TimeAdded in map_data:
            h = '%H'
            ms = ''
            p = ''
            if int(self.settings['ClockHour12']):
                h = '%I'
                p = ' %p'
            if int(self.settings['ShowMilliseconds']):
                ms = '.%f'
            time_added = datetime.datetime.fromtimestamp(map_data[Map.TimeAdded]).strftime(h+':%M:%S'+ms+p)
            self.ui.ms_time_stamp.setText(time_added)
        if Map.Name in map_data:
            self.ui.ms_name.setText(map_data[Map.Name])
        if Map.Tier in map_data:
            level = int(map_data[Map.Tier]) + 67
            self.ui.ms_tier.setText(map_data[Map.Tier] + '  (' + str(level) + ')')
        if Map.IQ in map_data:
            self.ui.ms_iq.setText(map_data[Map.IQ]+'%')
        if Map.IR in map_data:
            self.ui.ms_ir.setText(map_data[Map.IR]+'%')
        if Map.PackSize in map_data:
            self.ui.ms_pack_size.setText(map_data[Map.PackSize]+'%')
        if Map.Rarity in map_data:
            rarity = map_data[Map.Rarity]
            self.ui.ms_rarity.setText(rarity)
            if rarity == 'Rare':
                self.ui.ms_name.setStyleSheet("color: rgb(170, 170, 0);")
            elif rarity == 'Magic':
                self.ui.ms_name.setStyleSheet("color: rgb(0, 85, 255);")
            elif rarity == 'Unique':
                self.ui.ms_name.setStyleSheet("color: rgb(170, 85, 0);")
            else:
                self.ui.ms_name.setStyleSheet("color: rgb(0, 0, 0);")
        if Map.Mod1 in map_data:
            all_mods = map_data[Map.Mod1]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod2 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod2]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod3 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod3]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod4 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod4]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod5 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod5]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod6 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod6]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod7 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod7]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod8 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod8]
            self.ui.ms_mods.setText(all_mods)
        if Map.Mod9 in map_data:
            all_mods = all_mods + '\r\n' + map_data[Map.Mod9]
            self.ui.ms_mods.setText(all_mods)

    def updateUiMapRunning(self, clear=False):
        print('UI Updated')
        if clear:
            self.ui.mr_name.setText('None')
            self.ui.mr_tier.setText('0')
            self.ui.mr_iq.setText('0%')
            self.ui.mr_bonus_iq.setText('')
            self.ui.mr_ir.setText('0%')
            self.ui.mr_pack_size.setText('0%')
            self.ui.mr_rarity.setText('')
            self.ui.mr_mods.setText('')
            self.ui.mr_name.setStyleSheet("color: rgb(0, 0, 0);")
        else:
            self.ui.mr_name.setText(self.ui.ms_name.text())
            self.ui.mr_tier.setText(self.ui.ms_tier.text())
            self.ui.mr_iq.setText(self.ui.ms_iq.text())
            self.ui.mr_ir.setText(self.ui.ms_ir.text())
            self.ui.mr_pack_size.setText(self.ui.ms_pack_size.text())
            self.ui.mr_rarity.setText(self.ui.ms_rarity.text())
            self.ui.mr_mods.setText(self.ui.ms_mods.toPlainText())
            self.map_mod_text = self.ui.ms_mods.toHtml() # orginal copy for bonus IQ add/remove
            rarity = self.ui.ms_rarity.text()
            if rarity == 'Rare':
                self.ui.mr_name.setStyleSheet("color: rgb(170, 170, 0);")
            elif rarity == 'Magic':
                self.ui.mr_name.setStyleSheet("color: rgb(0, 85, 255);")
            elif rarity == 'Unique':
                self.ui.mr_name.setStyleSheet("color: rgb(170, 85, 0);")
            else:
                self.ui.mr_name.setStyleSheet("color: rgb(0, 0, 0);")

    def updateUiMapRunningBonuses(self):
        print('UI Updated')
        if Map.BonusIQ in self.mapDB.map_running and self.mapDB.map_running[Map.BonusIQ] != 0:
            self.ui.mr_bonus_iq.setText('+'+str(self.mapDB.map_running[Map.BonusIQ])+'%')
        else:
            self.ui.mr_bonus_iq.setText('')
        if Map.Mod9 in self.mapDB.map_running:
            if self.mapDB.map_running[Map.Mod9] and self.map_mod_text:
                all_mods = self.map_mod_text + '\r\n<br><b>' +self.mapDB.map_running[Map.Mod9]+ '</b>'
                self.ui.mr_mods.setText(all_mods)
            else:
                self.ui.mr_mods.setText(self.map_mod_text)

    def removeMap(self):
        print('Removing Last Map')
        self.ui_confirm.boxType('confirm')
        del_map = None
        if self.ui_confirm.exec_('Remove Map?', 'Are you sure you want to delete the last map saved to database?'):
            del_map = self.mapDB.deleteLastMap(Maps.Dropped)
            self.updateWindowTitle()
        if del_map:
            self.sysTrayIcon.showMessage(
                'Last Map Removed',
                del_map+' was removed from the database.',
                1, 1000)

    def addMap(self, unlinked=False):
        print('Adding to Map Drops')
        add_map = self.mapDB.addMap(self.map_data, unlinked)
        if add_map:
            self.minimizeToSysTray()
            self.updateWindowTitle()
            self.sysTrayIcon.showMessage(
                'Map Added',
                add_map+' was added to the database.',
                1, 1000)

    def clearMap(self):
        if self.mapDB.map_running:
            self.ui_confirm.boxType('confirm')
            if self.ui_confirm.exec_('Map Cleared?', 'Is the current running map cleared?  No more map drops will be linked to this map.'):
                self.mapDB.clearMap()
                self.updateUiMapRunning(True)
                return True
            else:
                return False
        else:
            return True

    def runMap(self):
        print('Running Selected Map')
        if self.mapDB.runMap(self.map_data):
            self.updateUiMapRunning()
            self.resetBonuses()

    def setDBFile(self, new=False):
        if self.clearMap():
            abs_path = os.path.abspath(os.path.dirname('__file__'))
            if new:
                file_name = QFileDialog.getSaveFileName(self, 'Create New Database File', abs_path+'/data', 'SQLite Files (*.sqlite)')
                if file_name[0]:
                    self.mapDB.setupDB(file_name[0])
            else:
                file_name = QFileDialog.getOpenFileName(self, 'Load Database File', abs_path+'/data', 'SQLite Files (*.sqlite)')
            # Update settings
            if file_name[0]:
                self.mapDB.setDBFile(file_name[0])
                if not new:
                    self.mapDB.setupDB('Checking DB Structure', True)
                self.updateWindowTitle()
                self.buttonAccess(True)
                self.settings['LastOpenedDB'] = file_name[0]
                writeSettings(self.settings)

    def addZanaMods(self):
        print('Adding Zana Mods to Combo Box')
        self.ui.mr_add_zana_mod.clear()
        for i, zana_mod in enumerate(self.zana_mods):
            self.ui.mr_add_zana_mod.addItem(zana_mod[ZanaMod.Name] + ' (' + zana_mod[ZanaMod.Cost] + ')')
            if int(self.settings['ZanaDefaultModIndex']) == i:
                self.ui.mr_add_zana_mod.setCurrentIndex(i)
            if int(self.settings['ZanaLevel']) < zana_mod[ZanaMod.Level]:
                break # Stop adding mod options if Zana level is to low to run them

    def changeZanaLevel(self):
        self.zana_mods[1][ZanaMod.IQ] = int(self.settings['ZanaLevel'])
        self.addZanaMods()

    def changeZanaMod(self):
        print('New Zana Mod Selected')
        if self.mapDB.map_running:
            self.mapDB.map_running[Map.BonusIQ] = self.calcBonusIQ()
            zana_mod_str = self.zana_mods[self.ui.mr_add_zana_mod.currentIndex()][ZanaMod.Desc]
            self.mapDB.map_running[Map.Mod9] = zana_mod_str
            self.updateUiMapRunningBonuses()
            self.ui.mr_mods.moveCursor(QtGui.QTextCursor.End)

    def changeBonusIQ(self):
        print('Bonus IQ Changed')
        if self.mapDB.map_running:
            self.mapDB.map_running[Map.BonusIQ] = self.calcBonusIQ()
            self.updateUiMapRunningBonuses()

    def calcBonusIQ(self):
        zana_iq = self.zana_mods[self.ui.mr_add_zana_mod.currentIndex()][ZanaMod.IQ]
        bonus_iq = self.ui.mr_add_bonus_iq.property('value') + zana_iq
        return bonus_iq

    def resetBonuses(self):
        self.ui.mr_add_zana_mod.setCurrentIndex(-1) # force change event
        self.ui.mr_add_zana_mod.setCurrentIndex(int(self.settings['ZanaDefaultModIndex']))
        self.ui.mr_add_bonus_iq.setProperty('value', 0)

    def openStatFile(self):
        stat_file = self.settings['SelectedStatisticsFile']
        webbrowser.open('file://' + stat_file)

    def getPrefs(self):
        if self.ui_prefs.exec_():
            self.setPrefs()

    def setPrefs(self):
        self.settings = readSettings()
        self.thread.setMapCheckInterval(float(self.settings['MapCheckInterval']))
        self.changeZanaLevel()
        hour12 = self.settings['ClockHour12']
        milliseconds = self.settings['ShowMilliseconds']
        hour12 = False if hour12 == '0' else True
        milliseconds = False if milliseconds == '0' else True
        settings = {'hour12': hour12, 'milliseconds': milliseconds}
        writeSettingsJS(settings)
        print("Preferences Updated")

    def about(self):
        self.ui_confirm.boxType('about')
        self.ui_confirm.exec_('About', 'Map Watch\nVersion '+self.version+'\n\nCreated by\nJonathan.D.Hatten@gmail.com\nIGN: Grahf_Azura')

    def updateWindowTitle(self):
        if self.mapDB.db_file:
            map_count = self.mapDB.countMapsAdded()
            self.setWindowTitle(self.appTitle + ' ---> ' + str(map_count) + ' map drops in database (' + os.path.basename(self.mapDB.db_file) + ')')
        else:
            self.setWindowTitle(self.appTitle + ' ---> Map Database Not Loaded')

    def buttonAccess(self, disable):
        self.ui.ms_add_map.setEnabled(disable)
        self.ui.ms_remove_map.setEnabled(disable)
        self.ui.mr_clear_map.setEnabled(disable)
        self.ui.mr_run_map.setEnabled(disable)
        self.ui.menu_ms_add_map.setEnabled(disable)
        self.ui.menu_ms_add_unlinked_map.setEnabled(disable)
        self.ui.menu_ms_remove_map.setEnabled(disable)
        self.ui.menu_mr_clear_map.setEnabled(disable)
        self.ui.menu_mr_run_map.setEnabled(disable)

    def error(self, err_msg, errors=None):
        err_msg += '\n'
        if errors is not None:
            for err in errors:
                err_msg += '\n'+str(err)
                #print(err)
        self.ui_confirm.boxType('error')
        self.ui_confirm.exec_('Error', err_msg)

    def closeApplication(self):
        print('Map Watch Closing')
        self.mapDB.clearMap() # In-case user forgot to clear thier map before closing app
        self.sysTrayIcon.hide()
        sys.exit()

    def closeEvent(self, event):
        # Changes the close button (X) behavior to minimize instead
        event.ignore()
        if self.firstClose:
            self.sysTrayIcon.showMessage(
                'Minimized To System Tray',
                'Map Watch will still continue to run in the background. Right click and select exit to shut down application.',
                1, 1000)
            self.firstClose = 0
        self.minimizeToSysTray()
        #self.closeApplication()

    def minimizeToSysTray(self):
        self.showMinimized()
        self.hide()


class ConfirmDialog(QtWidgets.QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Confirm()
        self.ui.setupUi(self)
        self.setFixedSize(270, 89)
        print("ConfirmBox loaded")

    def exec_(self, title=None, message=None):
        if title:
            self.setWindowTitle(title)
        if message:
            self.ui.message.setText(message)
        return super().exec_()
    
    def setTitle(self, text):
        self.setWindowTitle(text)

    def setTextMsg(self, text):
        self.ui.message.setText(text)

    def boxType(self, type):
        if type is 'confirm':
            self.setFixedSize(270, 89)
            self.ui.buttonBox.setGeometry(QtCore.QRect(10, 60, 251, 23))
            self.ui.message.setGeometry(QtCore.QRect(10, 0, 251, 61))
            self.ui.message.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
            self.ui.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.No|QtWidgets.QDialogButtonBox.Yes)
        if type is 'confirmXL':
            self.setFixedSize(270, 149)
            self.ui.buttonBox.setGeometry(QtCore.QRect(10, 120, 251, 23))
            self.ui.message.setGeometry(QtCore.QRect(10, 0, 251, 121))
            self.ui.message.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
            self.ui.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.No|QtWidgets.QDialogButtonBox.Yes)
        elif type is 'error':
            self.setFixedSize(270, 199)
            self.ui.buttonBox.setGeometry(QtCore.QRect(10, 170, 251, 23))
            self.ui.message.setGeometry(QtCore.QRect(10, 0, 251, 161))
            self.ui.message.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
            self.ui.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        elif type is 'about':
            self.setFixedSize(270, 189)
            self.ui.buttonBox.setGeometry(QtCore.QRect(10, 160, 251, 23))
            self.ui.message.setGeometry(QtCore.QRect(10, 0, 251, 141))
            self.ui.message.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
            self.ui.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)


class Preferences(QtWidgets.QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.setFixedSize(400, 342)
        self.loadData()
        self.ui.pref_buttons.accepted.connect(self.accept)
        self.ui.pref_buttons.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.reject)
        self.ui.pref_buttons.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self.restoreDefaults)
        print("Preferences Window loaded")

    def loadData(self):
        abs_path = os.path.abspath(os.path.dirname('__file__'))
        statistics_dir = abs_path+'\\statistics\\'
        file_names = os.listdir(statistics_dir)
        self.statistics_files = []
        for file_name in file_names:
            match = re.search(r'\w+\.html', file_name)
            if match:
                self.statistics_files.append(statistics_dir+file_name)

    def insertPrefs(self):
        self.ui.pref_map_check.setProperty('value', float(self.parent.settings['MapCheckInterval']))
        self.ui.pref_startup.setChecked(int(self.parent.settings['LoadLastOpenedDB']))
        self.ui.pref_db_path.setText((self.parent.settings['LastOpenedDB']))
        self.ui.pref_statistics.clear()
        for i, stat_file in enumerate(self.statistics_files):
            self.ui.pref_statistics.addItem(os.path.basename(stat_file))
            if stat_file == self.parent.settings['SelectedStatisticsFile']:
                self.ui.pref_statistics.setCurrentIndex(i)
        self.ui.pref_hour.setChecked(int(self.parent.settings['ClockHour12']))
        self.ui.pref_millisec.setChecked(int(self.parent.settings['ShowMilliseconds']))
        self.ui.pref_zana_level.setProperty('valse', int(self.parent.settings['ZanaLevel']))
        self.ui.pref_defualt_zana_mod.clear()
        for i, zana_mod in enumerate(self.parent.zana_mods):
            self.ui.pref_defualt_zana_mod.addItem(zana_mod[ZanaMod.Name] + ' (' + zana_mod[ZanaMod.Cost] + ')')
            if int(self.parent.settings['ZanaDefaultModIndex']) == i:
                self.ui.pref_defualt_zana_mod.setCurrentIndex(i)
            # if self.ui.pref_zana_level.property('value') < zana_mod[ZanaMod.Level]:
            #     break
        self.ui.pref_on_top.setChecked(int(self.parent.settings['AlwaysOnTop']))

    def restoreDefaults(self):
        self.parent.ui_confirm.boxType('confirm')
        if self.parent.ui_confirm.exec_('Restore Defaults?', 'Are you sure you want to restore the default settings?'):
            get_defaults = True
            self.parent.settings = readSettings(get_defaults)
            self.insertPrefs()

    def accept(self):
        self.parent.settings['MapCheckInterval'] = str(self.ui.pref_map_check.property('value'))
        self.parent.settings['LoadLastOpenedDB'] = str(self.ui.pref_startup.checkState())
        self.parent.settings['SelectedStatisticsFile'] = self.statistics_files[self.ui.pref_statistics.currentIndex()]
        self.parent.settings['ClockHour12'] = str(self.ui.pref_hour.checkState())
        self.parent.settings['ShowMilliseconds'] = str(self.ui.pref_millisec.checkState())
        self.parent.settings['ZanaLevel'] = str(self.ui.pref_zana_level.property('value'))
        self.parent.settings['ZanaDefaultModIndex'] = str(self.ui.pref_defualt_zana_mod.currentIndex())
        self.parent.settings['AlwaysOnTop'] = str(self.ui.pref_on_top.checkState())
        writeSettings(self.parent.settings)
        super().accept()

    def exec_(self):
        self.insertPrefs()
        return super().exec_()


class MapWatcher(QThread):

    trigger = pyqtSignal(object)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.check_interval = 2.0

    def __del__(self):
        self.exiting = True
        self.wait()

    def runLoop(self):
        self.start()

    def setMapCheckInterval(self, seconds):
        self.check_interval = seconds

    def parseMapData(self, copied_str):
        map_rarity =    re.search(r'Rarity:\s(\w*)\n', copied_str)
        map_name1 =     re.search(r'Rarity:\s\w*\n(.*)\n', copied_str)
        map_name2 =     re.search(r'Rarity:\s\w*\n.*\n([^-].*)\n', copied_str)
        map_tier =      re.search(r'Map\sTier:\s(\d*)\s', copied_str)
        map_iq =        re.search(r'Item\sQuantity:\s\+(\d*)\%.*\n', copied_str)
        map_ir =        re.search(r'Item\sRarity:\s\+(\d*)\%.*\n', copied_str)
        map_pack_size = re.search(r'Monster\sPack\sSize:\s\+(\d*)\%.*\n', copied_str)
        map_mods = []
        pattern = re.compile(r'Item\sLevel:\s\d*\n--------\n(.*)', re.DOTALL)
        remaining_data = re.search(pattern, copied_str)
        if remaining_data:
            map_mods = remaining_data.group(1).split('\n')
        map_data = {}
        map_data[Map.TimeAdded] = time.time()
        if map_rarity:
            print('Rarity: ' + map_rarity.group(1))
            map_data[Map.Rarity] = map_rarity.group(1)
        if map_name1 and map_name2:
            print('Map Name: ' + map_name1.group(1) + ' ' + map_name2.group(1))
            map_data[Map.Name] = map_name1.group(1) + ' ' + map_name2.group(1)
        elif map_name1:
            print('Map Name: ' + map_name1.group(1))
            map_data[Map.Name] = map_name1.group(1)
        if map_tier:
            print('Map Tier: ' + map_tier.group(1))
            map_data[Map.Tier] = map_tier.group(1)
        if map_iq:
            print('Map Item Quantity: ' + map_iq.group(1))
            map_data[Map.IQ] = map_iq.group(1)
        if map_ir:
            print('Map Item Rarity: ' + map_ir.group(1))
            map_data[Map.IR] = map_ir.group(1)
        if map_pack_size:
            print('Monster Pack Size: ' + map_pack_size.group(1))
            map_data[Map.PackSize] = map_pack_size.group(1)
        for i, mod in enumerate(map_mods):
            print('Map Mod ' + str(i+1) +': ' + mod)
            map_data[Map.Mod1 + i] = mod
            # Unidentified maps add 30% bonus IQ
            if mod == 'Unidentified':
                map_data[Map.IQ] = '30'
        # Send signal to Update UI
        self.trigger.emit(map_data)

    # Note: This is never called directly. It is called by Qt once the thread environment has been set up.
    def run(self):
        map_check_str = r'\r?\n--------\r?\nTravel to this Map by using it in the Eternal Laboratory or a personal Map Device\. Maps can only be used once\.'
        while not self.exiting:
            copied_data = pyperclip.paste()
            if copied_data:
                if re.search(map_check_str, copied_data) and not re.search(r'Map Watch Time Stamp:', copied_data): # Ignore maps already checked with Time Stamp
                    print('====Found a Map====')
                    # Add time stamp to every map found
                    time_stamp = '========\r\nMap Watch Time Stamp: ' + str(time.time()) + '\r\n========\r\n'
                    pyperclip.copy(time_stamp + copied_data)
                    # Remove all Windows specific carriage returns (\r)
                    copied_data = copied_data.replace('\r', '')
                    # Remove quote on a unique map (if there) and all other unneeded data below
                    pattern = re.compile(r'.*--------.*--------.*--------.*(\n--------.*--------.*)', re.DOTALL)
                    extra_text = re.search(pattern, copied_data)
                    if (extra_text):
                        copied_data = copied_data.replace(extra_text.group(1), '')
                    else:
                        copied_data = re.sub(map_check_str, '', copied_data)
                    # Trim all new lines at end, just in case
                    while copied_data[-1:] == '\n':
                        print('Trimming \\n')
                        copied_data = copied_data[:-1]
                    self.parseMapData(copied_data)
            time.sleep(self.check_interval)


class MapDatabase(object):
    
    def __init__(self, parent=None):
        self.parent = parent
        self.table_names = ['Maps_Dropped','Maps_Ran']
        self.unique_col_name = 'Time_Stamp_ID'
        self.column_names = [['Name','Tier','IQ','IR','Pack_Size','Rarity','Mod1','Mod2','Mod3','Mod4','Mod5','Mod6','Mod7','Mod8','Mod9','Dropped_In_ID'],
                            ['Name','Tier','IQ','Bonus_IQ','IR','Pack_Size','Rarity','Mod1','Mod2','Mod3','Mod4','Mod5','Mod6','Mod7','Mod8','Mod9','Time_Cleared']]
        self.map_running = None
        self.db_file = None
        print('MapDatabase loaded')

    def setDBFile(self, file):
        self.db_file = file
        # TODO: get current map running? has to be saved into db with no time_cleared

    def countMapsAdded(self):
        self.openDB()
        map_count = 0
        try:
            self.c.execute("SELECT * FROM {tn}".format(tn=self.table_names[Maps.Dropped]))
            map_count = len(self.c.fetchall())
        except:
            self.parent.error('Error: A database table could not be found. Atziri corrupted your database file!', sys.exc_info())
        self.closeDB()
        return map_count

    def openDB(self):
        if self.db_file:
            self.conn = sqlite3.connect(self.db_file)
            self.c = self.conn.cursor()
        else:
            self.parent.error('Error: No database file found.', {'Please select a database file before adding any maps.'})

    def closeDB(self):
        if self.db_file:
            self.conn.close()

    def addMap(self, map, unlinked=False):
        if map is None:
            self.parent.error('Error: Database record could not be created.',
                {"No map has been selected. Copy (Ctrl+C) a map from Path of Exile first."})
            return None
        if self.map_running and map[Map.TimeAdded] == self.map_running[Map.TimeAdded]:
            self.parent.error('Error: Database record could not be created.',
                {
                "You can't add the map running to it's own map drops.",
                "This isn't Back to the Future where you go back in time and bang your own mother to create yourself."
                })
            return None
        self.openDB()
        map_name = None
        try:
            for field, value in map.items():
                if int(field) == Map.TimeAdded:
                    self.c.execute("INSERT INTO {tn} ({kcn}) VALUES ({val})".format(
                            tn=self.table_names[Maps.Dropped],
                            kcn=self.unique_col_name,
                            val=value
                        ))
                else:
                    self.c.execute("UPDATE {tn} SET {cn}=({val}) WHERE {kcn}=({key})".format(
                            tn=self.table_names[Maps.Dropped],
                            cn=self.column_names[Maps.Dropped][int(field)-1],
                            kcn=self.unique_col_name,
                            val='\"'+value+'\"',
                            key=map[Map.TimeAdded]
                        ))
            # Map found in
            if self.map_running and not unlinked:
                self.c.execute("UPDATE {tn} SET {cn}=({val}) WHERE {kcn}=({key})".format(
                        tn=self.table_names[Maps.Dropped],
                        cn=self.column_names[Maps.Dropped][15], # Dropped_In_ID
                        kcn=self.unique_col_name,
                        val=self.map_running[Map.TimeAdded],
                        key=map[Map.TimeAdded]
                    ))
            map_name = map[Map.Name]
            self.conn.commit()
            print('Map added to database')
        except sqlite3.IntegrityError:
            self.parent.error('Error: Database record already exists.',
                {"This map has already been added to the database. If you want you may remove (delete) it and re-add it though."})
        except:
            self.parent.error('Error: Database record could not be created.', sys.exc_info())
        self.closeDB()
        return map_name

    def runMap(self, map):
        if map is None:
            self.parent.error('Error: Database record could not be created.',
                {"No map has been selected. Copy (Ctrl+C) a map from Path of Exile first."})
            return False
        if self.map_running and map[Map.TimeAdded] == self.map_running[Map.TimeAdded]:
            self.parent.error('Error: Database record could not be created.',
                {"This map is already running. If you would like to clear it click the 'Map Clear' button."})
            return False
        self.parent.clearMap()
        self.openDB()
        try:
            for field, value in map.items():
                if int(field) == Map.TimeAdded:
                    self.c.execute("INSERT INTO {tn} ({kcn}) VALUES ({val})".format(
                            tn=self.table_names[Maps.Ran],
                            kcn=self.unique_col_name,
                            val=value
                        ))
                else:
                    self.c.execute("UPDATE {tn} SET {cn}=({val}) WHERE {kcn}=({key})".format(
                            tn=self.table_names[Maps.Ran],
                            cn=self.column_names[Maps.Ran][int(field)-1],
                            kcn=self.unique_col_name,
                            val='\"'+value+'\"',
                            key=map[Map.TimeAdded]
                        ))
            self.conn.commit()
            success = True
            self.map_running = copy.deepcopy(map)
        except:
            self.parent.error('Error: Database record could not be created.', sys.exc_info())
            success = False
        self.closeDB()
        return success

    def updateMapRunning(self):
        if self.map_running:
            print('updateMapRunning')
            self.openDB()
            try:
                for col, i in {'Bonus_IQ': Map.BonusIQ, 'Mod9': Map.Mod9}.items():
                    self.c.execute("UPDATE {tn} SET {cn}=({val}) WHERE {kcn}=({key})".format(
                            tn=self.table_names[Maps.Ran],
                            cn=str(col),
                            kcn=self.unique_col_name,
                            val='\"'+str(self.map_running[i])+'\"',
                            key=self.map_running[Map.TimeAdded]
                        ))
                self.conn.commit()
            except:
                self.parent.error('Error: Database record could not be updated.', sys.exc_info())
            self.closeDB()

    def clearMap(self):
        if self.map_running:
            self.updateMapRunning()
            print('Map Cleared')
            self.openDB()
            clear_time = time.time()
            try:
                # Add time map cleared
                self.c.execute("UPDATE {tn} SET {cn}=({val}) WHERE {kcn}=({key})".format(
                        tn=self.table_names[Maps.Ran],
                        cn=self.column_names[Maps.Ran][16], # Time_Cleared
                        kcn=self.unique_col_name,
                        val=clear_time,
                        key=self.map_running[Map.TimeAdded]
                    ))
                self.conn.commit()
                # Any map drops in this map?
                self.c.execute("SELECT * FROM {tn} WHERE {kcn} = (SELECT MAX({mr_kcn}) FROM {mr_tn})".format(
                        tn=self.table_names[Maps.Dropped],
                        kcn=self.column_names[Maps.Dropped][15], # Dropped_In_ID
                        mr_kcn=self.unique_col_name,
                        mr_tn=self.table_names[Maps.Ran]
                    ))
                self.map_running = None
            except:
                self.parent.error('Error: Database record could not be updated.', sys.exc_info())
            if not self.c.fetchone():
                self.parent.ui_confirm.boxType('confirmXL')
                if self.parent.ui_confirm.exec_('Delete Current Map Running?',
                                                'No Map Drops were found in this map.  '+
                                                'Is this correct or did you run this map by mistake and want to delete it from the database?  '+
                                                '\nSelect "No" if you want to record this map with no map drops.'):
                    map_name = self.deleteLastMap(Maps.Ran)
                    if map_name:
                        self.parent.sysTrayIcon.showMessage(
                            'Last Map Ran Removed',
                            map_name+' was removed from the database.',
                            1, 1000)
            self.closeDB()
        else:
            print('No Map to Clear')

    def deleteLastMap(self, from_table):
        self.openDB()
        map_name = None
        try:
            self.c.execute("SELECT * FROM {tn} WHERE {kcn} = (SELECT MAX({kcn}) FROM {tn})".format(
                    tn=self.table_names[from_table],
                    kcn=self.unique_col_name
                ))
            map_name = self.c.fetchone()[Map.Name]
            self.c.execute("DELETE FROM {tn} WHERE {kcn} = (SELECT MAX({kcn}) FROM {tn})".format(
                    tn=self.table_names[from_table],
                    kcn=self.unique_col_name
                ))
            self.conn.commit()
            print('Map Deleted')
        except:
            self.parent.error('Error: Database record could not be deleted.', sys.exc_info())
        self.closeDB()
        return map_name

    def setupDB(self, file, db_struct_check=False):
        if not db_struct_check:
            print('Setting up new map database.')
            if os.path.exists(file):
                os.unlink(file) # Overwrite old file
            self.setDBFile(file)
        else:
            print('Checking database structure.')
        self.openDB()
        for i, tname in enumerate(self.table_names):
            # Create a map table with unique Time_Stamp column
            self.c.execute('CREATE TABLE IF NOT EXISTS {tn} ({cn} REAL PRIMARY KEY)'.format(
                    tn=tname,
                    cn=self.unique_col_name
                ))
            # Get existing columns
            self.c.execute('PRAGMA table_info({tn})'.format(tn=tname))
            existing_columns = []
            for excol in self.c.fetchall():
                existing_columns.append(excol[1])
            # Create columns if they don't already exist
            for col in self.column_names[i]:
                if col not in existing_columns:
                    if col in ['Tier','IQ','Bonus_IQ','IR','Pack_Size']:
                        col_type = 'INTEGER'
                    elif col in ['Dropped_In_ID','Time_Cleared']:
                        col_type = 'REAL'
                    else:
                        col_type = 'TEXT'
                    self.c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct}".format(
                            tn=tname,
                            cn=col,
                            ct=col_type
                        ))
        self.conn.commit()
        self.closeDB()


def writeSettings(settings, defaults=None):
    config = configparser.ConfigParser()
    default_settings = settingDefaults()
    if not settings:
        config['DEFAULT'] = default_settings
        config['CURRENT'] = default_settings
    else:
        if config.read('settings.ini'):
            if defaults: #update
                config['DEFAULT'] = defaults
            config['CURRENT'] = settings
        else:
            print('No settings file found.  Please restart application to create a default settings file.')
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)
        configfile.close()


def readSettings(defaults=False):
    config = configparser.ConfigParser()
    if config.read('settings.ini'):
        if defaults:
            return config['DEFAULT']
        else:
            verifySettings(config, 'CURRENT')
            return config['CURRENT']
    else:
        print('No settings file found, making new settings file with defaults.')
        writeSettings({})
        return readSettings()


def verifySettings(config, section):
    missing_option = False
    default_settings = settingDefaults()
    for option, value in default_settings.items():
        if not config.has_option(section, option):
            config.set(section, option, value)
            config.set('DEFAULT', option, value)
            missing_option = True
    if missing_option:
        writeSettings(config[section], config['DEFAULT'])


def settingDefaults():
    abs_path = os.path.abspath(os.path.dirname('__file__'))
    return {
            'MapCheckInterval': '2.0',
            'AlwaysOnTop': '2',
            'Language': 'English',
            'LastOpenedDB': abs_path+'\\data\\mw_db001.sqlite',
            'LoadLastOpenedDB': '2',
            'SelectedStatisticsFile': abs_path+'\\statistics\\stat_file_01.html',
            'ShowMilliseconds': '0',
            'ClockHour12': '2',
            'ZanaLevel': '8',
            'ZanaDefaultModIndex': '1'
            }


def writeSettingsJS(settings):
    if not settings:
        settings = {'hour12': True, 'milliseconds': False}
    settings = json.JSONEncoder().encode(settings)
    settings = 'var settings = '+settings
    with open('js\settings.js', 'w') as outfile:
        outfile.write(settings)


def main():
    app = QtWidgets.QApplication(sys.argv)
    mw_ui = MapWatchWindow()
    mw_ui.show()

    # All this just to steal focus, damn it Microsoft
    win32gui.EnumWindows(mw_ui._window_enum_callback, r'Map Watch \(')
    pywinapp = pywinauto.application.Application()
    if mw_ui._handle:
        mw_ui.window = pywinapp.window_(handle=mw_ui._handle)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
