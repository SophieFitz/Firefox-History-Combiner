from PyQt5.QtWidgets import QApplication, QPushButton, QDialog, QLabel, QStyle, QHBoxLayout, QVBoxLayout,\
							QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QCheckBox

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
from pathlib import Path

from programFiles.combinerFunctions.Supplementary.exceptionLogging import insertExceptionLog, dictExceptionLog, generalExceptionLog
from programFiles.guiClasses.widgets import createCheckbox
from programFiles.guiClasses.misc import confirmChanges

import programFiles.globalVars as g
import webbrowser, re, logging


class createWarning_InfoDialog(QDialog):
	def __init__(dialog, title, message, btnText, imgType, *show):
		super().__init__()

		dialog.setWindowTitle(title)
		dialog.setWindowFlags(Qt.WindowCloseButtonHint)

		if show: dialog.show = True
		dialog.heightComp = 70 # This is height compensation for the minimum size of the message label. It doesn't display how I want it to without this.

		iconLabel = QLabel(dialog)
		if imgType == 'Info':
			dialog.icon = QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation)
			iconLabel.move(10, 10)
			messageLabelOffset = 10
			dialog.heightComp = 45

		elif imgType == 'Warning':
			dialog.icon = QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning)
			iconLabel.move(10, 10)
			messageLabelOffset = 12
			dialog.heightComp = 60

		elif imgType == 'Error':
			dialog.icon = QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical)
			iconLabel.move(13, 15)
			messageLabelOffset = 10
			dialog.heightComp = 60

		iconLabel.setPixmap(dialog.icon.pixmap(40, 40))
		iconLabel.show()

		# dialog.setWindowIcon(dialog.icon)

		dialog.messageLabel = QLabel('', dialog)
		dialog.messageLabel.setStyleSheet('font-size: 13px;')
		dialog.messageLabel.move(iconLabel.geometry().right() + messageLabelOffset, 13)
		dialog.messageLabel.setOpenExternalLinks(True)
		dialog.messageLabel.show()
		dialog.setDialogDims(message)


		# # OK + Cancel buttons
		dialog.okBtn = QPushButton(btnText)

		dialog.cancelBtn = QPushButton('Cancel')
		dialog.cancelBtn.clicked.connect(lambda: dialog.reject())
		dialog.cancelBtn.hide()

		dialog.mainButtonsBox = QHBoxLayout()
		dialog.mainButtonsBox.addWidget(dialog.okBtn)
		dialog.mainButtonsBox.addWidget(dialog.cancelBtn)
		dialog.mainButtonsBox.insertStretch(0, 1)

		dialog.mainBox = QVBoxLayout(dialog)
		dialog.mainBox.addLayout(dialog.mainButtonsBox)
		dialog.mainBox.insertStretch(0, 1) # Add margin

		if show:
			showAgainCheckbox = createCheckbox('Don\'t show this again     ', 'Reminder dialogs', show[0])
			showAgainCheckbox.setStyleSheet('font-size: 13px')

			 # Only confirm or revert changes if the 'Don't show this again' checkbox is present.
			dialog.rejected.connect(lambda: g.combinerConfig.read_file(open('Settings.ini')))
			dialog.okBtn.clicked.connect(lambda: confirmChanges(dialog))

			dialog.mainButtonsBox.insertWidget(0, showAgainCheckbox)
			dialog.mainButtonsBox.insertSpacing(0, 40)

		else: dialog.okBtn.clicked.connect(dialog.accept)

	def setDialogDims(dialog, message):
		dialog.textOffset = 50
		numLines = len(message)

		messageForLineLens = []
		tagsToIgnore = ['<b>', '<i>', '</b>', '</i>', '</a>', '<a{1}.*>']
		for line in message:
			for tag in tagsToIgnore:
				line = re.sub(tag, '', line)

			messageForLineLens.append(line)

		lineLens = [len(line) for line in messageForLineLens]

		messageJoined = [f'{line}\n' for line in message]
		messageJoined = ''.join(messageJoined)
		messageJoined = f'<pre style="font-family: segoe ui; font-size: 13px">{messageJoined}</pre>'

		dialog.messageLabel.setText(messageJoined)

		dialog.width = dialog.textOffset + int(6.0 * max(lineLens)) # Was 6.4
		minHeight = 70
		heightFactor = 13

		if dialog.show: heightFactor = 15 # Need more vertical space for the checkbox
		dialog.height = minHeight + heightFactor * numLines


	def exec_(dialog, *resize):
		dialog.messageLabel.setMinimumSize(dialog.width - dialog.textOffset, dialog.height - dialog.heightComp)

		if not resize: dialog.setFixedSize(dialog.width, dialog.height)
		elif resize:
			dialog.resize(dialog.width, dialog.height)

		super().exec_()


class createFaviconsMissingDialog(createWarning_InfoDialog):
	def __init__(dialog, main, fileList):
		if main is not None:
			newWidth = 0
			newHeight = 0
			heightComp = 50

			titleText = ['The main DB is missing its <b><i>favicons.sqlite</i></b> counterpart file.',
						 'Combining can techincally continue without this file, however this is not recommended.', 
						 f'Press <b><i>Cancel</i></b>, then locate the <b><i>favicons.sqlite</i></b> file and copy it <a href="file:///{g.primaryDBFolder}">here.</a>',
						 '',
						 'After this you can restart combining.']

			if len(fileList) > 0: 
				titleText.extend(['', 
								  'In addition, the following databases are missing their <b><i>favicons DB</i></b> counterparts.',
								  'These also need copying into the appropriate folders (listed below):'])
				newHeight = 212
				heightComp = 255
				space = 100

		elif main is None:
			titleText = ['The following databases are missing their <b><i>favicons DB</i></b> counterparts.',
						 'Combining can techincally continue without these files, however this is not recommended.',
						 'Press <b><i>Cancel</i></b>, then locate the missing <b><i>favicons DBs</i></b> and copy them into the appropriate folders.',
						 '',
						 'After this you can restart combining.']

			newWidth = 20
			newHeight = 195
			heightComp = 250
			space = 90


		super().__init__('Favicons.sqlite file(s) are missing / haven\'t been named properly', titleText, 'Continue', 'Warning')
		dialog.width += newWidth
		dialog.height += newHeight
		dialog.heightComp = heightComp
		dialog.cancelBtn.setDefault(True)
		dialog.cancelBtn.show()

		iconsList = QListWidget()
		leftMarginBox = QHBoxLayout()
		leftMarginBox.addSpacing(45)
		leftMarginBox.addWidget(iconsList)
		# leftMarginBox.addSpacing(83)

		if len(fileList) > 0:
			# dialog.mainBox.takeAt(0) # Remove stretch as it prevents auto resize of text box
			dialog.mainBox.insertLayout(1, leftMarginBox)
			# dialog.mainBox.insertSpacing(1, space) # This apparently does nothing????
			dialog.mainBox.insertSpacing(3, 1)

			dbFolders = {}
			for dbPath in fileList:
				if dbFolders.get(dbPath.parent) is None:
					dbFolders.update({dbPath.parent: []})

				dbFolders[dbPath.parent].append(dbPath.name)


			titleFont = QFont()
			titleFont.setBold(True)
			titleFont.setItalic(True)
			titleFont.setUnderline(True)
			titleFont.setPointSize(11)

			firstFolder = list(dbFolders.keys())[0]
			for folder, DBs in dbFolders.items():
				i = iconsList.count()

				# Have a smaller margin for the first folder in the list. Looks better.
				folderTopMargin = 10
				if folder == firstFolder: folderTopMargin = 2

				iconsList.addItem('')
				iconsList.item(i).setSizeHint(QSize(1, folderTopMargin))

				iconsList.addItem(f'{folder}')
				iconsList.item(i+1).setFont(titleFont)

				iconsList.addItem('')
				iconsList.item(i+2).setSizeHint(QSize(1, 5))

				for dbName in DBs:
					dbNumberSuffix = dbName.split('places')[1]
					label = QLabel(f'<div style="font-size: 13px; text-decoration: line-through; margin-left: 5px"> {dbName}</div>'
								   f'<div style="font-weight: bold; font-size: 13px; margin-left: 6px">favicons{dbNumberSuffix}')
					
					listItem = QListWidgetItem()
					listItem.setSizeHint(QSize(1, 34))
					iconsList.addItem(listItem)
					iconsList.setItemWidget(listItem, label)

					iconsList.addItem('')
					iconsList.item(i+4).setSizeHint(QSize(1, 6))

			# Make items unclickable
			iconsList.setStyleSheet('QListWidget::item:disabled {background: transparent; color: black}')
			for i in range(iconsList.count()):
				iconsList.item(i).setFlags(iconsList.item(i).flags() & ~Qt.ItemIsEnabled)


class createErrorDialog(createWarning_InfoDialog):
	def __init__(dialog, errorItems):
		errorItems = errorItems[0]

		messageTitle = ['', 'The following error occurred.', 'Please send me the <b>combiner.log</b> file so I can figure out the problem.']
		super().__init__('Combining exception', messageTitle, 'OK', 'Error')
		dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMaximizeButtonHint)
		
		dialog.textBox = QTextEdit(f'')
		dialog.textBox.setTextInteractionFlags(Qt.TextSelectableByMouse)
		dialog.textBox.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		dialog.textBox.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		
		leftMarginBox = QHBoxLayout()
		leftMarginBox.addSpacing(4)
		leftMarginBox.addWidget(dialog.textBox)
		leftMarginBox.addSpacing(2)

		dialog.mainBox.takeAt(0) # Remove stretch as it prevents auto resize of text box
		dialog.mainBox.insertLayout(0, leftMarginBox)
		dialog.mainBox.insertSpacing(0, 47)
		
		dialog.height *= 3
		dialog.height -= 48
		dialog.heightComp = dialog.height - 40
		dialog.width *= 1.2
		dialog.setMinimumSize(700, 300)


		includePersonalInfo = createCheckbox('Include URLs, search terms etc. in the log file (helps with debugging).', 'Debugging', 'Log personal info')
		includePersonalInfo.setStyleSheet('font-size: 13px')
		includePersonalInfo.stateChanged.connect(lambda: dialog.formatLogEntry(errorItems, includePersonalInfo.checkState()))
		
		if type(errorItems) is str:
			errorItems = generalExceptionLog(errorItems)
			dialog.textBox.setText(f'<pre>{errorItems}</pre>')
			dialog.errorMessage = errorItems

		elif type(errorItems) is dict:
			show = False

			if errorItems.get('type') == 'dictExc':
				errorSplit = errorItems.get('errorMessage').split('      ')
				for i in range(1, len(errorSplit)): # Ignore first value as it's purely descriptive
					value = errorSplit[i]
					if 'url' in value.lower() or 'host' in value.lower(): show = True


			elif errorItems.get('type') == 'insertExc': show = True


			dialog.mainButtonsBox.insertWidget(0, includePersonalInfo)
			dialog.mainButtonsBox.insertSpacing(0, 7)
			includePersonalInfo.setVisible(show)
			dialog.formatLogEntry(errorItems, includePersonalInfo.checkState())


		dialog.finished.connect(dialog.closed)
		dialog.exec_('Resizable')

	def closed(dialog):
		combinerLogger = logging.getLogger('Combiner')

		now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
		combinerLogger.error(f'\n\nTimestamp: {now}\n{dialog.errorMessage}')

		confirmChanges()

	def formatLogEntry(dialog, errorItems, checkState):
		currScrollPos = dialog.textBox.verticalScrollBar().value()

		if errorItems.get('type') == 'insertExc': dialog.errorMessage = insertExceptionLog(errorItems, checkState)
		elif errorItems.get('type') == 'dictExc': dialog.errorMessage = dictExceptionLog(errorItems, checkState)

		dialog.textBox.clear()
		dialog.textBox.setText(f'<pre>{dialog.errorMessage}</pre>')
		dialog.textBox.verticalScrollBar().setValue(currScrollPos)


class createBackupDialog(createWarning_InfoDialog):
	def __init__(dialog, main):
		message = ['The fully combined DB will be backed up into the <b>Completed DBs</b> folder.',
				   'It will be placed in a subfolder, which can be named in the box below.',
				   '',
				   'The date/time will be automatically appended.',
				   'If the box is left blank, the name will <b><i>BE the date/time.</b></i>'
				   '']

		super().__init__('Completed DB folder name', message, 'OK', 'Info')
		dialog.timer = QTimer()

		dialog.textInput = QLineEdit()
		dialog.textInput.textEdited.connect(dialog.displayTime)
		
		dialog.timeLabel = QLabel()
		dialog.timeLabel.setStyleSheet('color: grey')
		dialog.timeLabel.hide()

		dialog.updateTime()
		
		dialog.inputBox = QHBoxLayout()
		dialog.mainButtonsBox.insertLayout(0, dialog.inputBox)
		dialog.mainButtonsBox.takeAt(1) # Remove stretch as spacing is manually configured here.

		dialog.spaceConst = 55
		dialog.inputBox.addSpacing(40)
		dialog.inputBox.addWidget(dialog.textInput)
		dialog.inputBox.addWidget(dialog.timeLabel)
		dialog.inputBox.addSpacing(dialog.spaceConst + 140)

		# dialog.height += 35
		dialog.width += 22
		dialog.heightComp = 60
		dialog.accepted.connect(lambda: dialog.acceptedSlot(main))

	def exec_(dialog):
		# See: https://stackoverflow.com/questions/41819082/updating-pyqt-label
		dialog.timer.timeout.connect(dialog.updateTime)
		dialog.timer.start(1000)
		dialog.textInput.setFocus()

		super().exec_()

	def updateTime(dialog):
		dialog.now = datetime.now().strftime('%d-%m-%Y %H.%M.%S')
		dialog.timeLabel.setText(f'({dialog.now})')
		dialog.textInput.setPlaceholderText(f'{dialog.now}')

	def displayTime(dialog):
		if len(dialog.textInput.text()) > 0:
			dialog.textInput.setAlignment(Qt.AlignHCenter)
			if dialog.timeLabel.isHidden() == True:
				dialog.inputBox.takeAt(dialog.inputBox.count() -1)
				dialog.inputBox.addSpacing(dialog.spaceConst + 23)
				dialog.timeLabel.show()

		elif len(dialog.textInput.text()) == 0:
			dialog.textInput.setAlignment(Qt.AlignLeft)
			if dialog.timeLabel.isHidden() == False:
				dialog.inputBox.takeAt(dialog.inputBox.count() -1)
				dialog.inputBox.addSpacing(dialog.spaceConst + 140)
				dialog.timeLabel.hide()

	def acceptedSlot(dialog, main):
		g.combinerConfig.set('Backup', 'Date/time', str(dialog.now))
		main.combiningStarted()

	def backupDBs(dialog):
		now = g.combinerConfig.get('Backup', 'Date/time')
		backupDir = dialog.textInput.text()
		if len(backupDir) == 0: backupDir = now # If the input is empty
		elif len(backupDir) > 0: backupDir = f'{backupDir} ({now})' # If the user has entered a name

		backupDir = Path.cwd().joinpath(f'Completed DBs\\{backupDir}')
		backupDir.mkdir()
		Path.cwd().joinpath('places.sqlite').replace(backupDir.joinpath('places.sqlite'))
		
		# Only copy favicons.sqlite if it exists
		if Path.cwd().joinpath('favicons.sqlite').is_file() == True:
			Path.cwd().joinpath('favicons.sqlite').replace(backupDir.joinpath('favicons.sqlite'))

		# Open the Completed DBs folder if the option is checked.
		# TODO: Check if dialog already open
		if g.combinerConfig.getint('Backup', 'Open folder') == 2: webbrowser.open(f'file:///{backupDir}')