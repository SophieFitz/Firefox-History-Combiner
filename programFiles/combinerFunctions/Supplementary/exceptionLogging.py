from programFiles.combinerFunctions.Supplementary.otherFunctions import faviconsFiles
from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries
from copy import deepcopy
from pathlib import Path

import logging, sqlite3
import programFiles.globalVars as g


def insertExceptionLog(items, checkState):
	def stripPersonalInfo(row):
		# Always remove the favicon data as certain characters can't be displayed in the error dialog.
		if table == 'moz_favicons': row[2] = 'data'
		elif table == 'moz_icons': row[7] = 'data'

		if checkState == 0:
			if   table == 'moz_favicons':      row[1] = 'url'
			elif table == 'moz_icons':         row[1] = 'icon_url'
			elif table == 'moz_pages_w_icons': row[1] = 'page_url'
			elif table == 'moz_hosts':         row[1] = 'host'
			elif table == 'moz_origins':       row[2] = 'host'

			elif table == 'moz_places':
				row[1] = 'url'; row[2] = 'title'; row[3] = 'rev_host'

				if   type(row[9]) is str: index = 12
				elif type(row[9]) is int: index = 13

				if   len(row) >= index + 1: row[index] = 'description'; row[index + 1] = 'preview_image_url'
				elif len(row) == index:   row[index] = 'description'
			
			elif table == 'moz_annos':
				insAttDownloadUriPropID = items.get('insAttDownloadUriPropID')
				if row[2] == insAttDownloadUriPropID: row[4] = 'content' # Only purge personal info if it's the download filename.

			elif table == 'moz_bookmarks':    row[5] = 'title'
			elif table == 'moz_items_annos':  row[4] = 'content'
			elif table == 'moz_inputhistory': row[1] = 'input' # Maybe exempt this one as this column forms half of the Primary Key.
			elif table == 'moz_keywords':     row[1] = 'keyword'

		# Return row regardless, but without personal info if the option is unchecked.
		return row
	
	errorTrace = items.get('errorTrace')
	mainDBName = items.get('mainDBName')
	dbExtPath = items.get('dbExtPath')
	newRow = items.get('new')

	# Have to connect to DBs again as the Cursor instance can't be shared across threads
	dbMain = sqlite3.connect(Path.cwd().joinpath('places.sqlite'))
	dbMain.row_factory = sqlite3.Row
	curMain = dbMain.cursor()

	sql = f'attach "{Path.cwd().joinpath("favicons.sqlite")}" as mainIcons'
	curMain.execute(sql)
	

	errorMessage = (f'Database: {dbExtPath}'
				     ''
				     ''
					f'\n\n{errorTrace}')

	table = errorTrace.__str__().split()[-1].split('.')[0]
	schemaSQL = f'SELECT * from {mainDBName}.{table}'
	schema = curMain.execute(schemaSQL).fetchone().keys()

	numUnique = errorTrace.__str__().count('.')
	conflictSQL = f'SELECT * from {mainDBName}.{table} where '

	if numUnique == 1:
		paramNames = [errorTrace.__str__().split('.')[1]]
		paramValues = (newRow[schema.index(paramNames[0])],)
		conflictSQL = f'{conflictSQL} {paramNames[0]} = ?'

	elif numUnique == 2:
		errorSplit = errorTrace.__str__().split('.')
		paramNames = [errorSplit[1].split(',')[0], errorSplit[-1]]

		paramValues = (newRow[schema.index(paramNames[0])], newRow[schema.index(paramNames[1])])
		conflictSQL = f'{conflictSQL} {paramNames[0]} = ? and {paramNames[1]} = ?'


	sql = f'SELECT * from {mainDBName}.{table}'

	if table != 'moz_inputhistory':
		oldEntryPK = newRow[0]
		oldEntries = getAllEntries(cur = curMain, SQL = sql, dictSchema = 'entry[0]: list(entry)')
		
	elif table == 'moz_inputhistory':
		oldEntryPK = newRow[:2]
		oldEntries = getAllEntries(cur = curMain, SQL = sql, dictSchema = '(entry[0], entry[1]): list(entry)')

	conflict = list(curMain.execute(conflictSQL, paramValues).fetchone())

	conflictsBefore = {}
	for primaryKey in list(oldEntries):
		if primaryKey == oldEntryPK: break
		conflictsBefore.update({primaryKey: oldEntries[primaryKey]})


	errorMessage += (''
					 ''
					 ''
					f'\n\n\nTable: {table}'
					f'\nSchema: {schema}'
					 ''
					f'\n\nThe error occurred when inserting this item:'
					f'\n{stripPersonalInfo(deepcopy(newRow))}'
					 ''
					f'\n\nConflicting with this item:'
					f'\n{stripPersonalInfo(conflict)}'
					 ''
					 ''
					 ''
					f'\n\n\nNum entries before conflict: {len(conflictsBefore)}'
					f'\nNum entries after conflict: {len(oldEntries) - len(conflictsBefore)-1}\n'
					 '')

	curMain.connection.commit()
	return errorMessage


def dictExceptionLog(items, checkState):
	errorMessage = items.get('errorMessage')
	frameInfo = items.get('frameInfo')
	dbExtPath = items.get('dbExtPath')

	if checkState == 0:
		errorSplit = errorMessage.split('      ')
		for i in range(1, len(errorSplit)): # Ignore first value as it's purely descriptive
			value = errorSplit[i]
			if 'url' in value.lower() or 'host' in value.lower():
				valueSplit = value.split(' = ')
				valueSplit[1] = f'{valueSplit[0]}\n      '
				valueSplit[0] += ' = '

				errorSplit[i] = ''
				for data in valueSplit: errorSplit[i] += data

		errorMessage = ''
		errorSplit[0] += '      '
		for data in errorSplit: errorMessage += data


	# See: https://stackoverflow.com/questions/3056048/filename-and-line-number-of-python-script
	# This adds the file name and corresponding line number of the error (-2 for the actual line in question, rather than the frameinfo() call).
	errorMessage = (f'Database: {dbExtPath}\n\n'
					''
					f'File: "{frameInfo.filename}"\n'
					f'Line: "{frameInfo.lineno - 2}"\n\n'
					 ''
					f'{errorMessage}')

	return errorMessage


def generalExceptionLog(errorMessage):
	# If the exception type is more of a general error (i.e. I have no idea what caused it), I want as much information as possible in the logfile. 
	# In that vein, this function adds the table schemas for all connected DBs to the logfile.

	def logDBSchema(cur, dbName, dbPath, errorMessage):
		sql = f'SELECT name from {dbName}.sqlite_master where type = ?'
		try: tablesGet = cur.execute(sql, ('table',)).fetchall()
		except sqlite3.OperationalError: return errorMessage


		tables = [name[0] for name in tablesGet]
		errorMessage += f'\n\n\nDB name: "{dbName}"\nDB path: "{dbPath}"\n\nTable schemas:'

		for table in tables:
			sql = f'pragma {dbName}.table_info({table})'
			colsGet = cur.execute(sql).fetchall()
			colNames = [col[1] for col in colsGet]
			colNums = '['
			for col in colsGet:
				if col[0] <= 9: spaces = len(col[1]) + 1
				elif col[0] > 9: spaces = len(col[1])

				if col[0] < len(colsGet) -1:
					colNums += str(col[0]) + ', ' + (' ' * spaces)

				elif col[0] == len(colsGet) -1:
					colNums += str(col[0]) + (' ' * spaces) + ']'			

			errorMessage += f'\n{table}\n{colNums}\n{colNames}\n'

		return errorMessage


	dbNames = {'main': g.primaryDBFolder.joinpath('places.sqlite'), 'mainIcons': '', 'dbExt': '', 'extIcons': ''}

	dbCon = sqlite3.connect(dbNames['main'])
	cur = dbCon.cursor()

	mainFaviconsPath = g.primaryDBFolder.joinpath('favicons.sqlite')
	if mainFaviconsPath.is_file() == True:
		sql = f'attach "{mainFaviconsPath}" as mainIcons'
		dbNames['mainIcons'] = mainFaviconsPath
		cur.execute(sql)


	allDBsPre55, allDBsPost55 = faviconsFiles('Combine')
	finishedDBs = []

	with open('Combiner.log', 'r') as logFile:
		allLines = logFile.readlines()

		lineNum = 0
		for line in reversed(allLines):
			if 'Completed:' in line: break
			lineNum += 1

		dbLines = allLines[(len(allLines) -1) - lineNum:]

		for line in dbLines:
			if line not in ('\n', 'Completed:\n'):
				line = line[:-1] # Remove trailing \n
				finishedDBs.append(Path(line))

			elif line == '\n': break


	for db in finishedDBs:
		if db in allDBsPre55: allDBsPre55.remove(db)
		elif db in allDBsPost55: allDBsPost55.remove(db)

	if len(allDBsPre55) > 0:
		sql = f'attach "{allDBsPre55[0]}" as dbExt'
		dbNames['dbExt'] = allDBsPre55[0]
		cur.execute(sql)

	elif len(allDBsPost55) > 0:
		dbExtPath = allDBsPost55[0]

		sql = f'attach "{dbExtPath}" as dbExt'
		dbNames['dbExt'] = allDBsPost55[0]
		cur.execute(sql)

		dbNumberSuffix = dbExtPath.name.split('places')[1]
		db2 = dbExtPath.parent.joinpath(f'favicons{dbNumberSuffix}')
		
		# Check if it already exists, otherwise it creates a 0-byte placeholder DB which I don't want.
		if db2.is_file() == True:
			sql = f'attach "{db2}" as extIcons'
			dbNames['extIcons'] = db2
			cur.execute(sql)
			

	for dbName, dbPath in dbNames.items():
		errorMessage = logDBSchema(cur, dbName, dbPath, errorMessage)

	cur.connection.commit()
	cur.close()

	return errorMessage
