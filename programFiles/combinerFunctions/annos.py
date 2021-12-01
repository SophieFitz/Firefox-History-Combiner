from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, getNewID, columnPresent, getDBExtPath
from programFiles.combinerFunctions.Supplementary.getModifyValues import insAttIDCheck, extAttIDCheck, updateOldEntries
from programFiles.combinerFunctions.combineLoops import combineLoops
from programFiles.guiClasses.misc import checkStopPressed

from inspect import currentframe, getframeinfo
import programFiles.globalVars as g


def annotations(curMain, newBookmarkIDs):
	# 'Att' is 'Attribute' in all forthcoming variable names.
	print('*moz_anno_attributes*') # The different types of attributes
	includeDownloads = g.combinerConfig.getint('History Combiner', 'Include downloads')
	
	insertAttLastID = curMain.execute('SELECT max(id) from main.moz_anno_attributes').fetchone()[0]
	if insertAttLastID is None: insertAttLastID = 0 # In case there are no entries present in "moz_anno_attributes", lastID is set to 0.
		
	bookmarkProperties = ('bookmarkProperties/description',)
	folderProperties = ('bookmarkPropertiesDialog/folderLastUsed',)
	uriProperties = ('URIProperties/characterSet',)

	annoAttID = 1
	insAttBookmarkPropID, annoAttID = insAttIDCheck(curMain, insertAttLastID, bookmarkProperties, annoAttID)
	insAttFolderPropID, annoAttID = insAttIDCheck(curMain, insertAttLastID, folderProperties, annoAttID)
	insAttUriPropID, annoAttID = insAttIDCheck(curMain, insertAttLastID, uriProperties, annoAttID)

	extAttBookmarkPropID = extAttIDCheck(curMain, bookmarkProperties)
	extAttFolderPropID = extAttIDCheck(curMain, folderProperties)
	extAttUriPropID = extAttIDCheck(curMain, uriProperties)

	curMain.connection.commit()


	newAnnosGet = curMain.execute('SELECT * from dbExt.moz_annos').fetchall()

	if includeDownloads == 0: # Downloads are ignored.
		newAnnos = {anno[0]: list(anno) for anno in newAnnosGet if anno[2] == extAttUriPropID}


	elif includeDownloads == 2: # Downloads are included.
		downloadUriProperties = ('downloads/destinationFileURI',)
		downloadMetaProperties = ('downloads/metaData',)

		insAttDownloadUriPropID, annoAttID = insAttIDCheck(curMain, insertAttLastID, downloadUriProperties, annoAttID)
		insAttDownloadMetaPropID, annoAttID = insAttIDCheck(curMain, insertAttLastID, downloadMetaProperties, annoAttID)

		extAttDownloadUriPropID = extAttIDCheck(curMain, downloadUriProperties)
		extAttDownloadMetaPropID = extAttIDCheck(curMain, downloadMetaProperties)
		extAttDownloadFileNameID = extAttIDCheck(curMain, ('downloads/destinationFileName',))

		newAnnos = {anno[0]: list(anno) for anno in newAnnosGet}

	# Only combine moz_annos if there are entries to combine!
	if len(newAnnos) == 0: return
	
	print('*moz_annos*') # Bookmark page encodings and downloads
	newAnnos = getAllEntries(entries = newAnnos, blockSize = 1000)

	# Default value for each column
	mimeType = None

	oldPlaceIDsAnnoAttIDs = g.oldEntries.get('moz_annos')
	oldPlaceGUIDs_IDs = g.oldEntries.get('moz_places')
	newPlaceIDs_GUIDs = getAllEntries(cur = curMain, SQL = 'SELECT id, guid from dbExt.moz_places', dictSchema = 'entry[0]: entry[1]')

	curInsNewID = getNewID(curMain, 'main.moz_annos')

	insMimeType = columnPresent(curMain, 'main', 'moz_annos', 'mime_type')
	extMimeType = columnPresent(curMain, 'dbExt', 'moz_annos', 'mime_type')

	i = 0
	newAnnosEdited = {}
	for blockData in newAnnos.values():
		checkStopPressed()

		for anno in blockData.values():
			# I think orphans are created from Download entries that have been deleted from history but still remain in this table.
			# They may get cleaned up eventually but frankly, meh. Just skip them.

			guid = newPlaceIDs_GUIDs.get(anno[1])
			if guid is None: continue
			
			if anno[2] == extAttUriPropID:
				# Only include bookmark page encodings if 1 or more bookmarks are present. If it's just downloads, skip the bookmarks stuff entirely.
				if len(newBookmarkIDs) > 0: anno[2] = insAttUriPropID
				elif len(newBookmarkIDs) == 0: continue

			elif anno[2] == extAttDownloadUriPropID:  anno[2] = insAttDownloadUriPropID
			elif anno[2] == extAttDownloadMetaPropID: anno[2] = insAttDownloadMetaPropID
			elif anno[2] == extAttDownloadFileNameID: continue # Skip download filenames as they are irrelevant.

			# Bizarrely, there are orphan annos for downloads which don't link to the correct place_id. This checks to see if the download still exists.
			# It includes it if so, skips it if not.
			if anno[2] in (insAttDownloadUriPropID, insAttDownloadMetaPropID):
				visitType = curMain.execute('SELECT visit_type from dbExt.moz_historyvisits where place_id = ?', (anno[1],)).fetchone()[0]
				if visitType != 7: continue

			placeID = oldPlaceGUIDs_IDs.get(guid)
			if placeID is None:
				frameInfo = getframeinfo(currentframe())
				errorMessage = (f'DB insert (moz_annos):-\n'
								 'Error retrieving "placeID" from moz_places\n'
								 'Where:\n'
								f'      guid = {guid}')

				items = {'frameInfo': frameInfo, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'errorMessage': errorMessage, 'type': 'dictExc'}
				raise g.dictException(items)

			anno[1] = placeID[1] # Get id, ignore last_visit_date
			anno[0] = i + curInsNewID
			i += 1

			if tuple(anno[1:3]) in oldPlaceIDsAnnoAttIDs: continue

			# Add or remove 'mime_type' if necessary. Whether or not it gets removed depends on the version of each DB 
			# (above or below FF 55.0). FF 55.0 removed 'mime_type'.
			if insMimeType == False:
				if extMimeType == True: del anno[3]

			elif insMimeType == True:
				if extMimeType == False: anno.insert(3, mimeType)

			insertSQL = ('?, ' * len(anno))[:-2]
			insertSQL = f'INSERT into main.moz_annos values({insertSQL})'
			try:
				curMain.execute(insertSQL, anno)

			except Exception as e:
				raise g.insertException({'new': anno, 'dbExtPath': getDBExtPath(curMain, 'dbExt'), 'mainDBName': 'main', 
										 'insAttDownloadUriPropID': insAttDownloadUriPropID, 'errorTrace': e, 'type': 'insertExc'})

			newAnnosEdited.update({anno[0]: anno})

	curMain.connection.commit()
	updateOldEntries(curMain, ['moz_annos'], newAnnosEdited)


	# Only include bookmark descriptions if 1 or more bookmarks are present. If it's just downloads, skip the bookmarks stuff entirely.
	if len(newBookmarkIDs) > 0:
		toSkip = ('Add bookmarks to this folder to see them displayed on the Bookmarks Toolbar')
		newItemAnnosGet = curMain.execute('SELECT * from dbExt.moz_items_annos').fetchall()
		newItemAnnos = {itemAnno[0]: list(itemAnno) for itemAnno in newItemAnnosGet if itemAnno[4] not in toSkip
						if itemAnno[2] in (extAttBookmarkPropID, extAttFolderPropID)}
						# Smart bookmarks will be ignored for now, unless people really want them.

		# Only combine moz_items_annos if there are entries to combine!
		if len(newItemAnnos) == 0: return

		print('*moz_items_annos*') # Bookmark descriptions
		newItemAnnos = getAllEntries(entries = newItemAnnos, blockSize = 1000)

		# In both DBs, I'm looking for the 'mime_type' column as this is more accurate. If I were to use the dbPre55 variables from 'combiner.py',
		# they're based off of whether the 'moz_favicons' table exists. Not whether the 'mime_type' column in 'moz_annos' and 'moz_items_annos' exist.
		# Checking for 'mime_type' is more fullproof.
		insMimeType = columnPresent(curMain, 'main', 'moz_items_annos', 'mime_type')
		extMimeType = columnPresent(curMain, 'dbExt', 'moz_items_annos', 'mime_type')

		newItemAnnosEdited = {key: {} for key in newItemAnnos.keys()}
		for blockNum, blockData in newItemAnnos.items():
			checkStopPressed()

			for itemAnno in blockData.values():
				# Skip orphaned item_annos
				guid = curMain.execute('SELECT guid from dbExt.moz_bookmarks where id = ?', (itemAnno[1],)).fetchone()
				if guid[0] is None: continue

				itemID = curMain.execute('SELECT id from main.moz_bookmarks where guid = ?', (guid[0],)).fetchone()[0]
				if itemID not in newBookmarkIDs.keys(): continue
				itemAnno[1] = itemID
				
				if itemAnno[2] == extAttBookmarkPropID: itemAnno[2] = insAttBookmarkPropID
				elif itemAnno[2] == extAttFolderPropID: itemAnno[2] = insAttFolderPropID

				# Same as before. Add or remove 'mime_type' if necessary. And insert the records.
				if insMimeType == False: 
					if extMimeType == True: del itemAnno[3]

				elif insMimeType == True: 
					if extMimeType == False: itemAnno.insert(3, mimeType)

				newItemAnnosEdited[blockNum].update({itemAnno[0]: itemAnno})


		loopDetails = {'tableName': 'main.moz_items_annos', 'dbExtName': 'dbExt', 'defaultValues': [],
					   'oldEntries': {'tables': ['moz_items_annos']},
					   'newEntries': {'entries': newItemAnnosEdited}}

		# There is a unique index constraint on item_id and anno_attribute_id. Therefore skip duplicates.
		loopDetails.update({'duplicateExec': 'if tuple(entry[1:3]) in oldEntries.keys(): continue'})
		combineLoops(curMain, loopDetails)