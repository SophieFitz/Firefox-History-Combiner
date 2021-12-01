# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. 
# If a copy of the MPL was not distributed with this file, you can obtain one at http://mozilla.org/MPL/2.0/.

# Support for upgrading old history DBs (ones from before FF 55.0) has been removed as of FF 85.0.
# ESR 78.0 is the last online-searchable repository that contains the since-removed favicons conversion code.
# I have re-implemented this code in my function 'contertToPNG()', basing it on 'FetchAndConvertUnsupportedPayloads::ConvertPayload'.
# See: https://searchfox.org/mozilla-esr78/source/toolkit/components/places/FaviconHelpers.cpp#1221


from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, checkPre55
# from programFiles.combinerFunctions.Supplementary.exceptions import insertException
from programFiles.guiClasses.misc import checkStopPressed
from PIL import Image, ImageFile
from io import BytesIO

import programFiles.globalVars as g

ImageFile.LOAD_TRUNCATED_IMAGES = True # Ignore


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
	fixedUrl = ''
	for prefix in ('https://', 'http://', 'ftp://'):
		if url.startswith(prefix): fixedUrl = url[len(prefix):]

	if fixedUrl.startswith('www.'): fixedUrl = fixedUrl[4:]
	return fixedUrl


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