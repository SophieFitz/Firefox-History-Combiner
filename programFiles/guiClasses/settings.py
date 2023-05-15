import PyQt5.QtWidgets as QtW
from PyQt5.QtCore import Qt

from datetime import datetime
from pathlib import Path

from programFiles.combinerFunctions.Supplementary.sqlFunctions import checkDBPost34

from programFiles.guiClasses.warning_info import createWarning_InfoDialog
from programFiles.guiClasses.misc import confirmChanges, cancelChanges
from programFiles.guiClasses.widgets import createCheckbox

import programFiles.globalVars as g
import logging

class createSettingsDialog(QtW.QDialog):
	def __init__(dialog):
		super().__init__()

		dialog.setFixedSize(400, 250)
		dialog.setWindowTitle('Settings')
		dialog.setWindowFlags(Qt.WindowCloseButtonHint)

		dialog.grid = QtW.QGridLayout(dialog)

		dialog.okBtn = QtW.QPushButton('OK')
		dialog.okBtn.clicked.connect(lambda: confirmChanges(dialog = dialog))
		dialog.okBtn.setDefault(True)
		dialog.okBtn.setFocus()

		dialog.cancelBtn = QtW.QPushButton('Cancel')
		dialog.cancelBtn.clicked.connect(lambda: cancelChanges(dialog = dialog))

	# 'Don't show again' dialog options don't work if put in __init__(). 
	# __init__() only works once, on first creation. Therefore any outside changes that influence options inside of this dialog won't work
	# as they can only be created once. Putting them in exec_() fixes the problem as this is called anew on each creation.
	def exec_(dialog):
		# When using exec_() instead of __init__(), a visual bug in certain text-displaying widgets occurs. 
		# For labels, it becomes essentially multi-coloured if you open and close the window it's attached to multiple times over. 
		# For radio buttons and checkboxes they become progressively more blurry.
		# Manually overwriting the widget's background-color fixes the bug. Or the widget's parent (QTabWidget in this case).
		bgColour = 'rgb(240, 240, 240)'

		tabWidget = QtW.QTabWidget()
		tabWidget.setStyleSheet(f'background-color: {bgColour}')
		tabWidget.addTab(dialog.historyTab(dialog), 'History')
		tabWidget.addTab(dialog.backupTab(dialog), 'Backups')
		tabWidget.insertTab(1, dialog.dialogsTab(dialog), 'Dialogs') # This is inserted as it relies on the previous tabs' data.
		tabWidget.addTab(dialog.uiTab(dialog), 'UI')
		tabWidget.addTab(dialog.miscTab(dialog), 'Misc')

		# Remember last selected tab
		tabWidget.setCurrentIndex(g.combinerConfig.getint('GUI', 'Settings - Last selected tab'))
		tabWidget.currentChanged.connect(lambda: g.combinerConfig.set('GUI', 'Settings - Last selected tab', str(tabWidget.currentIndex())))

		dialog.grid.addWidget(tabWidget, 0, 0, 1, -1)
		dialog.grid.addWidget(dialog.okBtn, 5, 5)
		dialog.grid.addWidget(dialog.cancelBtn, 5, 6)

		super().exec_()

	def keyPressEvent(dialog, keyEvent):
		if keyEvent.key() == Qt.Key_Escape: dialog.cancelBtn.setFocus()
		else: super().keyPressEvent(keyEvent)

	def keyReleaseEvent(dialog, keyEvent):
		if keyEvent.key() == Qt.Key_Escape: dialog.cancelBtn.click()
		else: super().keyReleaseEvent(keyEvent)

	class historyTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			titleLabel = QtW.QLabel('Include:')
			titleLabel.setStyleSheet('font-weight: bold; font-size: 12px')

			bookmarks = createCheckbox('Bookmarks', 'History Combiner', 'Bookmarks')
			bookmarkFoldersPos = createCheckbox('Position folders above bookmarks', 'History Combiner', 'Folders above')
			keywords = createCheckbox('Keywords', 'History Combiner', 'Keywords')
			inputHistory = createCheckbox('Input history (autocomplete)', 'History Combiner', 'Inputhistory')
			updateFrecency = createCheckbox('Frecency: update some, all or none', 'History Combiner', 'Update frecency', True)
			tab.includeDownloads = createCheckbox('Downloads', 'History Combiner', 'Include downloads')
			
			tab.includeDownloads.stateChanged.connect(lambda: tab.downloadsWarning())
			bookmarks.stateChanged.connect(lambda: bookmarkFoldersPos.setEnabled(bookmarks.isChecked()))
			bookmarkFoldersPos.setEnabled(bookmarks.isChecked())

			folderPosBox = QtW.QHBoxLayout()
			folderPosBox.addSpacing(19)
			folderPosBox.addWidget(bookmarkFoldersPos)
			
			checkmarksBox = QtW.QVBoxLayout()
			checkmarksBox.addWidget(bookmarks)
			checkmarksBox.addLayout(folderPosBox)

			leftMarginBox = QtW.QHBoxLayout()
			leftMarginBox.addSpacing(15)
			leftMarginBox.addLayout(checkmarksBox)

			for widget in (keywords, inputHistory, tab.includeDownloads, updateFrecency):
				checkmarksBox.addWidget(widget)
			
			checkmarksBox.addStretch(1)

			mainFrame = QtW.QFrame(tab)
			mainFrame.move(6, 0)

			mainBox = QtW.QVBoxLayout(mainFrame)
			mainBox.addWidget(titleLabel)
			mainBox.addLayout(leftMarginBox)

		def downloadsWarning(tab):
			option = 'Downloads'
			if g.combinerConfig.getint('Reminder dialogs', option) == 0: # If 'Don't show this again' is unchecked, show the dialog!
				if tab.includeDownloads.checkState() == 2:
					dbInsPost34 = checkDBPost34()

					if dbInsPost34 == False:
						message = ['If any of your DBs are older than Firefox 21.0, downloads history cannot be transferred.',
								   'In prior versions to this, all downloads were stored in a separate database.',
								   'It is impossible to transfer them from/into a DB older than 21.0.']

						downloadsDialog = createWarning_InfoDialog('Downloads warning', message, 'OK', 'Info', option)
						downloadsDialog.height += 5
						downloadsDialog.exec_()


	class backupTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			dialog.backupFinishedDBs = createCheckbox('Backup completed DBs', 'Backup', 'Finished DBs')
			overwritePrimaryDB = createCheckbox('Hide overwrite Primary DB warning dialog', 'Reminder dialogs', 'Overwrite DB')
			openCompletedFolder = createCheckbox('Automatically show folder on completion', 'Backup', 'Open folder')

			dialog.backupFinishedDBs.stateChanged.connect(lambda: openCompletedFolder.setEnabled(dialog.backupFinishedDBs.isChecked()))
			openCompletedFolder.setEnabled(dialog.backupFinishedDBs.isChecked())

			dialog.backupFinishedDBs.stateChanged.connect(lambda: overwritePrimaryDB.setEnabled(not dialog.backupFinishedDBs.isChecked()))
			overwritePrimaryDB.setEnabled(not dialog.backupFinishedDBs.isChecked())

			completedDBsPath = Path.cwd().joinpath('Completed DBs')
			tab.dbFolders = [folder for folder in completedDBsPath.iterdir()]
			tab.timestampToSkip = 0
			sizeSaved = 0
			for folder in tab.dbFolders:
				if folder.stat().st_mtime > tab.timestampToSkip:
					tab.timestampToSkip = folder.stat().st_mtime

			for folder in tab.dbFolders:
				if folder.stat().st_mtime == tab.timestampToSkip: continue
				for db in folder.iterdir():
					sizeSaved += db.stat().st_size

			sizeSaved = round(sizeSaved/pow(1024, 2), 2)

			message = ['This will permanently delete <b>all but</b> the most recently combined DB.', 
					   'This cannot be undone! Are you <b><i>ABSOLUTELY SURE</i></b> you want to do this?',
					   '',
					   f'<i>(Potential HDD space saved: {sizeSaved}MB)</i>']

			purgeWarningDialog = createWarning_InfoDialog('Delete backups?', message, 'Yes', 'Error')
			purgeWarningDialog.accepted.connect(tab.purgeOldDBs)
			purgeWarningDialog.cancelBtn.setText('No')
			purgeWarningDialog.cancelBtn.show()
			purgeWarningDialog.width += 40


			purgeBtn = QtW.QPushButton('Purge Completed DBs')
			purgeBtn.clicked.connect(purgeWarningDialog.exec_)
			if len(tab.dbFolders) <= 1: # Only enable button if there's more than one folder to purge.
				purgeBtn.setEnabled(False)
				purgeBtn.setStyleSheet('background-color: rgba(240, 240, 240, 80)')
			
			purgeBox = QtW.QHBoxLayout()
			purgeBox.addStretch(1)
			purgeBox.addWidget(purgeBtn)

			mainBox = QtW.QVBoxLayout(tab)
			mainBox.addWidget(dialog.backupFinishedDBs)
			mainBox.addWidget(overwritePrimaryDB)
			mainBox.addWidget(openCompletedFolder)
			mainBox.addStretch(1)
			mainBox.addLayout(purgeBox)

		def purgeOldDBs(tab):
			for folder in tab.dbFolders:
				if folder.stat().st_mtime == tab.timestampToSkip: continue
				for db in folder.iterdir(): db.unlink()
				folder.rmdir()


	class dialogsTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			titleLabel = QtW.QLabel('Hide dialog for:')
			titleLabel.setStyleSheet('font-weight: bold; font-size: 12px')

			welcome = createCheckbox('Welcome message', 'Reminder dialogs', 'Welcome')
			downloads = createCheckbox('Pre FF 21.0 downloads warning', 'Reminder dialogs', 'Downloads')
			# numberDBs = createCheckbox('Number DBs reminder', 'Reminder dialogs', 'Number DBs')
			stopCombining = createCheckbox('Stop combining warning', 'Reminder dialogs', 'Stop combining')
			firefoxClose = createCheckbox('Close all Firefox instances warning', 'Reminder dialogs', 'Firefox close')


			checkmarksBox = QtW.QVBoxLayout()
			leftMarginBox = QtW.QHBoxLayout()
			leftMarginBox.addSpacing(10)
			leftMarginBox.addLayout(checkmarksBox)

			checkmarksBox.addWidget(welcome)
			checkmarksBox.addWidget(downloads)
			# checkmarksBox.addWidget(numberDBs)
			checkmarksBox.addWidget(stopCombining)
			checkmarksBox.addWidget(firefoxClose)
			checkmarksBox.addStretch(1)

			mainFrame = QtW.QFrame(tab)
			mainFrame.move(6, 0)

			mainBox = QtW.QVBoxLayout(mainFrame)
			mainBox.addWidget(titleLabel)
			mainBox.addLayout(leftMarginBox)


	class uiTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			autoSizeFolderDialog = createCheckbox('Auto-resize dialog width to longest folder name', 'GUI', 'Auto-size folder dialog width')
			# autoSizeFolderDialog.setToolTip('No wider than half the width of the current screen resolution')

			titleLabel = QtW.QLabel('Folder selection dialog:')
			titleLabel.setStyleSheet('font-weight: bold; font-size: 12px')

			widgetBox = QtW.QVBoxLayout()
			leftMarginBox = QtW.QHBoxLayout()
			leftMarginBox.addSpacing(10)
			leftMarginBox.addLayout(widgetBox)

			widgetBox.addWidget(autoSizeFolderDialog)

			mainFrame = QtW.QFrame(tab)
			mainFrame.move(6, 0)

			mainBox = QtW.QVBoxLayout(mainFrame)
			mainBox.addWidget(titleLabel)
			mainBox.addLayout(leftMarginBox)
			mainBox.addStretch(1)


	class miscTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			pyInstallerCrashFiles = createCheckbox('Delete leftover temporary files, if the program crashes', 'Misc', 'Delete crashed py-installer files')

			mainBox = QtW.QVBoxLayout(tab)
			mainBox.addWidget(pyInstallerCrashFiles)
			mainBox.addStretch(1)


	class debugTab(QtW.QWidget):
		def __init__(tab, dialog):
			super().__init__()

			# enableDebug = createCheckbox('Enable debugging', 'Debugging', 'Enabled')
			# enableDebug.stateChanged.connect(lambda: tab.setLoggingLevel())

			logPersonalInfo = createCheckbox('Log URLs, page names etc.', 'Debugging', 'Log personal info')
			optionsBox = QtW.QVBoxLayout()
			
			mainBox = QtW.QVBoxLayout(tab)
			mainBox.addWidget(logPersonalInfo)
			# mainBox.addWidget(enableDebug)
			mainBox.addLayout(optionsBox)
			mainBox.addStretch(1)

		def setLoggingLevel(tab):
			debug = g.combinerConfig.getint('Debugging', 'Enabled')

			if debug == 0: level = 40 # ERROR
			elif debug == 2: level = 10 # DEBUG

			g.combinerConfig.set('Debugging', 'Debug level', str(level))
			combinerLogger = logging.getLogger('Combiner')
			combinerLogger.setLevel(level)