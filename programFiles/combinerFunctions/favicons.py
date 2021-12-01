from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, blocksToNormal, columnPresent, getNewID, getDBExtPath
from programFiles.combinerFunctions.Supplementary.getModifyValues import getMimeType, resizeImage, removePrefix, getRoot
from programFiles.combinerFunctions.Supplementary.urlHashing import getHash
from programFiles.combinerFunctions.combineLoops import combineLoops
from programFiles.guiClasses.misc import checkStopPressed

from inspect import currentframe, getframeinfo
import programFiles.globalVars as g
import logging


def mozFavicons(dbArgs):
	(curMain, dbInsPre55, dbExtPre55) = dbArgs
	dbListGet = curMain.execute('pragma database_list').fetchall()
	dbList = [db[1] for db in dbListGet]

	if dbInsPre55 == True:
		if dbExtPre55 == True:
			print('*moz_favicons*')

			# Default value for each column
			guid = None

			# moz_favicons
			loopDetails = {'tableName': 'main.moz_favicons', 'dbExtName': 'dbExt', 'defaultValues': [guid],
						   'oldEntries': {'tables': ['moz_favicons']},
						   'newEntries': {'SQL': 'SELECT * from dbExt.moz_favicons', 'schema': 'entry[0]: list(entry)', 'blockSize': 1000},
						   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue'}

			combineLoops(curMain, loopDetails)

		elif dbExtPre55 == False:
			# If iconsExtract's favicons.sqlite file is missing, skip it.
			if 'extIcons' in dbList:
				print('*favicons database* ---> *moz_favicons*')

				# Default value for each column
				guid = None

				sql = 'SELECT id, icon_url, data, width, expire_ms from extIcons.moz_icons order by width asc'

				# moz_favicons
				loopDetails = {'tableName': 'main.moz_favicons', 'dbExtName': 'extIcons', 'defaultValues': [guid],
							   'oldEntries': {'tables': ['moz_favicons']},
							   'newEntries': {'SQL': sql, 'schema': 'entry[1]: list(entry)', 'blockSize': 1000},
							   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue',
							   'Insert': {'functions': [lambda val: val], 'pos': [5], 'cols': [3]}, # Copy width to the end, then delete it.
							   'Modify': {'functions': [getMimeType, resizeImage], 'cols': [[2, 3], [2, 2]]},
							   'Conditional': {'1': 'if entry[4] > 0: entry[4] *= 1000', 
											   '2': 'if entry[3] == "image/": entry[3] = entry[5]',
											   '3': 'del entry[5]'}}

				combineLoops(curMain, loopDetails)

			elif 'extIcons' not in dbList: print('favicons.sqlite file is missing')


	elif dbInsPre55 == False:
		iconsPagesInsLen = len(curMain.execute('pragma mainIcons.table_info(moz_icons_to_pages)').fetchall())

		# If iconsExtract's favicons.sqlite file is missing, skip it.
		if 'extIcons' not in dbList and dbExtPre55 == False: print('favicons.sqlite file is missing')
		elif 'extIcons' in dbList and dbExtPre55 == False:
			print('*moz_icons*, *moz_pages_w_icons* and *moz_icons_to_pages*')
			newIcons = getAllEntries(cur = curMain, SQL = 'SELECT * from extIcons.moz_icons', dictSchema = 'entry[0]: list(entry)', blockSize = 1000)
			newIconID = getNewID(curMain, 'mainIcons.moz_icons')
			newWPageID = getNewID(curMain, 'mainIcons.moz_pages_w_icons')

			# moz_icons
			loopDetails = {'tableName': 'mainIcons.moz_icons', 'dbExtName': 'extIcons', 'defaultValues': [],
						   'oldEntries': {'tables': ['moz_icons']},
						   'newEntries': {'entries': newIcons},
						   'duplicateExec': 'if (entry[1], entry[3]) in oldEntries.keys(): continue'}

			combineLoops(curMain, loopDetails)


			# There are some duplicate entries in 'moz_pages_w_icons' tables. They almost always lead to a non-existent 'moz_icons_to_pages' entry.
			# In one of my DBs that I checked for these sorts of duplicates, I found one that pointed to the wrong icon. 
			# Luckily, Python dictionaries automatically discard duplicate Keys. 
			# And since I'm looping through in order of 'id' it will discard newer entries that are tarnished, so this should be fine.
			newWPages = getAllEntries(cur = curMain, SQL = 'SELECT * from extIcons.moz_pages_w_icons order by id asc', 
							   		  dictSchema = 'entry[0]: list(entry)', blockSize = 1000)

			# moz_pages_w_icons
			loopDetails = {'tableName': 'mainIcons.moz_pages_w_icons', 'dbExtName': 'extIcons', 'defaultValues': [],
						   'oldEntries': {'tables': ['moz_pages_w_icons']},
						   'newEntries': {'entries': newWPages},
						   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue'}

			combineLoops(curMain, loopDetails)

			newIcons = blocksToNormal(newIcons)
			newWPages = blocksToNormal(newWPages)
			newlyCombinedIcons = g.oldEntries.get('moz_icons')
			newlyCombinedWPages = g.oldEntries.get('moz_pages_w_icons')

			# Default value for each column
			expireMS = 0
			
			iconsPagesExtLen = len(curMain.execute('pragma extIcons.table_info(moz_icons_to_pages)').fetchall())
			newToPages = getAllEntries(cur = curMain, SQL = 'SELECT * from extIcons.moz_icons_to_pages', dictSchema = 'tuple(entry): list(entry)', blockSize = 1000)

			for blockData in newToPages.values():
				checkStopPressed()

				for toPage in blockData.values():
					if iconsPagesExtLen == 3: expireMS = toPage[2]
					pageID, iconID = toPage[:2]

					# These don't need a dict exception as they are checked below.
					pageUrl = newWPages.get(pageID)
					iconUrl_Width = newIcons.get(iconID)
					if pageUrl is None or iconUrl_Width is None: continue # Skip references to non-existent entries.


					# If these aren't None, subcript them
					pageUrl = pageUrl[1]
					iconUrl_Width = iconUrl_Width[1:4]
					del iconUrl_Width[1]

					newWPageID = newlyCombinedWPages.get(pageUrl)
					if newWPageID is None:
						frameInfo = getframeinfo(currentframe())
						errorMessage = ('DB icons insert (moz_icons_to_pages):-\n'
										 'Error retrieving "newWPageID" from moz_pages_w_icons\n'
										 'Where:\n'
										 f'      page_url = {pageUrl}')

						items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'extIcons'), 'errorMessage': errorMessage, 'type': 'dictExc'}
						raise g.dictException(items)

					newIconID = newlyCombinedIcons.get(tuple(iconUrl_Width))
					if newIconID is None:
						frameInfo = getframeinfo(currentframe())
						errorMessage = ('DB icons insert (moz_icons_to_pages):-\n'
										'Error retrieving "newIconID" from moz_icons\n'
										'Where:\n'
									   f'      icon_url = {iconUrl_Width[0]}\n'
									   f'      width = {iconUrl_Width[1]}')

						items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'extIcons'), 'errorMessage': errorMessage, 'type': 'dictExc'}
						raise g.dictException(items)

					toPage = [newWPageID, newIconID]
					if iconsPagesInsLen == 2:
						toPagesSQL = 'INSERT or IGNORE into mainIcons.moz_icons_to_pages values (?, ?)'

					elif iconsPagesInsLen == 3:
						toPage.append(expireMS)
						toPagesSQL = 'INSERT or IGNORE into mainIcons.moz_icons_to_pages values (?, ?, ?)'

					# Should be fine as I'm inserting / ignoring the values, therefore duplicates and errors should be ommitted.
					curMain.execute(toPagesSQL, toPage)

			curMain.connection.commit()


		elif dbExtPre55 == True:
			print('*moz_favicons* --> *moz_icons*, *moz_pages_w_icons* and *moz_icons_to_pages*')

			sql = '''SELECT id, url, 
									 
							 CASE 
								  WHEN mime_type = "image/png" THEN 16 
								  WHEN mime_type = "image/svg+xml" THEN 65535 
								  ELSE mime_type 
							 END, 

					 data from dbExt.moz_favicons'''

			# moz_icons
			loopDetails = {'tableName': 'mainIcons.moz_icons', 'dbExtName': 'dbExt', 'defaultValues': [],
						   'oldEntries': {'tables': ['moz_icons', 'newlyCombinedIcons']},
						   'newEntries': {'SQL': sql, 'schema': 'entry[0]: list(entry)', 'blockSize': 1000},
						   'Insert': {'functions': [removePrefix, getHash, getRoot], 'pos': [0, 3, 5, 6, 6], 'cols': [1, 0, 0, None, 0]},
						   'duplicateExec': 'if (entry[1], entry[2]) in oldEntries.keys(): continue'}

			combineLoops(curMain, loopDetails)

			sql = 'SELECT p.id, p.url FROM dbExt.moz_places p join dbExt.moz_favicons f on f.id = p.favicon_id'
			# moz_pages_w_icons
			loopDetails = {'tableName': 'mainIcons.moz_pages_w_icons', 'dbExtName': 'dbExt', 'defaultValues': [],
						   'oldEntries': {'tables': ['moz_pages_w_icons']},
						   'newEntries': {'SQL': sql, 'schema': 'entry[0]: list(entry)', 'blockSize': 1000},
						   'Insert': {'functions': [getHash], 'pos': [2], 'cols': [1]},
						   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue'}

			combineLoops(curMain, loopDetails)


			newlyCombinedIcons = g.oldEntries.get('newlyCombinedIcons')
			newlyCombinedWPages = g.oldEntries.get('moz_pages_w_icons')

			sql = 'SELECT p.url, f.url from dbExt.moz_places p inner join dbExt.moz_favicons f on p.favicon_id = f.id where p.favicon_id is not null'
			newToPagesGet = curMain.execute(sql).fetchall()
			newToPages = {tuple(url): [newlyCombinedWPages.get(url[0]), newlyCombinedIcons.get(url[1])] for url in newToPagesGet}
			newToPages = getAllEntries(entries = newToPages, blockSize = 1000)

			# Default values for columns
			expireMS = 0

			for blockNum, blockData in newToPages.items():
				checkStopPressed()

				for toPage in blockData.values():
					if iconsPagesInsLen == 2:
						iconsInsertSQL = 'INSERT or IGNORE into mainIcons.moz_icons_to_pages values (?, ?)'

					elif iconsPagesInsLen == 3:
						toPage.append(expireMS)
						iconsInsertSQL = 'INSERT or IGNORE into mainIcons.moz_icons_to_pages values (?, ?, ?)'

					# Should be fine without try/except as I'm inserting / ignoring the values, therefore duplicates and errors should be ommitted.
					curMain.execute(iconsInsertSQL, toPage)

			curMain.connection.commit()