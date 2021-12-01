from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries
from programFiles.combinerFunctions.combineLoops import combineLoops
from programFiles.guiClasses.misc import checkStopPressed

from inspect import currentframe, getframeinfo
import programFiles.globalVars as g


def mozInputHistory(curMain):
	newInputHistory = getAllEntries(cur = curMain, SQL = 'SELECT * from dbExt.moz_inputhistory', 
									dictSchema = '(entry[0], entry[1]): entry[2]', blockSize = 1000)

	if len(newInputHistory) == 0: return
	print('*moz_inputhistory*')
	curMain.execute('begin')
	
	newPlaceIDs_GUIDs = getAllEntries(cur = curMain, SQL = 'SELECT id, guid from dbExt.moz_places', dictSchema = 'entry[0]: entry[1]')
	oldPlaceGUIDs_IDs = g.oldEntries.get('moz_places')

	for blockNum, blockData in newInputHistory.items():
		checkStopPressed()

		for place_Input, useCount in blockData.items():
			place_Input = list(place_Input) # Lists can't be hashed in dicts, but I need it to be modifiable so I'm converting to a list here.

			currPlaceGUID = newPlaceIDs_GUIDs.get(place_Input[0])
			if currPlaceGUID is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB extract (moz_inputhistory):-\n'
								 'Error retrieving "currPlaceGUID" from moz_places\n'
								 'Where:\n'
								f'      id = {place_Input[0]}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			place_Input[0] = oldPlaceGUIDs_IDs.get(currPlaceGUID)
			if place_Input[0] is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB insert (moz_inputhistory):-\n'
								 'Error retrieving "place_Input[0]" from moz_places\n'
								 'Where:\n'
								f'      guid = {currPlaceGUID}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			place_Input[0] = place_Input[0][1] # Get id, ignore last_visit_date

			entryAlreadyExists = curMain.execute('SELECT exists (SELECT * from main.moz_inputhistory where place_id = ? and input = ?)', place_Input).fetchone()[0]

			# Updating pre-existing entries
			if entryAlreadyExists == True:
				oldInputEntry = curMain.execute('SELECT * from main.moz_inputhistory where place_id = ? and input = ?', place_Input).fetchone()

				useCount += oldInputEntry[2]
				# inputItem[2] /= 2 # Take the average
				# If the input already exists, the new value is divided by 1.5. Not entirely sure why I've done this... I think cos it's less extreme than 2...
				useCount /= 1.5

				# According to the sourcecode, this is the maximum value that use_count will ascend to 
				# (asymptotically, but I don't have the faintest how to do that so this'll do)
				if useCount > 10.0: useCount = 10.0 

				curMain.execute('UPDATE main.moz_inputhistory set use_count = ? where place_id = ? and input = ?', (useCount, place_Input[0], place_Input[1]))

			# Adding new entries!
			elif entryAlreadyExists == False:
				try:
					curMain.execute('INSERT into main.moz_inputhistory values (?, ?, ?)', (place_Input[0], place_Input[1], useCount))

				except Exception as e:
					raise g.insertException({'new': (place_Input[0], place_Input[1], useCount), 'dbExtPath': getDBExtPath(curMain, dbExtName), 
											 'mainDBName': mainDBName, 'errorTrace': e, 'type': 'insertExc'})

	curMain.connection.commit()


def mozKeywords(curMain):
	newKeywords = getAllEntries(cur = curMain, SQL = 'SELECT * from dbExt.moz_keywords', dictSchema = 'entry[0]: list(entry)')
	if len(newKeywords) == 0: return
	
	print('*moz_keywords*')

	keywordInsLen = len(curMain.execute('pragma main.table_info(moz_keywords)').fetchall())
	keywordExtLen = len(curMain.execute('pragma dbExt.table_info(moz_keywords)').fetchall())

	oldKeywords = getAllEntries(cur = curMain, SQL = 'SELECT keyword from main.moz_keywords', dictSchema = 'entry[0]: ""')
	oldKeysPost = getAllEntries(cur = curMain, SQL = 'SELECT keyword, post_data from main.moz_keywords', dictSchema = r'(entry[0], entry[1]): ""')

	# Default value for each column
	postData = None

	loopDetails = {'tableName': 'main.moz_keywords', 'defaultValues': [postData],
				   'oldEntries': {'entries': oldKeywords},
				   'newEntries': {'entries': newKeywords},
				   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue'}

	newKeywordsEdited = {}
	if keywordInsLen == 4:
		for keyword in newKeywords.values():
			oldID = keyword[0]
			if keywordExtLen == 2:
				# I presume that the 'keyword_id' column from 'moz_bookmarks' was used at one time to point to the id of the given keyword.
				# In FF versions since 40.0 (db version 28), place_id has been added to 'moz_keywords', 
				# making the aforementioned 'keyword_id' column seemingly reduntant.
				# This next clause attempts to fill the 'place_id' column.
				try:
					placeID = curMain.execute('SELECT place_id from dbExt.moz_bookmarks where keyword_id = ?', (oldID,)).fetchone()[0]

				except:
					continue
				
				keyword.extend([placeID, postData])

			elif keywordExtLen == 4:
				# If the 2 columns 'keyword' and 'post_data' aren't unique, skip them. They have a unique index constraint.
				keyPost = (keyword[1], keyword[3])
				if keyPost in oldKeysPost.keys(): continue

				guid = curMain.execute('SELECT guid from dbExt.moz_places where id = ?', (keyword[2],)).fetchone()[0]
				keyword[2] = curMain.execute('SELECT id from main.moz_places where guid = ?', (guid,)).fetchone()[0]

			newKeywordsEdited.update({keyword[0]: keyword})

		loopDetails.update({'defaultValues': [], 'dbExtName': 'dbExt', 'newEntries': {'entries': newKeywordsEdited}})
	
	combineLoops(curMain, loopDetails)