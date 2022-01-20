from pathlib import Path
from datetime import datetime

import ast, sqlite3, time
import programFiles.globalVars as g

from programFiles.guiClasses.misc import confirmChanges
from programFiles.combinerFunctions.Supplementary.sqlFunctions import checkPre55


def faviconsFiles(stage):
	# Create lists of DBs to extract history data from!
	allDBsPre55 = []
	allDBsPost55 = []

	missingIconsList = []

	isProfile = False
	allDBFoldersGet = ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders'))

	for folder in allDBFoldersGet.keys():
		folder = Path(folder)

		for path in folder.iterdir():
			if path.name == 'prefs.js': isProfile = True

		if folder == g.primaryDBFolder: continue # Don't combine the Primary DB into itself! Waste of time.

		if isProfile == True:
			placesDB = [db for db in folder.iterdir() if db.name == 'places.sqlite']
			faviconsDB = [db for db in folder.iterdir() if db.name == 'favicons.sqlite']
			if len(faviconsDB) == 1: allDBsPre55.extend([faviconsDB[0], placesDB[0]]) # Have to reverse these as for some reason, faviconsDB becomes None otherwise
			elif len(faviconsDB) == 0: allDBsPre55.append(placesDB[0])
			
		elif isProfile == False:
			# recursive = g.combinerConfig.getint('History Combiner', 'Recursive')
			
			# if recursive == 0: folderDBs = [db for db in folder.glob('*.sqlite')]
			# elif recursive == 2: folderDBs = [db for db in folder.rglob('*.sqlite')] # rglob is recursive glob.

			folderDBs = [db for db in folder.rglob('*.sqlite')] # rglob is recursive glob. Might as well look in all subfolders.
			allDBsPre55.extend(folderDBs)
			

	# All DBs are initially assumed to be pre FF 55. This loop transfers those that aren't into 'allDBsPost55'.
	for db in allDBsPre55:
		if db.name.startswith('places'):
			dbCon = sqlite3.connect(db)
			dbCur = dbCon.cursor()
			dbPre55 = checkPre55(dbCur, 'main')

			# Only check for favicons.sqlite if places.sqlite is definitely above FF 55. 
			if dbPre55 == False:
				allDBsPost55.append(db)

				# Can't remove yet as it messes up the indeces of 'allDBsPre55', which is currently being looped over! 
				# Therefore, set to None and remove later.
				allDBsPre55[allDBsPre55.index(db)] = None
				
				dbNumberSuffix = db.name.split('places')[1]
				db2 = db.parent.joinpath(f'favicons{dbNumberSuffix}')

				# Finally, look for its reciprocal favicons.sqlite DB.
				if db2 in allDBsPre55:
					# Can't remove yet as it messes up the indeces of 'allDBsPre55', which is currently being looped over! 
					# Therefore, set to None and remove later.
					allDBsPre55[allDBsPre55.index(db2)] = None

				elif db2 not in allDBsPre55:
					# Re-order so that favicons.sqlite is always first, rather than last.
					if db2.name == 'favicons.sqlite': missingIconsList.insert(0, db)
					else: missingIconsList.append(db)

			dbCon.commit()
			dbCur.close()

	if stage == 'Check':
		curMain = sqlite3.connect(g.primaryDBFolder.joinpath('places.sqlite')).cursor() # DB is presumed to have the name 'places.sqlite'.
		mainPre55 = checkPre55(curMain, 'main')
		mainIconsMissing = None

		if mainPre55 == False:
			hasFavicons = g.primaryDBFolder.joinpath('favicons.sqlite').is_file()
			if hasFavicons == False:
				mainIconsMissing = g.primaryDBFolder.joinpath('places.sqlite')

		curMain.connection.commit()
		curMain.close()

		return (mainIconsMissing, missingIconsList)

	elif stage == 'Combine':
		# Finish removal of DBs that are above FF 55 whose values have already been transferred to the reciprocal 'allDBsPost55' list.
		allDBsPre55 = [db for db in allDBsPre55 if db is not None]
		return (allDBsPre55, allDBsPost55)
		

def originsGetPrefixHost(url):
	if url.find('://') != -1: partTwo = '://'
	elif url.find(':') != -1: partTwo = ':'

	(prefix, domain) = url.split(partTwo)[0:2]
	prefix += partTwo

	domain = domain.split('/')[0]
	if any(remPrefix in prefix for remPrefix in ('file', 'mega', 'place', 'javascript')): return (prefix, '')

	return (prefix, domain)


def checkDBExists(dbPath):
	db = sqlite3.connect(dbPath)
	cur = db.cursor()

	tables = cur.execute('SELECT sql from sqlite_master').fetchall()
	cur.connection.commit()
	cur.close()

	if len(tables) > 0: return True
	else:				return False


def removeOrphanedSqliteFiles():
	pathNames = {}
	exts = ['sqlite-wal', 'sqlite-shm']
	allDBFoldersGet = ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders'))
	allDBFoldersGet.update({g.primaryDBFolder: ''})
	allDBFoldersGet.update({Path.cwd(): ''})
	for folder in allDBFoldersGet.keys():
		folder = Path(folder)
		foldersToIgnore = {}

		for path in folder.rglob('*'):
			if path.name == 'prefs.js': foldersToIgnore.update({path.parent: ''})

	for folder in allDBFoldersGet.keys():
		folder = Path(folder)

		for ext in exts:
			for path in folder.rglob(f'*.{ext}'):
				ignore = False
				for folIgnore in foldersToIgnore.keys():
					if str(folIgnore) in str(path): ignore = True

				if ignore == True: continue # Don't remove orphaned sqlite files from Firefox profiles as this could have unintended consequences...
				pathNames.update({path: ''})

	# if g.primaryDBFolder not in foldersToIgnore.keys(): # Also don't remove files if current folder is main DB profile
	# 	for ext in exts: pathNames.update({path: '' for path in Path(g.primaryDBFolder).glob(f'*.{ext}')})

	for path in pathNames.keys():
		# print(path)
		nowInSecs = time.time()
		# while path.is_file() == True:
			# print(int(time.time() - nowInSecs))
			# if time.time() - nowInSecs >= 2: break # If any file is taking too long, skip it.
		try: path.unlink()
		except: pass


def removeFiles_Dirs(path, pathType):
	if pathType == 'file':
		while path.is_file() == True:
			try: path.unlink()
			except: pass

	elif pathType == 'folder':
		while path.is_dir() == True:
			try: path.rmdir()
			except: pass

def removeTempFiles():
	# Only delete the files if the option is checked.
	if g.combinerConfig.getint('Misc', 'Delete crashed py-installer files') == 2:
		tempDirGen = Path.home().joinpath(r'AppData\Local\Temp').glob('_MEI*')
		tempDirs = [tempDir for tempDir in tempDirGen]
		cTimes = [tempDir.stat().st_ctime for tempDir in tempDirs]

		for tempDir in tempDirs:
			if tempDir.stat().st_ctime == max(cTimes): continue # Miss out the current _MEI directory

			pathNames = [path for path in tempDir.rglob('*')]
			pathNames.reverse()

			for path in pathNames:
				if path.is_file() == True: removeFiles_Dirs(path, 'file')
				elif path.is_dir() == True: removeFiles_Dirs(path, 'folder')

			removeFiles_Dirs(tempDir, 'folder')