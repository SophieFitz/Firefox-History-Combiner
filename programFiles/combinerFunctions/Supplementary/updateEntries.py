# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. 
# If a copy of the MPL was not distributed with this file, you can obtain one at http://mozilla.org/MPL/2.0/.

# 'updateFrecency()' is a re-implentation of 'CalculateFrecencyFunction'.
#  My implementation includes provision for moz_hosts and moz_origins.
#  See: https://searchfox.org/mozilla-central/source/toolkit/components/places/SQLFunctions.cpp#540


from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, getNewID, checkPost62, columnPresent, remove_RemakeIndeces
from programFiles.combinerFunctions.Supplementary.getModifyValues import convertToPNG, getRoot
from programFiles.combinerFunctions.Supplementary.otherFunctions import originsGetPrefixHost
from programFiles.combinerFunctions.Supplementary.urlHashing import getHash
from programFiles.guiClasses.misc import checkStopPressed

from math import ceil
from time import time
from datetime import datetime

import programFiles.globalVars as g


def updateFrecency(curToUpdate, updateFrecSetting, *oldPlaceGUIDs):
	# Note: The only element of frecency updating not currently implemented is the source redirect bonus.
	print('\n\nUpdating frecency')
	
	curToUpdate.execute('begin')
	
	foreignCountPresent = columnPresent(curToUpdate, 'main', 'moz_places', 'foreign_count')
	dbUpdPost62 = checkPost62(curToUpdate, 'main')

	bonusVisited = {1: 100, 2: 2000, 3: 75, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0} # Link, Typed, Bookmark, Embed, RedirPerm, RedirTemp, Download, FramedLink, Reload
	bonusUnvisited = {1: 200, 3: 140} # Unvisited Typed, Unvisited Bookmark
	redirBonus = 25 # Redir source bonus

	oneDayMicros = 86400000000 # Number of microseconds in 1 day
	currTimeMicros = time() * 1000000

	tenVisitsSQL = 'SELECT visit_date, visit_type from main.moz_historyvisits where place_id = ? group by visit_date order by visit_date desc limit 10'


	def toDomain(url):
		if url.find('https://') != -1: scheme = 'https://'
		elif url.find('http://www.') != -1: scheme = 'www.'
		elif url.find('https://www.') != -1: scheme = 'https://www.'
		else: scheme = None

		if scheme not in ('www.', 'https://', 'https://www.', None): return None

		if url.find('://') == -1: domain = url.split(':')[1]
		elif url.find('://') != -1: domain = url.split('://')[1]

		return domain

	def newFrecencyScore(place):
		tenVisitsGet = curToUpdate.execute(tenVisitsSQL, (place[0],)).fetchall()
		if len(tenVisitsGet) == 0:
			visitsPoints = 0
			if foreignCountPresent == True: # DBs older than FF 34.0 won't have 'foreign_count'
				if place[4] == 0 and place[6] == 1:
					visitsPoints += bonusUnvisited[0]
					if place[10] == 1: # If bookmark exists, add the bonus for unvisited bookmarks
						visitsPoints += bonusUnvisited[1]

				elif place[4] == 0 and place[10] == 1:
					visitsPoints += bonusUnvisited[1]
					if place[6] == 1: # If it's typed as well, add the typed bonus
						visitsPoints += bonusUnvisited[0]

			elif foreignCountPresent == False:
				if place[4] == 0 and place[6] == 1: visitsPoints += bonusUnvisited[0]


			# Because it's an unvisited site, the most recent bucket weighting applies (according to the Firefox source) hence * 100.
			if visitsPoints == 0: place[7] = -1
			elif visitsPoints > 0: place[7] = ceil(1 * ceil((visitsPoints / 100.0)) * 100) # Multiplied by 1, for 1 visit count


		elif len(tenVisitsGet) >= 1:
			visitsPoints = 0
			tenVisits = {visit[0]: visit[1] for visit in tenVisitsGet}
			for date, type in tenVisits.items():
				if   currTimeMicros-date <= 4*oneDayMicros:                                                 weight = 100
				elif (currTimeMicros-date > 4*oneDayMicros)  and (currTimeMicros-date <= 14*oneDayMicros):  weight = 70
				elif (currTimeMicros-date > 14*oneDayMicros) and (currTimeMicros-date <= 31*oneDayMicros):  weight = 50
				elif (currTimeMicros-date > 31*oneDayMicros) and (currTimeMicros-date <= 90*oneDayMicros):  weight = 30
				elif (currTimeMicros-date > 90*oneDayMicros):                                               weight = 10

				visitsPoints += (bonusVisited[type] / 100.0) * weight
	 
			if visitsPoints == 0: place[7] = -1
			elif visitsPoints > 0: place[7] = ceil(place[4] * ceil(visitsPoints) / len(tenVisits)) # New frecency score


		# Updating 'moz_hosts' frecency
		if dbUpdPost62 == False:
			domain = toDomain(place[1])
			if domain not in hostUpdatesDict.keys(): hostUpdatesDict.update({domain: [place[7]]})
			elif domain in hostUpdatesDict.keys(): hostUpdatesDict[domain].append(place[7])
			elif domain is None: pass # For 'moz_hosts', don't include blank domains.

		# Updating 'moz_origins' frecency
		elif dbUpdPost62 == True:
			prefix, domain = originsGetPrefixHost(place[1])

			if (prefix, domain) not in hostUpdatesDict.keys(): hostUpdatesDict.update({(prefix, domain): [place[7]]})
			elif (prefix, domain) in hostUpdatesDict.keys(): hostUpdatesDict[(prefix, domain)].append(place[7])

		return place[7]


	hostUpdatesDict = {}
	allPlaces = getAllEntries(cur = curToUpdate, SQL = 'SELECT * from main.moz_places', dictSchema = 'entry[0]: list(entry)', blockSize = 1000)
	allPlacesEdited = allPlaces

	# If the 'Update only new entries` frecency' option is checked, skip all the old entries
	if updateFrecSetting == 1:
		if   dbInsPre55 == True:  guidCol = 10
		elif dbInsPre55 == False: guidCol = 9

		allPlacesEdited = {key: {} for key in allPlaces.keys()}
		for blockNum, blockData in allPlaces.items():
			checkStopPressed()

			for key, place in blockData.items():
				if place[guidCol] in oldPlaceGUIDs.keys(): continue # Original entries' frecency values will NOT be updated, only new ones.
				allPlacesEdited[blockNum].update({key, place})

		allPlaces = allPlacesEdited


	remove_RemakeIndeces(curToUpdate, 'main', 'moz_places', 'Remove')
	for blockData in allPlacesEdited.values():
		checkStopPressed()

		for place in blockData.values():
			# No need to update frecency for sites that have only been visited once, or ones that have a frecency of 0 (invalid)
			if place[7] == 0 or place[4] == 1: continue

			# print(place[1])
			newFrecency = newFrecencyScore(place)
			curToUpdate.execute('UPDATE main.moz_places set frecency = ? where id = ?', (newFrecency, place[0]))

	remove_RemakeIndeces(curToUpdate, 'main', 'moz_places', 'Remake')


	if dbUpdPost62 == False:
		oldHostNames = {}
		if updateFrecSetting == 1: oldHostNames = getAllEntries(cur = curToUpdate, SQL = 'SELECT host from main.moz_hosts', dictSchema = 'entry[0]: ""')

		for domain, frecency in hostUpdatesDict.items():
			if domain in oldHostNames.keys(): continue

			maxFrecency = max(frecency)
			frecencyIsZero = True

			# Check for '0' value frecency. '0' means it is invalid and won't be displayed.
			for value in frecency: 
				if value != 0: 
					frecencyIsZero = False
					break

			# If any frecency values aren't 0, that means the frecency should never be 0. If the max() still says it is 0, make it -1. Otherwise, leave it.
			if frecencyIsZero == False: 
				if maxFrecency == 0: frecency = -1
				else: frecency = maxFrecency

			elif frecencyIsZero == True: frecency = maxFrecency
			curToUpdate.execute('UPDATE main.moz_hosts set frecency = ? where host = ?', (frecency, domain))

	elif dbUpdPost62 == True:
		oldPrefixesHosts = {}
		if updateFrecSetting == 1: 
			oldPrefixesHosts = getAllEntries(cur = curToUpdate, SQL = 'SELECT prefix, host from main.moz_origins', dictSchema = 'tuple(entry): ""')

		for key, frecency in hostUpdatesDict.items():
			prefix, domain = key
			if (prefix, domain) in oldPrefixesHosts.keys(): continue

			# 'moz_origins' frecency scores work by taking the sum of the place frecencies, rather than the max.
			# See: https://searchfox.org/mozilla-central/source/toolkit/components/places/Database.cpp#2392
			sumFrecency = sum(frecency)

			# Check for '0' value frecency. '0' means it is invalid and won't be displayed.
			for value in frecency: 
				if value != 0: 
					frecencyIsZero = False
					break

			# If any frecency values aren't 0, that means the frecency should never be 0. If the max() still says it is 0, make it -1. 
			# Some values also seem to become less than -1. Set those anomolies to -1 as well. Otherwise, leave it.
			if frecencyIsZero == False: 
				if sumFrecency == 0 or sumFrecency < -1: frecency = -1
				else: frecency = sumFrecency

			elif frecencyIsZero == True: frecency = sumFrecency
			curToUpdate.execute('UPDATE main.moz_origins set frecency = ? where host = ? and prefix = ?', (frecency, domain, prefix))

	curToUpdate.connection.commit()


def updateVisit_foreignCounts(curToUpdate):
	# print('Updating visit_count and foreign_count columns in moz_places')

	curToUpdate.execute('begin')
	updateVisitCountsGet = curToUpdate.execute('SELECT place_id, count(place_id) from moz_historyvisits group by place_id').fetchall()
	updateVisitCounts = [(visitCount[1], visitCount[0]) for visitCount in updateVisitCountsGet]

	# If any of the DBs to Extract were below FF 34.0, the column foreign_count won't have existed. This is pertinent to bookmarks. 
	# The column needs recalculating, which is what this clause does.
	sql = 'SELECT p.id from moz_places p inner join moz_bookmarks b on p.id = b.fk'
	newForeignCounts = curToUpdate.execute(sql).fetchall()

	curToUpdate.executemany('UPDATE moz_places set foreign_count = 1 where id = ?', (newForeignCounts))
	curToUpdate.executemany('UPDATE moz_places set visit_count = ? where id = ?', updateVisitCounts)
	curToUpdate.connection.commit()


def updatePlaceURLHashes(curToUpdate):
	# Only update the column if it exists. Pre FF 50.0 it doesn't.
	if columnPresent(curToUpdate, 'main', 'moz_places', 'url_hash') == True:
		allPlaces = getAllEntries(cur = curToUpdate, SQL = 'SELECT * from main.moz_places where url_hash = 0', 
								  dictSchema = 'entry[0]: list(entry)', blockSize = 100)

		placesToUpdate = []

		for blockData in allPlaces.values():
			checkStopPressed()

			for place in blockData.values():
				placesToUpdate.append((getHash(place[1]), place[0]))


		curToUpdate.executemany('UPDATE moz_places set url_hash = ? where id = ?', placesToUpdate)
		curToUpdate.connection.commit()


def updateIcons_toPages(curToUpdate, dbInsPre55):
	curToUpdate.execute('begin')
	secondsInWeek = 7 * 24 * 60 * 60

	if dbInsPre55 == False:
		print('\nRemoving redundant moz_icons_to_pages entries')
		allIcons = getAllEntries(cur = curToUpdate, SQL = 'SELECT * from mainIcons.moz_icons', dictSchema = 'entry[0]: list(entry)')
		allWPages = getAllEntries(cur = curToUpdate, SQL = 'SELECT * from mainIcons.moz_pages_w_icons', dictSchema = 'entry[0]: list(entry)')
		allToPages = getAllEntries(cur = curToUpdate, SQL = 'SELECT * from mainIcons.moz_icons_to_pages', dictSchema = 'tuple(entry): ""', blockSize = 1000)

		for toPage in allToPages[1].keys(): insLen = len(toPage); break
		insertSQL = ('?, ' * insLen)[:-2]
		insertSQL = f'INSERT or IGNORE into mainIcons.moz_icons_to_pages values({insertSQL})'

		curToUpdate.execute('DELETE from mainIcons.moz_icons_to_pages')
		toPagesEdited = {}

		for blockNum, blockData in allToPages.items():
			checkStopPressed()

			for toPage in blockData.keys():
				wPage = allWPages.get(toPage[0])
				icon = allIcons.get(toPage[1])

				if wPage is None or icon is None: continue
				curToUpdate.execute(insertSQL, toPage)
		

		print('Converting moz_icons payloads')
		allIcons = getAllEntries(entries = allIcons, blockSize = 500)
		allIconsEdited = {key: {} for key in allIcons.keys()}

		for blockNum, blockData in allIcons.items():
			checkStopPressed()

			for icon in blockData.values():
				icon = convertToPNG(icon)
				allIconsEdited[blockNum].update({icon[0]: icon})


		print('\nUpdating columns')
		sql = 'UPDATE moz_icons set width = ?, root = ?, expire_ms = ?, data = ? where id = ?'

		for blockData in allIconsEdited.values():
			checkStopPressed()

			for icon in blockData.values():
				if icon[6] == 0: icon[6] = int((datetime.now().timestamp() + secondsInWeek) * 1000)
				icon[4] = getRoot(icon[1])

				curToUpdate.execute(sql, (icon[3], icon[4], icon[6], icon[7], icon[0]))

	elif dbInsPre55 == True:
		print('Updating columns')
		allIconExpiries = getAllEntries(cur = curToUpdate, SQL = 'SELECT id, expiration from moz_favicons', dictSchema = 'entry[0]: entry[1]')

		for iconID, expiry in allIconExpiries.items():
			if expiry == 0: expiry = int((datetime.now().timestamp() + secondsInWeek) * 1000) * 1000
			curToUpdate.execute('UPDATE moz_favicons set expiration = ? where id = ?', (expiry, iconID))


	curToUpdate.connection.commit()