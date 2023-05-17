from PyQt6.QtCore import Qt, QSize, QItemSelectionModel
from PyQt6.QtGui import QFont, QGuiApplication
import PyQt6.QtWidgets as QtW
from pathlib import Path
import ast

from programFiles.guiClasses.warning_info import createWarning_InfoDialog
from programFiles.guiClasses.misc import confirmChanges, cancelChanges
from programFiles.guiClasses.widgets import createCheckbox
from programFiles.otherFunctions import checkFolderHasDBs

import programFiles.globalVars as g

class createDBSelectionDialog(QtW.QDialog):
	def __init__(dialog, combineBtn):
		super().__init__()

		dialog.combineBtn = combineBtn
		dialog.minHeight = 243

		dialog.setMinimumSize(450, dialog.minHeight)
		dialog.setWindowTitle('Database folder selection')
		dialog.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)

		# dialog.recursiveCheckbox = createCheckbox('Look in all subfolders (recursive processing)', 'History Combiner', 'Recursive')
		# dialog.recursiveCheckbox.setToolTip('Doesn\'t apply to Firefox Profiles (i.e. \\AppData\\Roaming\\Mozilla\\Firefox\\Profiles)')

		dialog.selectionBox = QtW.QListWidget()
		dialog.selectionBox.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		dialog.selectionBox.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		dialog.selectionBox.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection) # Enable multi-selection!
		dialog.selectionBox.setMinimumWidth(220)
		
		dialog.selectionBox.keyPressEvent = dialog.selectionBoxEnterPressed
		dialog.selectionBox.doubleClicked.connect(lambda: dialog.modifyDir())

		addBtn = QtW.QPushButton('Add')
		addBtn.clicked.connect(lambda: dialog.addDir())

		modifyBtn = QtW.QPushButton('Modify')
		modifyBtn.clicked.connect(lambda: dialog.modifyDir())

		removeBtn = QtW.QPushButton('Remove')
		removeBtn.clicked.connect(lambda: dialog.removeDir())


		dialog.okBtn = QtW.QPushButton('OK')
		dialog.okBtn.clicked.connect(lambda: dialog.checkOK())
		dialog.okBtn.setDefault(True)
		dialog.okBtn.setFocus()

		dialog.cancelBtn = QtW.QPushButton('Cancel')
		dialog.cancelBtn.clicked.connect(lambda: cancelChanges(dialog = dialog))
		dialog.cancelBtn.keyReleaseEvent = dialog.cancelKeyRelease
		
		mainBox = QtW.QVBoxLayout(dialog)

		# Selection box and buttons
		selectHBox = QtW.QHBoxLayout()
		selectHBox.addSpacing(8)
		selectHBox.addWidget(dialog.selectionBox)
		
		selectButtonsBox = QtW.QVBoxLayout()
		selectButtonsBox.addSpacing(3)
		selectButtonsBox.addWidget(addBtn)
		selectButtonsBox.addWidget(modifyBtn)
		selectButtonsBox.addWidget(removeBtn)
		selectButtonsBox.addStretch(1)

		selectHBox.addLayout(selectButtonsBox)
		mainBox.addLayout(selectHBox)
		mainBox.addSpacing(5)

		# Ok + Cancel buttons
		mainButtonsBox = QtW.QHBoxLayout()
		# mainButtonsBox.addSpacing(9)
		# mainButtonsBox.addWidget(dialog.recursiveCheckbox)
		mainButtonsBox.addStretch(1)
		mainButtonsBox.addWidget(dialog.okBtn)
		mainButtonsBox.addWidget(dialog.cancelBtn)

		mainBox.addLayout(mainButtonsBox)

	def keyPressEvent(dialog, keyEvent):
		if keyEvent.key() == Qt.Key.Key_Escape:
			dialog.cancelBtn.setFocus()

		# I've set it here that anytime the user presses the CTRL or SHIFT keys, the list box is brought to focus.
		# Witout this, Ctrl+A won't always select all the items in the list.
		# This means that any CTRL+A usages will work regardless of whether the user has already selected the box or not!
		# Same for Shift+Up and Shift+Down.
		elif keyEvent.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift): dialog.selectionBox.setFocus()

		# Pressing Backspace or Delete activates the removeDir() function!
		elif keyEvent.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace): dialog.removeDir()
		else: super().keyPressEvent(keyEvent)

	def dirDialog(dialog, dirType, *primaryDB):

		# The directory will always default to the last one the user selected.
		# If the user has yet to choose any directories, the default Firefox Profiles' directory is used!
		lastSelectedDir = g.combinerConfig.get('GUI', 'Folders - Last selected directory')
		if   dialog.primaryDBFolder == Path.home().joinpath('AppData\\Roaming\\Mozilla\\Firefox\\Profiles'): startingDir = dialog.primaryDBFolder
		elif dirType == 'Add': startingDir = lastSelectedDir
		elif dirType == 'Modify':
			if primaryDB: startingDir = dialog.primaryDBFolder
			elif not primaryDB:
				selectedRows = dialog.selectionBox.selectionModel().selectedRows()
				startingDir = dialog.selectionBox.item(selectedRows[0].row()).text()

		if primaryDB: title = 'Where is the Primary DB located?'
		elif not primaryDB: title = 'Where are the other DBs located?'

		dir_ = QtW.QFileDialog.getExistingDirectory(None, title, str(startingDir))
		dir_ = dir_.replace('/', '\\')

		if primaryDB: dir_ = dialog.processFolders(dir_ = dir_, dirType = dirType, primaryDB = primaryDB)
		elif not primaryDB: dir_ = dialog.processFolders(dir_ = dir_, dirType = dirType)

		return dir_

	def processFolders(dialog, **args):
		dir_ = args.get('dir_')
		dirType = args.get('dirType')
		primaryDB = args.get('primaryDB')

		message = ['', 'Please select a different folder.']
		forbiddenFolderName = ''
		title = ''
		height = 0
		width = 0

		if primaryDB:
			if dir_ in dialog.dbFolders:
				message = ['This folder is already in <b><i>Other DB folders</i></b>. The Primary DB must be in a separate folder.']
				forbiddenFolderName = dialog.dbFolders
				title = 'Primary DB folder'
				width = 10

			elif Path(dir_).joinpath('places.sqlite').is_file() == False:
				message = ['The <b><i>places.sqlite</i></b> file is either missing, or its name is incorrect.',
						   '',
						   'Please either:',
						   '     - Copy the <b><i>places.sqlite</i></b> (and <b><i>favicons.sqlite</i></b> if relevant) into the folder',
						   '     - Appropriately rename the files, or',
						   '     - Select a different folder']

				forbiddenFolderName = dir_
				title = 'places.sqlite file is missing or incorrrectly named'

			elif dir_ == str(Path.cwd()):
				message.insert(0, 'The programs\'s root directory (i.e. the place that <i>Firefox history combiner.exe</i> is located)')
				message.insert(1, 'is reserved for internal functions and cannot be used as the <b>Primary DB folder</b>.')
				forbiddenFolderName = dir_
				title = 'Root directory cannot be used'
				width = -20


		elif not primaryDB:
			if dir_ in dialog.dbFolders and dirType == 'Add': # Doesn't matter if the user modifies an entry to be the same.
				message.insert(0, 'The folder you\'ve selected is already in this list.')
				forbiddenFolderName = dialog.dbFolders
				title = 'Duplicate entry'
				width = -10

			elif dir_ == dialog.primaryDBFolder:
				message.insert(0, 'This folder is the <b>Primary DB folder</b> location.')
				message.insert(1, 'This cannot be used for any other purpose.')
				forbiddenFolderName = dialog.primaryDBFolder
				title = 'Primary DB folder'
				width = 35

			elif dir_ == str(Path.cwd()):
				message.insert(0, 'The programs\'s root directory (i.e. the place that <i>Firefox history combiner.exe</i> is located)')
				message.insert(1, 'is reserved for internal functions and cannot be used.')
				forbiddenFolderName = dir_
				title = 'Root directory cannot be used'
				width = 25

			elif dialog.primaryDBFolder in dir_:
				message.insert(0, 'This is a subsidiary of the <b>Primary DB folder</b>.')
				forbiddenFolderName = dialog.primaryDBFolder
				title = 'Subsidiary of Primary DB folder'
				width = 10

			elif checkFolderHasDBs(Path(dir_)) == False: pass

		# Process forbidden folders
		if forbiddenFolderName != '':
			if dir_ in forbiddenFolderName or forbiddenFolderName in dir_:
				duplicateDialog = createWarning_InfoDialog(title, message, 'OK', 'Warning')
				duplicateDialog.width += width
				duplicateDialog.height += height
				duplicateDialog.exec()

				if primaryDB: dir_ = dialog.dirDialog(dirType, primaryDB)
				elif not primaryDB: dir_ = dialog.dirDialog(dirType)

		return dir_

	def addDir(dialog):
		dir_ = dialog.dirDialog('Add')

		# Clear the selection and focus the OK button (these are not done automatically).
		selectedRows = dialog.selectionBox.selectionModel().selectedRows()
		if len(selectedRows) > 0: dialog.selectionBox.clearSelection()
		
		dialog.okBtn.setFocus()
		
		if dir_ == '': return # If the user hits 'Cancel', exit the folder-picker dialog.

		dialog.dbFolders.append(dir_)
		dialog.fillSelectionBox()

		g.combinerConfig.set('History Combiner', 'DB folders', str(dialog.dbFolders))
		g.combinerConfig.set('GUI', 'Folders - Last selected directory', dir_)

	def modifyDir(dialog):
		selectedRows = dialog.selectionBox.selectionModel().selectedRows()
		if len(selectedRows) == 1:
			if selectedRows[0].row() == 3: dir_ = dialog.dirDialog('Modify', True)
			else: dir_ = dialog.dirDialog('Modify')

			# Clear the selection and focus the OK button (not done automatically).
			dialog.selectionBox.clearSelection()
			dialog.okBtn.setFocus()

			if dir_ == '': return # If the user hits 'Cancel', exit the folder-picker dialog.

			item = dialog.selectionBox.item(selectedRows[0].row())
			oldText = item.text()
			item.setText(dir_)

			g.combinerConfig.set('GUI', 'Folders - Last selected directory', dir_)

			if selectedRows[0].row() == 3:
				dialog.primaryDBFolder = item.text()
				g.combinerConfig.set('History Combiner', 'Primary DB folder', dialog.primaryDBFolder)

			elif selectedRows[0].row() > 6:
				oldFolderIndex = dialog.dbFolders.index(oldText)
				del dialog.dbFolders[oldFolderIndex]
				dialog.dbFolders.insert(oldFolderIndex, dir_)

				g.combinerConfig.set('History Combiner', 'DB folders', str(dialog.dbFolders))

	def removeDir(dialog):
		selectedRows = dialog.selectionBox.selectionModel().selectedRows() # Yields all the selected rows' numbers rather than their contents.
		for row in selectedRows:
			row = row.row()
			if row in (list(range(7))): continue # Don't remove titles, separators or spacers.

			item = dialog.selectionBox.takeItem(row)
			if item is None: 
				# If selecting multiple entries with Shift+Up/Down or Ctrl+A the index goes too high and so 'item' returns None. No idea why.
				item = dialog.selectionBox.takeItem(row - 1)

			itemIndex = dialog.dbFolders.index(item.text())
			del dialog.dbFolders[itemIndex]
			del item

		g.combinerConfig.set('History Combiner', 'DB folders', str(dialog.dbFolders))
		dialog.selectionBox.clearSelection()
		dialog.okBtn.setFocus()

	def checkOK(dialog):
		message = None
		defaultPrimaryPath = str(Path.home().joinpath('AppData\\Roaming\\Mozilla\\Firefox\\Profiles'))
		tooltip = ''
		width = 0

		if len(dialog.dbFolders) == 0 and dialog.primaryDBFolder != defaultPrimaryPath:
			title = 'Add DB folders'
			message = ['You must add at least <b>1 folder</b> containing 1 or more DBs.',
					   '',
					   'These can be Firefox Profiles (i.e. from \\AppData\\Roaming\\Mozilla\\Firefox\\Profiles)',
					   'or a folder of your choosing that has multiple DBs inside.']

		elif len(dialog.dbFolders) > 0 and  dialog.primaryDBFolder == defaultPrimaryPath:
			title = 'Choose different folder'
			message = ['You must choose a new location for the <b><i>Primary DB folder.</b></i>',
					   'This should be the location of the backup you made of your original DB.']

		elif len(dialog.dbFolders) == 0 and dialog.primaryDBFolder == defaultPrimaryPath:
			title = 'Add more folders and new Primary DB folder'
			message = ['You must add at least <b>one folder</b> containing one or more DBs.',
					   '',
					   'In addition, you must choose a new location for the <b><i>Primary DB folder.</b></i>']

			width = 12


		if message is not None:
			newDirsDialog = createWarning_InfoDialog(title, message, 'OK', 'Info')
			newDirsDialog.messageLabel.setToolTip(tooltip)
			newDirsDialog.width += width
			newDirsDialog.heightComp = 60
			newDirsDialog.exec()
			return

		option = 'Number DBs' # For 'Don't show this again' message
		show = False
		# if g.combinerConfig.getint('Reminder dialogs', option) == 0: # If 'Don't show this again' is unchecked, show it!
		if show == True: # Disabling this for now.
			message = \
			('Just a small reminder that if you\'re combining multiple places.sqlite and favicons.sqlite files from the same folder',
			 '(i.e. DBs from FF 55.0 and newer), you must rename them to include numbers.',
			 '',
			 'Convention (\'places (1).sqlite\', \'places_1.sqlite\' etc.) doesn\'t matter here; But the numbering must be added to the end of the file name, as shown above.',
			 'However, the convention (and the numbers) must match up between the places.sqlite and favicons.sqlite files. Combining won\'t work otherwise!',
			 'Pre FF 55.0 DBs can be named whatever you like because they have no accompanying favicons.sqlite files.',
			 '',
			 'Hint: You can have both types (pre and post FF 55.0 DBs) in the same folder :)',
			 'Hint 2: Obviously this reminder doesn\'t apply to DBs taken from actual Profiles (i.e. AppData\\Mozilla\\Firefox\\Profiles)')
			
			numberDBsDialog = createWarning_InfoDialog('Have you numbered the DBs?', message, 'OK', 'Info', option)
			numberDBsDialog.exec()

		dialog.combineBtn.setEnabled(True)        
		confirmChanges(dialog = dialog)

	def cancelKeyRelease(dialog, keyEvent):
		if keyEvent.key() == Qt.Key.Key_Escape: dialog.cancelBtn.click()
		else: super(QtW.QPushButton, dialog.cancelBtn).keyReleaseEvent(keyEvent)

	def selectionBoxEnterPressed(dialog, keyEvent):
		if keyEvent.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
			selectedRows = len(dialog.selectionBox.selectionModel().selectedRows())
			if selectedRows == 0 or selectedRows > 1: dialog.okBtn.click() # If 0 rows or more than 1 row is selected, close the window and save changes.
			elif selectedRows == 1: dialog.modifyDir() # If 1 row is selected, pressing Enter modifies that directory!!

		else: super(QtW.QListWidget, dialog.selectionBox).keyPressEvent(keyEvent)

	def fillSelectionBox(dialog):
		def fillLoop(titlesSeparators, sepPos, sizePos, titlePos_Size):
			dialog.selectionBox.addItems(titlesSeparators)

			separator = QtW.QFrame()
			separator.setFrameShape(QtW.QFrame.Shape.HLine)
			dialog.selectionBox.setItemWidget(dialog.selectionBox.item(sepPos), separator)

			dialog.selectionBox.item(sizePos[0]).setSizeHint(QSize(1, 19)) # Title
			dialog.selectionBox.item(sizePos[1]).setSizeHint(QSize(1, 1)) # Separator
			dialog.selectionBox.item(sizePos[2]).setSizeHint(QSize(1, 4)) # Spacer

			title = dialog.selectionBox.item(titlePos_Size[0])
			title.setFont(titleFont)
			title.setSizeHint(QSize(1, titlePos_Size[1]))
			title.setTextAlignment(Qt.AlignmentFlag.AlignBottom)

			
		dialog.selectionBox.clear()

		# Disable hover highlighting on disabled items. Also set text colour to black as disabling items turns them grey.
		dialog.selectionBox.setStyleSheet('QListWidget::item:disabled {background: transparent; color: black}')


		# Can't use a stylesheet for font adjustments on QListWidetItems. Not for size or weight anyway.
		titleFont = QFont()
		titleFont.setBold(True)
		titleFont.setPointSize(10)

		fillLoop(['                           Primary DB folder', '', '',  dialog.primaryDBFolder],  1, [0, 1, 2], [0, 25])
		fillLoop(['                            Other DB folders', '', '', *dialog.dbFolders], 5, [4, 5, 6], [4, 30])


		# Disable titles and separators, not invisible but not enabled!
		for i in range(7):
			if i != 3:
				dialog.selectionBox.item(i).setFlags(dialog.selectionBox.item(i).flags() & ~Qt.ItemFlag.ItemIsEnabled)
		
		# for i in range(8, dialog.selectionBox.count()): dialog.selectionBox.item(i).setSizeHint(QSize(1, 19))
		# dialog.selectionBox.setAutoScroll(True)

	def exec(dialog):
		# dialog.recursiveCheckbox.resetState() # It incorrectly displays otherwise.
		dialog.dbFolders = ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders'))
		dialog.primaryDBFolder = g.combinerConfig.get('History Combiner', 'Primary DB folder')
		dialog.fillSelectionBox()

		# If the option is checked, resize the dialog to width
		if g.combinerConfig.get('GUI', 'Auto-size folder dialog width') == 'Checked':
			# Get a list of all displays (just to be thorough)
			widthList = []
			for displayNum in QGuiApplication.screens():
				widthList.append(displayNum.geometry().width())

			# Find the smallest width
			minWidth = min(widthList)

			# sizeHintForColumn() gets the maximum width of all the rows for the given column.
			# 140 is the constant. The gap between the right-hand edge of the selection box and the window's right-hand edge.
			newWidth = dialog.selectionBox.sizeHintForColumn(0) + 140

			# Make sure the new width never exceeds the width of the smallest connected display.
			if newWidth > minWidth: newWidth = minWidth
			
			dialog.resize(newWidth, dialog.minHeight)


		elif g.combinerConfig.get('GUI', 'Auto-size folder dialog width') == 'Unchecked':
			dialog.resize(450, dialog.minHeight)

		super().exec()