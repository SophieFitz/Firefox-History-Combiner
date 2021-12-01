from PyQt5.QtWidgets import QWidget, QPushButton, QGridLayout, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QThread

from configparser import ConfigParser
from pathlib import Path

from programFiles.guiClasses.warning_info import createWarning_InfoDialog, createFaviconsMissingDialog, createErrorDialog, createBackupDialog
from programFiles.combinerFunctions.Supplementary.otherFunctions import removeOrphanedSqliteFiles, faviconsFiles, checkDBExists
from programFiles.combinerFunctions.Supplementary.otherFunctions import removeFiles_Dirs
from programFiles.guiClasses.dbFolderSelect import createDBSelectionDialog
from programFiles.guiClasses.workers import combinerWorker, ffOpenWorker
from programFiles.guiClasses.settings import createSettingsDialog
from programFiles.guiClasses.misc import confirmChanges

import programFiles.globalVars as g
import psutil, logging

combinerLogger = logging.getLogger('Combiner')


class createMainWidget(QWidget):
	def __init__(self):
		super().__init__()

		grid = QGridLayout(self)

		self.stopBtn = QPushButton('Stop')
		self.stopBtn.hide()

		self.dbFoldersBtn = QPushButton(' Select DB folders.... ')
		self.settingsBtn = QPushButton('Settings')
		self.combineBtn = QPushButton('Combine!')

		self.combineBtn.clicked.connect(self.combineWarnings)

		self.dbSelectionDialog = createDBSelectionDialog(self.combineBtn)
		self.dbFoldersBtn.clicked.connect(self.dbSelectionDialog.exec_)
		# self.dbFoldersBtn.click()
		
		settingsDialog = createSettingsDialog()
		self.settingsBtn.clicked.connect(lambda: settingsDialog.exec_()) # Need lambda here, doesn't work without it.
		# self.settingsBtn.click()

		# Placeholder graphic for progress bar
		# Would prefer progress bar integrated into the main window, looks nicer (by default it's separate inside its own window).
		progBarPlaceholder = QLabel('**Progress bar placeholder**')
		progBarPlaceholder.setStyleSheet('font-weight: bold; font-size: 20px')


		grid.addWidget(self.dbFoldersBtn, 1, 8)
		grid.addWidget(self.settingsBtn, 1, 5)
		grid.addWidget(progBarPlaceholder, 9, 1, 1, 10, Qt.AlignHCenter)
		grid.addWidget(self.combineBtn, 10, 10)
		grid.addWidget(self.stopBtn, 10, 10)

		grid.setRowMinimumHeight(0, 20) # Spacing at top

		grid.setRowMinimumHeight(11, 5) # Combine button spacers
		grid.setColumnMinimumWidth(11, 5)

		grid.setColumnMinimumWidth(6, 10) # Space between folder and settings buttons.
		grid.setColumnMinimumWidth(7, 5)
 
	def keyPressEvent(self, keyEvent):
		if keyEvent.key() == Qt.Key_Escape and self.stopBtn.isVisible() == True: self.stopBtn.click() # Press esc to terminate combining.
		if keyEvent.key() in (Qt.Key_Return, Qt.Key_Enter) and self.combineBtn.isVisible() == True: self.combineBtn.click()
		else: super().keyPressEvent(keyEvent)

	def combiningStarted(self):
		Path.cwd().joinpath('places.sqlite').write_bytes(g.primaryDBFolder.joinpath('places.sqlite').read_bytes())

		# Only copy favicons.sqlite if it exists
		if g.primaryDBFolder.joinpath('favicons.sqlite').is_file() == True:
			Path.cwd().joinpath('favicons.sqlite').write_bytes(g.primaryDBFolder.joinpath('favicons.sqlite').read_bytes())

		self.combineBtn.hide()
		self.stopBtn.show()
		self.settingsBtn.setEnabled(False)
		self.dbFoldersBtn.setEnabled(False)

		self.combinerThread.start()

	def combiningFinished(self):
		self.combinerThread.quit()
		self.combinerThread.wait()

		g.combinerConfig.read_file(open('Settings.ini'))
		if g.combinerConfig.getint("GUI", "Stop pressed") == 1:
			print('Combining cancelled') # Print message in tandem with stop pressed
			combinerLogger.info('**Combining cancelled**')

		g.combinerConfig.set('GUI', 'Stop pressed', '0') # Reset "Stop pressed" state
		confirmChanges()
		
		self.stopBtn.hide()
		self.combineBtn.show()
		self.settingsBtn.setEnabled(True)
		self.dbFoldersBtn.setEnabled(True)


	def stopProc(self):
		# Make a local copy of combinerConfig. This ensures thread safety.
		# Calling confirmChanges() here meant reading and writing to Settings.ini at the same time from 2 different threads.
		# Which resulted in glitches.
		combinerConfig = ConfigParser()
		combinerConfig.read_file(open('Settings.ini'))
		combinerConfig.set('GUI', 'Stop pressed', '1')
		with open('Settings.ini', 'w') as settingsFile: combinerConfig.write(settingsFile)

		# The slots are connected multiple times if combining is repeatedly stopped and started. 
		# Therefore, disconnect all slots if any are present.
		self.stopBtn.clicked.disconnect()

	def startCombining(self):
		# Create the QThread and worker, then move the worker to the new QThread.
		self.combinerThread = QThread(self)
		self.combineAllDBs = combinerWorker()
		self.combineAllDBs.moveToThread(self.combinerThread)

		stopMessage = ['Are you sure you want to cancel combining?   ']
		stopConfirmDialog = createWarning_InfoDialog('Stop combining?', stopMessage, 'Yes', 'Warning', 'Stop combining')
		stopConfirmDialog.cancelBtn.setText('No')
		stopConfirmDialog.cancelBtn.show()
		
		stopConfirmDialog.mainButtonsBox.insertSpacing(2, 20)
		stopConfirmDialog.accepted.connect(self.stopProc)
		stopConfirmDialog.height += 15

		# Start and stop signals
		self.combinerThread.started.connect(self.combineAllDBs.runCombinerProc)
		if g.combinerConfig.getint('Reminder dialogs', 'Stop combining') == 0:
			self.stopBtn.clicked.connect(stopConfirmDialog.exec_)

		elif g.combinerConfig.getint('Reminder dialogs', 'Stop combining') == 2:
			self.stopBtn.clicked.connect(self.stopProc)

		# Setup for the error GUI
		self.combineAllDBs.error.connect(createErrorDialog)

		# Reset combine button, quit thread and remove temp files
		self.combineAllDBs.finished.connect(self.combiningFinished)
		
		# DB backup dialog
		backupDialog = createBackupDialog(self)

		# Only backup if the option is checked
		if g.combinerConfig.getint('Backup', 'Finished DBs') == 2:
			backupDialog.exec_()
			self.combineAllDBs.backup.connect(backupDialog.backupDBs)

		elif g.combinerConfig.getint('Backup', 'Finished DBs') == 0:
			if g.combinerConfig.getint('Reminder dialogs', 'Overwrite DB') == 0:
				message = ['Auto-backing up of combined DBs has been disabled. Because of this, the most recently combined',
						   '<i><b>places.sqlite</b></i> DB is located in Firefox History Combiner\'s root directory.',
						   '',
						   f'It will be overwritten by the backup located <a href="file:///{g.primaryDBFolder}">here</a> if you continue.',
						   'Is this okay?']

				if g.primaryDBFolder.joinpath('favicons.sqlite').is_file() == True:
					message[1] = message[1].replace('<i><b>places.sqlite</b></i> DB is', '<i><b>places.sqlite</b></i> and <i><b>favicons.sqlite</b></i> DBs are')
					message[3] = message[3].replace('It will be', 'These will be')

				overwriteDialog = createWarning_InfoDialog('Overwrite DBs?', message, 'OK', 'Warning', 'Overwrite DB')
				overwriteDialog.accepted.connect(self.combiningStarted)
				overwriteDialog.cancelBtn.show()
				
				overwriteDialog.width += 20
				overwriteDialog.exec_()

			elif g.combinerConfig.getint('Reminder dialogs', 'Overwrite DB') == 2:
				self.combiningStarted()


	def combineWarnings(self):
		# Another dialog hinting at the max_pages setting in Firefox. Suggest to the user to change it?

		firefoxOpen = False
		# for proc in psutil.process_iter():
		#     try:
		#         if 'firefox.exe' == proc.name().lower(): firefoxOpen = True

		#     except psutil.AccessDenied: # Not all processes are accessible, therefore skip over any that aren't.
		#         pass

		if firefoxOpen == True:
			def quitFFCheckThread():
				ffOpenDialog.okBtn.setEnabled(True)
				self.ffCheckThread.quit()
				self.ffCheckThread.wait()

			message = ['The databases cannot be combined while Firefox is still open.',
					   'You must close Firefox before you can begin combining.',
					   '',
					   'Once Firefox is closed, press the <b>OK</b> button to begin combining.']

			ffOpenDialog = createWarning_InfoDialog('Please close Firefox', message, 'OK', 'Warning')
			ffOpenDialog.setWindowFlags(Qt.WindowTitleHint)
			ffOpenDialog.okBtn.setEnabled(False)
			ffOpenDialog.width += 18
			
			self.ffCheckThread = QThread(self)

			self.ffOpen = ffOpenWorker()
			self.ffOpen.moveToThread(self.ffCheckThread)
			self.ffOpen.finished.connect(quitFFCheckThread)

			self.ffCheckThread.started.connect(self.ffOpen.check)
			self.ffCheckThread.start()

			ffOpenDialog.exec_()

		primaryDBPath = g.primaryDBFolder.joinpath('places.sqlite')
		if checkDBExists(primaryDBPath) == False:
			primaryDBPath.unlink() # Remove 0-byte places.sqlite file.
			message = [f'The main DB (<b><i>places.sqlite</i></b>) is either missing from <a href="file:///{g.primaryDBFolder}">here</a>'
						' or has been misnamed.',
						'The name must be <b><i>places.sqlite</i></b> (and <b><i>favicons.sqlite</i></b> if relevant).',
						'Please rename the appropriate files (along with its <b><i>favicons.sqlite</i></b> counterpart if relevant)',
						'and copy it/them into the above folder. Then press <i>Combine</i> again.']

			placesMissingDialog = createWarning_InfoDialog('Main places.sqlite DB missing', message, 'OK', 'Error')
			placesMissingDialog.width -= 3
			placesMissingDialog.height += 10
			placesMissingDialog.heightComp = 50
			placesMissingDialog.exec_()
			return

		(mainMissing, othersMissing) = faviconsFiles('Check')
		faviconsMissingDialog = createFaviconsMissingDialog(mainMissing, othersMissing)
		faviconsMissingDialog.accepted.connect(lambda: self.startCombining())

		if len(othersMissing) > 0: faviconsMissingDialog.exec_('Resizable') # Make it resizable if it's a list, otherwise don't.
		elif len(othersMissing) == 0 and mainMissing is not None: faviconsMissingDialog.exec_()

		elif mainMissing is None and len(othersMissing) == 0:
			self.startCombining()