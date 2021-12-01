from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, getNewID, getDBExtPath
from programFiles.combinerFunctions.Supplementary.getModifyValues import updateOldEntries

from inspect import currentframe, getframeinfo
import programFiles.globalVars as g


def mozBookmarks(curMain):
	extAttUriPropID = curMain.execute('SELECT id from dbExt.moz_anno_attributes where name = ?', ('URIProperties/characterSet',)).fetchone()
	if extAttUriPropID is None: # If all bookmarks are only pre-genned
		# print('Only pre-genned bookmarks here. Skipping.')
		return {} # Return newBookmarkIDs as blank

	def insertBookmarks(bookmark):
		global newID
		bookmark[0] = newID + curInsNewID
		newID += 1
		try:
			if bookmarksInsLen == 11:
				curMain.execute('INSERT into main.moz_bookmarks values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', bookmark[:11])

			elif bookmarksInsLen == 13:
				if bookmarksExtLen == 11: bookmark.extend([syncStatus, syncChange])
				curMain.execute('INSERT into main.moz_bookmarks values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', bookmark)

		except Exception as e:
			raise g.insertException({'new': bookmark, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'mainDBName': 'main', 'errorTrace': e, 'type': 'insertExc'})

		newBookmarkIDs.update({bookmark[0]: ""})
		newBookmarkGUIDs.update({bookmark[10]: ""})
		curMain.connection.commit()

	def getNewPlaceID(oldPlaceID):
		guid = newPlaces.get(oldPlaceID)
		if guid is None:
			frameInfo = getframeinfo(currentframe())
			errorMessage = (f'DB extract (moz_bookmarks):-\n'
							 'Error retrieving "guid" from moz_places\n'
							 'Where:\n'
							f'      id = {oldPlaceID}')

			items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
			raise g.dictException(items)

		newPlaceID = oldPlaces.get(guid)
		if newPlaceID is None:
			frameInfo = getframeinfo(currentframe())
			errorMessage = (f'DB insert (moz_bookmarks):-\n'
							 'Error retrieving "id" from moz_places\n'
							 'Where:\n'
							f'      guid = {guid}')

			items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
			raise g.dictException(items)

		return newPlaceID[1] # Get id, ignore last_visit_date

	def updateMenuGUIDs(dbName):
		sql = f'SELECT id from {dbName}.moz_bookmarks where title = ? and fk is ?'
		mobileID = curMain.execute(sql, ('mobile', None)).fetchone()

		rootGUIDS = {1: 'root________', 2: 'menu________', 3: 'toolbar_____', 4: 'tags________', 5: 'unfiled_____'}
		if mobileID is not None: rootGUIDS.update({mobileID[0]: 'mobile______'}) # mobile doesn't always have 6 as its ID.

		if dbName == 'main':
			sql = f'UPDATE {dbName}.moz_bookmarks set guid = ? where id = ?'
			for rootID, guid in rootGUIDS.items(): curMain.execute(sql, (guid, rootID))
			curMain.connection.commit()

		elif dbName == 'dbExt':
			for rootID, guid in rootGUIDS.items(): newBookmarks[rootID][10] = guid


	# This tuple is for folders that already exist, but whose contents will be preserved (as in not overwritten, to avoid duplicate folders)
	preGenFolders = ('Bookmarks Menu', 'Bookmarks Toolbar', 'Tags', 'Unsorted Bookmarks',
					 'Other Bookmarks', 'menu', 'toolbar', 'tags', 'unfiled', 'mobile')



	# All these folders will be skipped
	foldersToSkip = ('Mozilla Firefox', 'Links for United Kingdom', 'Microsoft Websites', 
					 'MSN Websites', 'Windows Live', 'Latest Headlines', 'All Bookmarks')

	# foldersToSkip = []
	
	bookmarksToSkip = {# Pre-gen bookmarks. May have to modify depending on user's language???
					   'Most Visited':          ('place:queryType=0&sort=8&maxResults=10', 'place:sort=8&maxResults=10'), 
					   'Recently Bookmarked':   ('place:folder=BOOKMARKS_MENU&folder=UNFILED_BOOKMARKS&folder=TOOLBAR&queryType=1&sort=12&excludeItemIfParentHasAnnotation=livemark%2FfeedURI&maxResults=10&excludeQueries=1',
												 'place:folder=BOOKMARKS_MENU&folder=UNFILED_BOOKMARKS&folder=TOOLBAR&queryType=1&sort=12&maxResults=10&excludeQueries=1'), 
					   'Recent Tags':           ('place:type=6&sort=14&maxResults=10',),
					   'Getting Started':       ('http://en-gb.www.mozilla.com/en-GB/firefox/central/', 
												 'http://www.mozilla.com/en-GB/firefox/central/', 'https://www.mozilla.com/en-GB/firefox/central/', 
												 'http://www.mozilla.org/en-GB/firefox/central/', 'https://www.mozilla.org/en-GB/firefox/central/'),
					   'Web Slice Gallery':     ('http://go.microsoft.com/fwlink/?LinkId=121315',),
					   'Suggested Sites':       ('https://ieonline.microsoft.com/#ieslice',),
					   'Get Bookmark Add-ons':  ('https://en-gb.add-ons.mozilla.com/en-GB/firefox/bookmarks/', 
												 'https://addons.mozilla.org/en-GB/firefox/bookmarks/')}
			

	curMain.execute('begin')

	bookmarksInsLen = len(curMain.execute('pragma main.table_info(moz_bookmarks)').fetchall())
	bookmarksExtLen = len(curMain.execute('pragma dbExt.table_info(moz_bookmarks)').fetchall())

	oldBookmarkGUIDs = g.oldEntries.get('moz_bookmarks')
	curInsNewID = getNewID(curMain, 'main.moz_bookmarks')

	oldPlaces = g.oldEntries.get('moz_places')
	newPlaces = getAllEntries(cur = curMain, SQL = 'SELECT id, guid from dbExt.moz_places', dictSchema = 'entry[0]: entry[1]')

	newBookmarks = getAllEntries(cur = curMain, SQL = 'SELECT * from dbExt.moz_bookmarks order by parent asc, position asc', dictSchema = 'entry[0]: list(entry)')
	newBookmarksEdited = {}
	newBookmarkGUIDs = {}
	newBookmarkIDs = {}


	# This may possibly cause issues with DB Insert when the user tries adding new bookmarks from within Firefox?? I have no idea.
	updateMenuGUIDs('main')
	updateMenuGUIDs('dbExt')


	# Default value for each column
	syncStatus = 0
	syncChange = 1

	global newID; newID = 1
	for bookmark in newBookmarks.values():
		if bookmark[3] == 0 or bookmark[1] == 3: continue # If it's 'root' or a separator, skip

		placeToSkip = curMain.execute('SELECT url from dbExt.moz_places where id = ?', (bookmark[2],)).fetchone()
		if placeToSkip is not None: placeToSkip = placeToSkip[0]

		parent = newBookmarks.get(bookmark[3])
		if parent is None:
			frameInfo = getframeinfo(currentframe())
			errorMessage = (f'DB extract (moz_bookmarks):-\n'
							 'Error retrieving "id" from moz_bookmarks\n'
							 'Where:\n'
							f'      parent = {bookmark[3]}')

			items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
			raise g.dictException(items)

		# Skip:
		# If the bookmark is in bookmarksToSkip
		# If it's a folder and its title is in foldersToSkip/preGenFolders
		# If the bookmark's parent is a folder, skip it but leave its bookmarks. These will be handled at the end.
		if (bookmark[5] in bookmarksToSkip.keys() and placeToSkip in bookmarksToSkip.get(bookmark[5])) \
			or ((parent[2] is None and parent[5] in foldersToSkip)
			or (bookmark[2] is None and bookmark[5] in foldersToSkip)
			or (bookmark[2] is None and bookmark[5] in preGenFolders)) \
			or bookmark[10] in oldBookmarkGUIDs.keys(): continue
		
		# If it's a bookmark
		if bookmark[2] is not None: 
			bookmark[2] = getNewPlaceID(bookmark[2])
			newBookmarksEdited.update({bookmark[0]: bookmark})

		# If it's a folder
		elif bookmark[2] is None:
			newParentID = curMain.execute('SELECT id from main.moz_bookmarks where guid = ?', (parent[10],)).fetchone()
			if newParentID is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB insert (moz_bookmarks):-\n'
								 'Error retrieving "newParentID" from moz_bookmarks\n'
								 'Where:\n'
								f'      guid = {parent[10]}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			newParentID = newParentID[0]
			newPos = curMain.execute('SELECT max(position) from main.moz_bookmarks where parent = ?', (newParentID,)).fetchone()[0]
			if newPos is not None: bookmark[4] = newPos + 1
			elif newPos is None: bookmark[4] = 0

			bookmark[3] = newParentID
			insertBookmarks(bookmark)


	if len(newBookmarksEdited) > 0: print('*moz_bookmarks*')
	foldersConcat = {}
	i = 0
	for bookmark in newBookmarksEdited.values(): # Group bookmarks by their parent
		parent = newBookmarks.get(bookmark[3])
		if parent is None:
			frameInfo = getframeinfo(currentframe())
			errorMessage = (f'DB extract (moz_bookmarks):-\n'
							 'Error retrieving "id" from moz_bookmarks\n'
							 'Where:\n'
							f'      parent = {bookmark[3]}')

			items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
			raise g.dictException(items)

		newParentID = curMain.execute('SELECT id from main.moz_bookmarks where guid = ?', (parent[10],)).fetchone()
		i += 1
		# if i == 5: newParentID = None
		if newParentID is None:
			frameInfo = getframeinfo(currentframe())
			newBookmarksEdited = list(newBookmarksEdited.values())
			
			j = 2
			prevBKs = {}
			if len(newBookmarksEdited) > 1:
				while True:
					numBks = 0
					for BKs in prevBKs.values(): numBks += len(BKs)
					if numBks >= 10 or i - j < 0: break

					currBK = newBookmarksEdited[i - j]
					if currBK is not None: 
						currBKParent = tuple(newBookmarks.get(currBK[3]))
						if prevBKs.get(currBKParent) is None:
							prevBKs.update({currBKParent: []})

						prevBKs[currBKParent].append(currBK)

					j += 1


			errorMessage = (f'\nDB insert (moz_bookmarks):-\n'
							 'Error retrieving "newParentID" from moz_bookmarks\n'
							 'Where:\n'
							f'      guid = {parent[10]}')

			newParents = []
			newParent = newBookmarks.get(parent[3])
			newParents.extend([newParent, parent])

			if newParent[3] > 0:
				while newParent[3] > 0:
					newParent = newBookmarks.get(newParent[3])
					newParents.insert(0, newParent)

			errorMessage += (f'\n\n\nPlease note: The item\'s parent column has NOT been updated. '
							  'Any discrepancy between the parent\'s id column and the item\'s parent column can be safely ignored.\n\n')

			i = len(newParents)
			for parent in newParents:
				errorMessage += f'Parent {i}: {tuple(parent)}\n'
				i -= 1

			errorMessage += f'Item:     {bookmark}\n'
			errorMessage += '\n\nPrevious entries:-\n\n'
			for bkParent, bkChildren in prevBKs.items():
				errorMessage += f'Parent: {bkParent}\n'
				if   len(bkChildren) > 1:  errorMessage += f'Items:  {bkChildren[0]}\n'
				elif len(bkChildren) == 1: errorMessage += f'Item:   {bkChildren[0]}'
				for bk in bkChildren[1:]:  errorMessage += f'        {bk}\n'

				errorMessage += '\n\n'

			items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
			raise g.dictException(items)

		newParentID = newParentID[0]
		if newParentID not in foldersConcat.keys():
			foldersConcat.update({newParentID: {}})

		foldersConcat[newParentID].update({bookmark[0]: bookmark})


	for parentID, folder in foldersConcat.items():
		pos = 1
		newPos = curMain.execute('SELECT max(position) from main.moz_bookmarks where parent = ?', (parentID,)).fetchone()[0]
		for bookmark in folder.values():
			bookmark[3] = parentID
			if newPos is not None: bookmark[4] = pos + newPos # Calculate new position
			elif newPos is None: bookmark[4] = pos-1

			pos += 1
			insertBookmarks(bookmark)


	# If the option is checked:
	# Group all folders in the main menu together and preserve their original positioning while moving them collectively above the bookmarks.
	foldersMenuPosSQL = 'SELECT id from main.moz_bookmarks where parent = 2 order by fk asc, position asc'
	foldersAbove = g.combinerConfig.getint('History Combiner', 'Folders above')
	if foldersAbove == 2:
		newPos = 0
		allBookmarks = getAllEntries(cur = curMain, SQL = foldersMenuPosSQL, dictSchema = 'entry[0]: ""')
		for bkID in allBookmarks.keys():
			curMain.execute('UPDATE moz_bookmarks set position = ? where id = ?', (newPos, bkID))
			newPos += 1


	curMain.connection.commit()
	updateOldEntries(curMain, ['moz_bookmarks'], newBookmarkGUIDs)

	deldBookmarks(curMain)
	return newBookmarkIDs


def deldBookmarks(curMain):
	deldSQL = 'SELECT exists (SELECT name from main.sqlite_master where type = ? and name = ?)'
	deldInsExists = curMain.execute(deldSQL, ('table', 'moz_bookmarks_deleted')).fetchone()[0]
	deldExtExists = curMain.execute(deldSQL.replace('main.', 'dbExt.'), ('table', 'moz_bookmarks_deleted')).fetchone()[0]

	# If 'moz_bookmarks_deleted' exists
	if deldInsExists == True and deldExtExists == True:
		newDeld = getAllEntries(cur = curMain, SQL = 'SELECT * from dbExt.moz_bookmarks_deleted', dictSchema = 'entry[0]: list(entry)')
		if len(newDeld) == 0: return

		print('*moz_bookmarks_deleted*')
		curMain.execute('begin')
		oldDeld = getAllEntries(cur = curMain, SQL = 'SELECT guid from main.moz_bookmarks_deleted', dictSchema = 'entry[0]: ""')

		for deldBookmark in newDeld.values():
			if deldBookmark[0] in oldDeld.keys(): continue # If for some reason it already exists

			try:
				curMain.execute('INSERT into main.moz_bookmarks_deleted values (?, ?)', deldBookmark)

			except Exception as e:
				raise g.insertException({'new': deldBookmark, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'mainDBName': 'main', 'errorTrace': e, 'type': 'insertExc'})

		curMain.connection.commit()
