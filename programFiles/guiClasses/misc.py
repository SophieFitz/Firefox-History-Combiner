from pathlib import Path

import sqlite3
import programFiles.globalVars as g


def confirmChanges(**args):
	dialog = args.get('dialog')

	with open('Settings.ini', 'w') as settingsFile: g.combinerConfig.write(settingsFile)
	if dialog: dialog.accept()

	g.combinerConfig.read_file(open('Settings.ini')) # Read the new version of the file
	g.primaryDBFolder = Path(g.combinerConfig.get('History Combiner', 'Primary DB folder')) # Get most up-to-date version of g.primaryDBFolder.
	# dialog.done(dialog.Accepted)

def cancelChanges(**args):
	dialog = args.get('dialog')

	g.combinerConfig.read_file(open('Settings.ini')) # Open the old version of the file
	if dialog: dialog.reject()
	# dialog.done(dialog.Rejected)

def checkStopPressed():
	g.combinerConfig.read_file(open('Settings.ini'))
	if g.combinerConfig.getint("GUI", "Stop pressed") == 1: raise g.combiningStopped()