from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, checkUTF8, checkPost62, checkPost96, columnPresent,\
																	  remove_RemakeIndeces, getDBExtPath, removeReorderTableColumns, reorderColumnSql

from programFiles.combinerFunctions.Supplementary.getModifyValues import insUpdFaviconIDs, originsGetPrefixHost
from programFiles.combinerFunctions.combineLoops import combineLoops
from programFiles.guiClasses.misc import checkStopPressed

from inspect import currentframe, getframeinfo
import programFiles.globalVars as g


def mozPlaces(dbArgs):
	print('*moz_places*')
	(curMain, dbInsPre55, dbExtPre55) = dbArgs

	curMain.execute('begin')
	placesInsLen = len(curMain.execute('pragma main.table_info(moz_places)').fetchall())
	placesExtLen = len(curMain.execute('pragma dbExt.table_info(moz_places)').fetchall())

	newUrls_VisitDates = getAllEntries(cur = curMain, SQL = 'SELECT url, last_visit_date from dbExt.moz_places',
									   dictSchema = 'entry[0]: entry[1]', blockSize = 1000)

	remove_RemakeIndeces(curMain, 'main', 'moz_places', 'Remove')
	# Only update 'last_visit_date' if the column actually exists 
	# (it's a longshot it won't exist, FF 3.0 was the only version that didn't have it).
	if placesInsLen > 9 and placesExtLen > 9:
		oldUrls_DatesIDs = g.oldEntries.get('moz_places')
		for blockData in newUrls_VisitDates.values():
			checkStopPressed()

			for newUrl, newVisitDate in blockData.items():
				if newUrl in oldUrls_DatesIDs.keys():
					(oldVisitDate, oldPlaceID) = oldUrls_DatesIDs.get(newUrl)

					if (newVisitDate is not None) and (oldVisitDate is not None):
						if newVisitDate > oldVisitDate:
							curMain.execute('UPDATE main.moz_places set last_visit_date = ? where id = ?', (newVisitDate, oldPlaceID))

	remove_RemakeIndeces(curMain, 'main', 'moz_places', 'Remake')
	curMain.connection.commit()


	curMain.execute('begin')
	dbListGet = curMain.execute('pragma database_list').fetchall()
	dbList = [db[1] for db in dbListGet]

	dbInsPost62 = checkPost62(curMain, 'main')
	dbExtPost62 = checkPost62(curMain, 'dbExt')

	dbInsPost96 = checkPost96(curMain, 'main')
	dbExtPost96 = checkPost96(curMain, 'dbExt')

	insFaviconID = columnPresent(curMain, 'main', 'moz_places', 'favicon_id')
	extFaviconID = columnPresent(curMain, 'dbExt', 'moz_places', 'favicon_id')

	# Default value for each column
	lastVisitDate = None
	guid = None
	foreignCount = 0
	urlHash = 0
	description = None
	previewImageURL = None
	tempOriginID = 0
	siteName = None

	# Put 'site_name' at the end.
	# For some reason, as of Firefox 96, when a new places.sqlite DB is created, 'site_name' is put before 'origin_id'.
	# Only for new DBs. Old ones that are upgraded to the newest schema have the column appended like normal.
	# No idea why. But it screws things up as this combiner works on the assumption that each new column is appended, not inserted!
	if dbInsPost96 == True:
		colTo = 15
		columns = {'reorder': {'site_name TEXT': colTo}}
		removeReorderTableColumns(curMain, 'main', 'moz_places', columns)


	newPlacesSql = 'SELECT * from dbExt.moz_places'
	# For all other DBs, only re-order the sql for the dictionary's columns, not the actual DB directly.
	# It messes with the file's date/time properties otherwise.
	if dbExtPost96 == True:
		if extFaviconID == True: colTo = 16
		elif extFaviconID == False: colTo = 15

		newPlacesSql = reorderColumnSql(curMain, 'dbExt', 'moz_places', newPlacesSql, {'site_name': colTo})


	newPlaces = checkUTF8(curMain, newPlacesSql, 'entry[0]: list(entry)', {'description': [None]}, 1000)

	if dbInsPre55 == True:
		if dbExtPre55 == True:
			defaultValues = [lastVisitDate, guid, foreignCount, urlHash]

			oldIconURLs_IDs = g.oldEntries.get('moz_favicons')
			newIconIDs_URLs = getAllEntries(cur = curMain, SQL = 'SELECT id, url from dbExt.moz_favicons', dictSchema = 'entry[0]: entry[1]')

			# Because moz_favicons has already been merged at this stage, 'favicon_id' is pulled from main.moz_places
			for blockNum, blockData in newPlaces.items():
				checkStopPressed()

				for place in blockData.values():
					if place[7] is not None: # A None value means the page has no favicon
						extIconUrl = newIconIDs_URLs.get(place[7])
						if extIconUrl is None:
							frameInfo = getframeinfo(currentframe())
							errorMessage = (f'DB extract (moz_places):-\n'
											 'Error retrieving "extIconUrl" from moz_favicons\n'
											 'Where:\n'
											f'      id = {place[7]}')

							items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
							raise g.dictException(items)

						place[7] = oldIconURLs_IDs.get(extIconUrl)
						if place[7] is None:
							frameInfo = getframeinfo(currentframe())
							errorMessage = (f'DB insert (moz_places):-\n'
											 'Error retrieving "place[7]" from moz_favicons\n'
											 'Where:\n'
											f'      url = {extIconUrl}')

							items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
							raise g.dictException(items)

						newPlaces[blockNum].update({place[0]: place})


		elif dbExtPre55 == False:
			defaultValues = []

			# If iconsExtract's favicons.sqlite file is present, transfer the favicon IDs.
			if 'extIcons' in dbList:
				# Insert/update 'favicon_id'
				newPlaces = insUpdFaviconIDs(curMain, newPlaces, extFaviconID)

			# If iconsExtract's favicons.sqlite file is missing, skip transfering the favicon IDs and set them all to None.
			elif 'extIcons' not in dbList:
				for blockNum, blockData in newPlaces.items():
					checkStopPressed()

					for place in newPlaces.values():
						if extFaviconID == True: place[7] = None
						elif extFaviconID == False: place.insert(7, None)

						newPlaces[blockNum].update({place[0]: place})


		curMain.connection.commit()

		# Finally, combine the tables together!!
		loopDetails = {'tableName': 'main.moz_places', 'dbExtName': 'dbExt', 'defaultValues': defaultValues,
					   'oldEntries': {'tables': ['moz_places']},
					   'newEntries': {'entries': newPlaces},
					   'duplicateExec': 'if entry[10] in oldEntries.keys(): continue'}

		combineLoops(curMain, loopDetails)


	elif dbInsPre55 == False:
		# Remove 'favicon_id' column from dbExt if present
		if insFaviconID == False and extFaviconID == True:
			for blockNum, blockData in newPlaces.items():
				checkStopPressed()

				for place in blockData.values():
					del place[7]
					newPlaces[blockNum].update({place[0]: place})


		if dbInsPost62 == False:
			dbInsPost56 = columnPresent(curMain, 'main', 'moz_places', 'description')
			if   dbInsPost56 == True:  defaultValues = [lastVisitDate, guid, foreignCount, urlHash, description, previewImageURL]
			elif dbInsPost56 == False: defaultValues = [lastVisitDate, guid, foreignCount, urlHash]

		elif dbInsPost62 == True:
			defaultValues = [lastVisitDate, guid, foreignCount, urlHash, description, previewImageURL, tempOriginID]

			if dbInsPost96 == True:
				defaultValues = [lastVisitDate, guid, foreignCount, urlHash, description, previewImageURL, tempOriginID, siteName]


		# Both DBs are above FF 62.0
		if dbInsPost62 == True and dbExtPost62 == True:
			# This single iteration for-loop calculates the originCol position
			for place in newPlaces[1].values():
				if type(place[-1]) is int:
					originCol = len(place) -1

				elif type(place[-1]) is not int:
					originCol = len(place) -2

				break


			oldOriginIDs_PrefixHosts = getAllEntries(cur = curMain, SQL = 'SELECT id, prefix, host from dbExt.moz_origins', dictSchema = 'entry[0]: (entry[1], entry[2])')
			newOriginPrefixHosts_IDs = g.oldEntries.get('moz_origins')

			for blockNum, blockData in newPlaces.items():
				checkStopPressed()

				for place in blockData.values():
					oldPrefixHost = oldOriginIDs_PrefixHosts.get(place[originCol])
					if oldPrefixHost is None:
						frameInfo = getframeinfo(currentframe())
						errorMessage = (f'DB insert (moz_places):-\n'
										 'Error retrieving "oldPrefixHost" from moz_origins\n'
										 'Where:\n'
										f'      origin_id = {place[originCol]}')

						items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
						raise g.dictException(items)

					place[originCol] = newOriginPrefixHosts_IDs.get(oldPrefixHost)
					if place[originCol] is None:
						frameInfo = getframeinfo(currentframe())
						errorMessage = (f'DB extract (moz_places):-\n'
										 'Error retrieving "place[originCol]" from moz_origins\n'
										 'Where:\n'
										f'      oldPrefixHost = {list(oldPrefixHost)}')

						items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
						raise g.dictException(items)

					newPlaces[blockNum].update({place[0]: place})


		curMain.connection.commit()
		# Finally, combine the tables together!!
		loopDetails = {'tableName': 'main.moz_places', 'dbExtName': 'dbExt', 'defaultValues': defaultValues,
					   'oldEntries': {'tables': ['moz_places']},
					   'newEntries': {'entries': newPlaces},
					   'duplicateExec': 'if entry[9] in oldEntries.keys(): continue'}

		combineLoops(curMain, loopDetails)


		# In this instance, DB extract is below FF 62.0 which means it still has moz_hosts. This clause and loop gets the 'origin_id' for each place entry
		# and updates the entry accordingly. They must be updated in this manner as the method by which all the previous record insertions have been done 
		# involves using the extend() method of a list. It was simpler to adjust this small section of code than to adjust the entirety of the rest 
		# so that they inserted values rather than extended them.
		if dbInsPost62 == True and dbExtPost62 == False:
			oldPrefixesHosts = g.oldEntries.get('moz_origins')

			for blockNum, blockData in newPlaces.items():
				checkStopPressed()

				for place in blockData.values():
					prefix, host = originsGetPrefixHost(place[1])

					originID = oldPrefixesHosts.get((prefix, host))
					if originID is None:
						frameInfo = getframeinfo(currentframe())
						errorMessage = (f'DB insert (moz_places):-\n'
										 'Error retrieving "originID" from moz_origins\n'
										 'Where:\n'
										f'      prefix = {prefix}\n'
										f'      host = {host}')

						items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
						raise g.dictException(items)

					curMain.execute('UPDATE main.moz_places set origin_id = ? where id = ?', (originID, place[0]))

			curMain.connection.commit()

	mozHistoryVisits(curMain)


def mozHistoryVisits(curMain):
	print('*moz_historyvisits*')

	oldHistoryDates = g.oldEntries.get('moz_historyvisits')
	oldPlaceGUIDs_IDs = g.oldEntries.get('moz_places')
	newPlaceIDs_GUIDs = getAllEntries(cur = curMain, SQL = 'SELECT id, guid from dbExt.moz_places', dictSchema = 'entry[0]: entry[1]')
	newVisits = getAllEntries(cur = curMain, SQL = 'SELECT * from dbExt.moz_historyvisits order by visit_type desc', 
							  dictSchema = 'entry[0]: list(entry)', blockSize = 1000)

	includeDownloads = g.combinerConfig.getint('History Combiner', 'Include downloads')
	newVisitsEdited = {key: {} for key in newVisits.keys()}

	for blockNum, blockData in newVisits.items():
		checkStopPressed()

		for historyVisit in blockData.values():
			fkGUID = newPlaceIDs_GUIDs.get(historyVisit[2])
			if fkGUID is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB extract (moz_historyvisits):-\n'
								 'Error retrieving "fkGUID" from moz_places\n'
								 'Where:\n'
								f'      id = {historyVisit[2]}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			historyVisit[2] = oldPlaceGUIDs_IDs.get(fkGUID) # Foreign id
			if historyVisit[2] is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB insert (moz_historyvisits):-\n'
								 'Error retrieving "historyVisit[2]" from moz_places\n'
								 'Where:\n'
								f'      guid = {fkGUID}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			historyVisit[2] = historyVisit[2][1] # Get id, ignore last_visit_date
			
			# If the entry is an exact duplicate of one already present, then it's skipped!
			if fkGUID in oldPlaceGUIDs_IDs.keys() and historyVisit[3] in oldHistoryDates.keys(): continue
			if includeDownloads == 0 and historyVisit[4] == 7: continue # Downloads are ignored if the option is checked.

			fromVisitDiff = historyVisit[0] - historyVisit[1]  # Get the original visit difference
			historyVisit.append(fromVisitDiff)  # Append visit diff

			newVisitsEdited[blockNum].update({historyVisit[0]: historyVisit})

	loopDetails = {'tableName': 'main.moz_historyvisits', 'dbExtName': 'dbExt', 'defaultValues': [],
				   'oldEntries': {'tables': ['moz_historyvisits']},
				   'newEntries': {'entries': newVisitsEdited},

				   # if historyVisit[1] > 0: historyVisit[1] = historyVisit[0] - fromVisitDiff
				   'Conditional': {'1': 'if entry[1] > 0: entry[1] = entry[0] - entry[6]'}}

	combineLoops(curMain, loopDetails)