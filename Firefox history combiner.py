from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMainWindow
from configparser import ConfigParser
from pathlib import Path

from programFiles.otherFunctions import removeOrphanedSqliteFiles, removeTempFiles
from programFiles.guiClasses.warning_info import createWarning_InfoDialog
from programFiles.guiClasses.mainWidget import createMainWidget
from programFiles.guiClasses.misc import confirmChanges

import programFiles.globalVars as g
import logging, ast


class createMainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		# Support for different size screens??? Resize widgets and text to accommodate??

		self.setFixedSize(450, 250)
		self.setWindowTitle('Firefox History Combiner')

		# So that the DB folder selection dialog doesn't totally hide the main window when it's opened. Aesthetics, but it's important to me.
		screen = QDesktopWidget().screenGeometry()
		win = self.geometry()
		x = int((screen.width() /2) - (win.width() /2))
		y = int((screen.height() /2) - (win.height() /2) -70)

		self.move(x, y)


def cleanupProcessStuff():
	# Make a local copy of combinerConfig. This ensures thread safety.
	# Calling confirmChanges() here meant reading and writing to Settings.ini at the same time from 2 different threads.
	# Which resulted in glitches.
	combinerConfig = ConfigParser()
	combinerConfig.read_file(open('Settings.ini'))
	combinerConfig.set('GUI', 'Stop pressed', '1')
	with open('Settings.ini', 'w') as settingsFile: combinerConfig.write(settingsFile)
	
	# Only quit combining Thread if it's actually running.
	try:
		mainWidget.combinerThread.quit()
		mainWidget.combinerThread.wait()

		# Restore backup if thread was running???

	except:
		pass


removeTempFiles() # Remove any lingering temp files caused by crashes, bluescreens etc. It takes like 70MB per folder!!!
removeOrphanedSqliteFiles() # Same for orphaned files
g.combinerConfig.set('GUI', 'Stop pressed', '0') # Reset "Stop pressed" state
confirmChanges()


combinerLogger = logging.getLogger('Combiner')
combinerLogger.addHandler(logging.FileHandler('Combiner.log'))

# Set logging level based on settings.ini
loggerLevel = g.combinerConfig.getint('Debugging', 'Debug level')
combinerLogger.setLevel(loggerLevel)


app = QApplication([])
mainWindow = createMainWindow()
mainWidget = createMainWidget()
mainWindow.setCentralWidget(mainWidget)

# Create the 'Completed DBs' directory if not already present.
if Path.cwd().joinpath('Completed DBs').is_dir() == False: Path.cwd().joinpath('Completed DBs').mkdir()

frecencyLink = 'https://developer.mozilla.org/en-US/docs/Mozilla/Tech/Places/Frecency_algorithm'
message = ['Welcome to Firefox History Combiner!',
		   '',
		   'This tool allows you to combine as many Firefox history databases as you want into a single DB.',
		   'Before doing anything else, make a backup of your original DB!!! <b>Very important.</b> Put this anywhere you choose.',
		   '',
		   'After you press <b><i>OK</i></b>, the folder selection window will open.',
		   'You must add a minimum of <b>one folder</b> (containing one or more DBs for combining) before closing that window.',
		   'In addition, the <b><i>Primary DB location</b></i> must contain the backup of your original DB (mentioned above).',
		   '',
		   'Various aspects of your history data can be selected for combining, including Frecency! Open <b><i>Settings</b></i> for this.',
		   'There are also options for hiding dialog reminders, creating backups, and other miscellaneous things.',
		   '',
		   f'<a href="{frecencyLink}">Click here</a> for a more in-depth explanation of what Frecency is and how it works.',
		   '']

# welcomeDialog.messageLabel.setToolTip(frecencyLink)
welcomeDialog = createWarning_InfoDialog('Welcome', message, 'OK', 'Info', 'Welcome')

# No DB folders means it's the program's first run. Therefore show the DB folder selection dialog.
dbFoldersLen = len(ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders')))

if dbFoldersLen == 0:
	welcomeDialog.finished.connect(mainWindow.show)
	welcomeDialog.finished.connect(mainWidget.dbSelectionDialog.exec_)
	welcomeDialog.width += 12

	# On first run, disable the combine button until the user has selected appropriate folders!
	# This also handles the unlikely scenario of the user cancelling the folder selection dialog on said first run (meaning there are no DBs to combine).
	# In this case, the combine button remains disabled until folders have been selected.
	mainWidget.combineBtn.setEnabled(False)


# Modify the welcome message slightly depending on whether it's the first run or not.
elif dbFoldersLen > 0:
	message[0] = message[0].replace('Welcome to', 'Welcome back to')
	message[2] = message[2].replace('This tool', 'As you know, this tool')
	message[3] = 'Don\'t forget to make a backup of your main DB! Put this anywhere you choose.'

	del message[4:8]

	welcomeDialog.setDialogDims(message)
	welcomeDialog.width += 20
	welcomeDialog.finished.connect(mainWindow.show)


# If the option is unchecked, display the welcome message
if g.combinerConfig.getint('Reminder dialogs', 'Welcome') == 0:
	welcomeDialog.exec_()

# Otherwise just display the main window
elif g.combinerConfig.getint('Reminder dialogs', 'Welcome') == 2:
	mainWindow.show()


app.aboutToQuit.connect(cleanupProcessStuff)
app.exec_()