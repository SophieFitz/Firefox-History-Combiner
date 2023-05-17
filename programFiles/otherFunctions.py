from pathlib import Path

import ast, sqlite3
import programFiles.globalVars as g


def checkDBExists(dbPath):
	db = sqlite3.connect(dbPath)
	cur = db.cursor()

	tables = cur.execute('SELECT sql from sqlite_master').fetchall()
	cur.connection.commit()
	cur.close()

	if len(tables) > 0: return True
	else:				return False


def checkFolderHasDBs(dbFolder):
	numDBs = len([db for db in dbFolder.glob('*.sqlite')])
	if numDBs == 0: return False
	elif numDBs > 0: return True


def removeOrphanedSqliteFiles():
	pathNames = {}
	exts = ['sqlite-wal', 'sqlite-shm']
	allDBFolders = ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders'))
	allDBFolders.append(g.primaryDBFolder)
	allDBFolders.append(Path.cwd())
	for folder in allDBFolders:
		folder = Path(folder)
		foldersToIgnore = {}

		for path in folder.rglob('*'):
			if path.name == 'prefs.js': foldersToIgnore.update({path.parent: ''})

	for folder in allDBFolders:
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
		# nowInSecs = time.time()
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
	if g.combinerConfig.get('Misc', 'Delete crashed py-installer files') == 'Checked':
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