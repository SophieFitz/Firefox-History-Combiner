import time, logging, sqlite3
import programFiles.globalVars as g

from pathlib import Path
from datetime import datetime

from programFiles.combinerFunctions.inputKeywords import mozInputHistory, mozKeywords
from programFiles.combinerFunctions.hostsOrigins import mozHosts_Origins
from programFiles.combinerFunctions.placesVisits import mozPlaces
from programFiles.combinerFunctions.bookmarks import mozBookmarks
from programFiles.combinerFunctions.favicons import mozFavicons
from programFiles.combinerFunctions.annos import annotations

from programFiles.combinerFunctions.Supplementary.updateEntries import updateFrecency, updateVisit_foreignCounts, updatePlaceURLHashes, updateIcons_toPages
from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, checkPre55, columnPresent, removeReorderTableColumns
from programFiles.combinerFunctions.Supplementary.getModifyValues import faviconsFiles, allOldEntriesGet
from programFiles.combinerFunctions.Supplementary.createBlankDBs import createBlankFaviconsDB


def combiner():
	def combineTables(dbExtPath, dbExtIcons):
		if dbExtIcons is not None: dbNameStr = f'\n\n{dbExtPath} and {dbExtIcons.name}\n'
		elif dbExtIcons is None: dbNameStr = f'\n\n{dbExtPath}\n'
		print(dbNameStr)

		sql = f'attach "{dbExtPath}" as dbExt'
		curMain.execute(sql)
		dbExtPre55 = checkPre55(curMain, 'dbExt')

		mozFavicons((curMain, dbInsPre55, dbExtPre55))
		mozHosts_Origins(curMain) # Copy moz_origins before moz_places because the latter relies on the IDs of the former.
		mozPlaces((curMain, dbInsPre55, dbExtPre55))

		# Only transfer bookmarks if both DBs are above FF 4.0
		extBookmarksGUID = columnPresent(curMain, 'dbExt', 'moz_bookmarks', 'guid')
		if insBookmarksGUID == True and extBookmarksGUID == True:
			if g.combinerConfig.getint('History Combiner', 'Bookmarks') == 2:
				newBookmarkIDs = mozBookmarks(curMain) # Bookmarks and if checked, Downloads
				annotations(curMain, newBookmarkIDs)

			elif g.combinerConfig.getint('History Combiner', 'Bookmarks') == 0: annotations(curMain, {}) # Downloads, if checked

		else: print('Cannot transfer bookmarks as DB insert and/or DB extract is older than Firefox 4.0')


		if g.combinerConfig.getint('History Combiner', 'Inputhistory') == 2: mozInputHistory(curMain)
		if g.combinerConfig.getint('History Combiner', 'Keywords') == 2: mozKeywords(curMain)
		
		
		if dbExtIcons is None: 
			combinerLogger.info(f'{dbExtPath}')

		elif dbExtIcons is not None:
			combinerLogger.info(f'\n{dbExtPath}\n{dbExtIcons}')
			curMain.execute('detach extIcons')

		curMain.connection.commit()
		curMain.execute('detach dbExt')


	startTime = time.time()

	# Get logger
	now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
	combinerLogger = logging.getLogger('Combiner')
	combinerLogger.info(f'\n\nCombining started at {now}\n\nCompleted:')

	# DB variables set up here.
	allDBsPre55, allDBsPost55 = faviconsFiles('Combine')


	# Transfer contents of main DB into memory. Improves HDD performance drastically (specifically for bookmarks processing).
	dbMainSource = sqlite3.connect(g.primaryDBFolder.joinpath('places.sqlite'))
	dbMain = sqlite3.connect(':memory:')
	dbMainSource.backup(dbMain)
	dbMainSource.close()

	dbMain.row_factory = sqlite3.Row
	curMain = dbMain.cursor()

	g.dbMain = dbMain


	# Frecency settings
	updateFrecSetting = g.combinerConfig.getint('History Combiner', 'Update frecency')
	if updateFrecSetting == 1: oldPlaceGUIDs = getAllEntries(cur = curMain, SQL = 'SELECT guid from main.moz_places', dictSchema = [0, ''])

	# This seems to commit everything properly. Autocheckpoint increment is every 1 entry, instead of 1000.
	# And it's set to Truncate rather than Passive to make sure it all gets properly committed and has exclusive access to do so.
	curMain.execute('pragma wal_autocheckpoint = 1')
	curMain.execute('pragma wal_checkpoint = truncate')
	curMain.connection.commit()

	g.updateProgBar.emit(100)

	dbInsPre55 = checkPre55(curMain, 'main')
	insBookmarksGUID = columnPresent(curMain, 'main', 'moz_bookmarks', 'guid')
	if dbInsPre55 == False:
		mainFaviconsPath = g.primaryDBFolder.joinpath('favicons.sqlite')
		# If main favicons.sqlite is missing, create a new blank one.
		if mainFaviconsPath.is_file() == False:
			createBlankFaviconsDB(Path.cwd().joinpath('favicons.sqlite'), curMain)

		# Attach favicons.sqlite DB to the main connection object as mainIcons
		sql = f'attach "{mainFaviconsPath}" as mainIcons'
		curMain.execute(sql)

		# Remove favicon_id column from DB insert, if present.
		faviconIDPresent = columnPresent(curMain, 'main', 'moz_places', 'favicon_id')
		if faviconIDPresent == True: removeReorderTableColumns(curMain, 'main', 'moz_places', {'remove': ['favicon_id']})

	elif dbInsPre55 == True:
		if insBookmarksGUID == False: print('\nThe main DB must be newer than Firefox 4.0 to transfer bookmarks.\n')


	# Get all old entries so that combining is quicker (rather than getting all the entries repeatedly with every database, which is slow).
	allOldEntriesGet(curMain)

	# Combine DBs that are from below FF 55.0
	for dbExtPath in allDBsPre55: combineTables(dbExtPath, None)

	# Combine DBs that are from FF 55.0 and above
	for dbExtPath in allDBsPost55:
		# dbExtPath = Path(dbExtPath) # Convert to Path
		dbNumberSuffix = dbExtPath.name.split('places')[1]
		db2 = dbExtPath.parent.joinpath(f'favicons{dbNumberSuffix}')
		
		# Check if it already exists, otherwise it creates a 0-byte placeholder DB which I don't want.
		if db2.is_file() == True:
			sql = f'attach "{db2}" as extIcons'
			curMain.execute(sql)

		elif db2.is_file() == False: db2 = None
		combineTables(dbExtPath, db2)


	if updateFrecSetting == 1: updateFrecency(curMain, updateFrecSetting, oldPlaceGUIDs)
	elif updateFrecSetting == 2: updateFrecency(curMain, updateFrecSetting)
	updateIcons_toPages(curMain, dbInsPre55)
	updateVisit_foreignCounts(curMain)
	updatePlaceURLHashes(curMain)


	# 'The VACUUM command may change the ROWIDs of entries in any tables that do not have an explicit INTEGER PRIMARY KEY.'
	# From https://www.sqlite.org/lang_vacuum.html 
	# The only table that may be affected by this is 'moz_bookmarks_deleted'. I doubt this will matter? We'll see I guess.
	print('Compacting and optimising database....')    
	curMain.execute('vacuum')
	curMain.execute('pragma optimize') # Why not

	# Copy combined DBs back onto disk.
	dbMain.backup(sqlite3.connect(Path.cwd().joinpath('places.sqlite')), name = 'main')
	if Path.cwd().joinpath('favicons.sqlite').is_file() == True:
		dbMain.backup(sqlite3.connect(Path.cwd().joinpath('favicons.sqlite')), name = 'mainIcons')

	curMain.connection.commit()
	curMain.close()

	print(f'\n--- {(time.time() - startTime)} seconds ---')