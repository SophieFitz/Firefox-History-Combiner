# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. 
# If a copy of the MPL was not distributed with this file, you can obtain one at http://mozilla.org/MPL/2.0/.

# Support for upgrading old history DBs (ones from before FF 55.0) has been removed as of FF 85.0.
# ESR 78.0 is the last searchable-online repository that contains the since-removed favicons conversion code.
# I have re-implemented this code in my function 'contertToPNG()', basing it on 'FetchAndConvertUnsupportedPayloads::ConvertPayload'.
# See: https://searchfox.org/mozilla-esr78/source/toolkit/components/places/FaviconHelpers.cpp#1221
from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, checkPre55
from programFiles.guiClasses.misc import checkStopPressed
from PIL import Image, ImageFile
from pathlib import Path
from io import BytesIO

import programFiles.globalVars as g
import sqlite3, ast

ImageFile.LOAD_TRUNCATED_IMAGES = True # Ignore


def faviconsFiles(stage):
	# Create lists of DBs to extract history data from!
	allDBsPre55 = []
	allDBsPost55 = []

	missingIconsList = []

	isProfile = False
	allDBFolders = ast.literal_eval(g.combinerConfig.get('History Combiner', 'DB folders'))

	for folder in allDBFolders:
		folder = Path(folder)

		for path in folder.iterdir():
			if path.name == 'prefs.js': isProfile = True

		if folder == g.primaryDBFolder: continue  # Don't combine the Primary DB into itself! Waste of time.

		if isProfile == True:
			faviconsDB = [db for db in folder.iterdir() if db.name == 'favicons.sqlite']
			placesDB = [db for db in folder.iterdir() if db.name == 'places.sqlite']
			if len(faviconsDB) == 1: allDBsPre55.extend([faviconsDB[0], placesDB[0]])  # Have to reverse these as for some reason, faviconsDB becomes None otherwise
			elif len(faviconsDB) == 0: allDBsPre55.append(placesDB[0])

		elif isProfile == False:
			# recursive = g.combinerConfig.getint('History Combiner', 'Recursive')

			# if recursive == 0: folderDBs = [db for db in folder.glob('*.sqlite')]
			# elif recursive == 2: folderDBs = [db for db in folder.rglob('*.sqlite')] # rglob is recursive glob.

			folderDBs = [db for db in folder.rglob('*.sqlite')]  # rglob is recursive glob. Might as well look in all subfolders.
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
		curMain = sqlite3.connect(g.primaryDBFolder.joinpath('places.sqlite')).cursor()  # DB is presumed to have the name 'places.sqlite'.
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
	if url.find('://') != -1:
		partTwo = '://'
	elif url.find(':') != -1:
		partTwo = ':'

	(prefix, domain) = url.split(partTwo)[0:2]
	prefix += partTwo

	domain = domain.split('/')[0]
	if any(remPrefix in prefix for remPrefix in ('file', 'mega', 'place', 'javascript')): domain = ''

	return (prefix, domain)


def getMimeType(iconBlob):
	mimeType = 'image/'

	# In FF 55.0 and above all icons are converted to PNGs, except for SVGs which are left intact.
	# Sourcecode: https://searchfox.org/mozilla-central/source/toolkit/components/places/FaviconHelpers.cpp#1212
	if iconBlob[:4] == b'\x89PNG': mimeType += 'png'
	elif iconBlob[:5] in (b'<?xml', b'<svg '): mimeType += 'svg+xml'

	return mimeType


def resizeImage(iconBlob):
	# If the image is unreadable, return the image unchanged. In my test DB, there's only one image that fails like this.
	# This doesn't include SVGs which PIL apparently can't open anyway. Also, SVGs aren't converted to PNGs by Firefox so a direct copy is fine.
	if iconBlob[:5] in (b'<?xml', b'<svg '): return iconBlob

	try: img = Image.open(BytesIO(iconBlob))
	except: return iconBlob 


	sizeThresh = (32, 32)
	if  img.size <= sizeThresh: return iconBlob # Only want to resize images bigger than 32x32.
	img.thumbnail(sizeThresh)

	newIcon = BytesIO()
	img.save(newIcon, 'png')
	return newIcon.getvalue()


def convertToPNG(icon):
	defaultIconSizes = [256, 192, 144, 96, 64, 48, 32, 16]

	iconBlob = icon[7]
	if iconBlob[:5] in (b'<?xml', b'<svg '): return icon

	try: img = Image.open(BytesIO(iconBlob))
	except: return icon

	img.convert('RGBA')

	origSize = max(img.width, img.height)
	size = origSize
	for suppSize in defaultIconSizes:
		if suppSize <= origSize: size = suppSize; break

	icon[3] = size
	if (size == origSize or size < 16) and img.format == 'PNG': return icon # Some icons are smaller than 16px, convert these but don't resize them.

	img.thumbnail((size, size))

	newIcon = BytesIO()
	img.save(newIcon, 'png')
	icon[7] = newIcon.getvalue()
	return icon


def removePrefix(url):
	editedUrl = ''
	for prefix in ('https://', 'http://', 'ftp://'):
		if url.startswith(prefix): editedUrl = url[len(prefix):]

	if editedUrl.startswith('www.'): editedUrl = editedUrl[4:]
	return editedUrl


def getRoot(url):
	root = 0
	if url.count('/') == 3: root = 1
	return root


def insAttIDCheck(curMain, insertAttLastID, prop, newID):
	# 'Att' is 'Attribute'
	insAttID = curMain.execute('SELECT id from main.moz_anno_attributes where name = ?', prop).fetchone()
	if insAttID is None:
		try:
			curMain.execute('INSERT into main.moz_anno_attributes values (?, ?)', (insertAttLastID + newID, prop[0]))

		except Exception as e:
			insertException(curMain, {'new': (insertAttLastID + newID, prop[0]), 'dbExtName': 'main'}, e)

		insAttID = curMain.execute('SELECT id from main.moz_anno_attributes where name = ?', prop).fetchone()[0]
		newID += 1

	elif insAttID is not None: insAttID = insAttID[0]
	return (insAttID, newID)


def extAttIDCheck(curMain, prop):
	# 'Att' is 'Attribute'
	extAttID = curMain.execute('SELECT id from dbExt.moz_anno_attributes where name = ?', prop).fetchone()
	if extAttID is not None: return extAttID[0]


def insUpdFaviconIDs(curMain, newPlaces, extFaviconID):
	# There are some duplicate entries in 'moz_pages_w_icons'. They almost always lead to a non-existent 'moz_icons_to_pages' entry.
	# In one of my DBs (where I checked for these sorts of duplicates) I found one entry that pointed to the wrong icon. 
	# Luckily, Python dictionaries automatically discard duplicate keys. And since I'm looping through in order of 'id', this should be fine.

	# First check all non-root icons by linking all 'page_url' entries in 'moz_pages_w_icons' to an 'icon_url' in 'moz_icons'.
	# If there's no match, check all root icons. If no match still, return 'favicon_id' as None.
	# The link below for Firefox's sourcecode gave me the inspiration to account for root and non-root icons:
	# https://searchfox.org/mozilla-central/source/toolkit/components/places/FaviconHelpers.cpp#862
	def getFaviconID(placeURL):
		iconURL = pURLs_iURLs.get(placeURL)
		if iconURL is None:
			placeDomain = toDomain(placeURL)
			if placeDomain == '': return None

			iconURL = iconURLRoots.get(placeDomain)
			if iconURL is None: return None

		newIconID = oldIconURLs_IDs.get(iconURL)
		return newIconID

	def toDomain(url):
		if url.find('://') != -1: partTwo = '://'
		elif url.find(':') != -1: partTwo = ':'

		domain = url.split(partTwo)[1].split('/')[0]
		if domain[:4] == 'www.': domain = domain[4:]
		return domain


	sql = '''   SELECT wPages.page_url,
					   icons.icon_url
				 
				from   extIcons.moz_pages_w_icons wPages
					   inner join extIcons.moz_icons_to_pages toPages
					   on wPages.id = toPages.page_id
					   inner join extIcons.moz_icons icons
					   on icons.id = toPages.icon_id
						
				 order by wPages.id asc, icons.width asc'''

	pURLs_iURLs = getAllEntries(cur = curMain, SQL = sql, dictSchema = 'entry[0]: entry[1]')
	oldIconURLs_IDs = getAllEntries(cur = curMain, SQL = 'SELECT url, id from main.moz_favicons', dictSchema = 'entry[0]: entry[1]')

	iconURLs = getAllEntries(cur = curMain, SQL = 'SELECT icon_url from extIcons.moz_icons order by width asc', dictSchema = 'entry[0]: ""')
	iconURLRoots = {}
	for url in iconURLs.keys():
		# For some reason, not all root icons have their root value set properly. Hence, find the roots manually.
		if url.count('/') == 3: iconURLRoots.update({toDomain(url): url})


	# Sometimes the 'favicon_id' column in 'moz_places' remains intact even after the DB has been upgraded to FF 55.0 or above. 
	# This clause catches this instance. If the column is present, replace its (None) value with the new 'favicon_id'. If not, insert the new 'favicon_id'.
	for blockNum, blockData in newPlaces.items():
		checkStopPressed()

		for place in blockData.values():
			if extFaviconID == True: place[7] = getFaviconID(place[1])
			elif extFaviconID == False: place.insert(7, getFaviconID(place[1]))

			newPlaces[blockNum].update({place[0]: place})

	return newPlaces


def updateOldEntries(curMain, oldEntryTables, newEntries):
	# Updates globalVars.oldEntries to include all newly combined entries. This saves getting all the old (i.e. newly combined) entries repeatedly.
	pre55 = checkPre55(curMain, 'main')
	if   pre55 == False: placesSchema = 'entry[9]:  (entry[8], entry[0])'
	elif pre55 == True:  placesSchema = 'entry[10]: (entry[9], entry[0])'

	for table in oldEntryTables:
		schema = None
		oldEntries = g.oldEntries.get(table)

		if   table ==  'moz_hosts':                                                  schema =   'entry[1]:  ""'
		elif table ==  'moz_origins':                                                schema =  '(entry[1],  entry[2]): entry[0]'
		elif table in ('moz_pages_w_icons', 'moz_favicons', 'newlyCombinedIcons'):   schema =   'entry[1]:  entry[0]'
		elif table in ('moz_annos', 'moz_items_annos'):                              schema =  '(entry[1],  entry[2]): ""'
		elif table ==  'moz_historyvisits':                                          schema =   'entry[3]:  ""'
		elif table ==  'moz_icons':                                                  schema =  '(entry[1],  entry[3]): entry[0]'

		elif table ==  'moz_places':    schema = placesSchema
		elif table ==  'moz_bookmarks': newEntriesUpd = newEntries


		if schema is not None: 
			newEntriesUpd = {}
			exec('newEntriesUpd.update({' + schema + ' for entry in newEntries.values()})')

		g.oldEntries.update({table: {**oldEntries, **newEntriesUpd}})