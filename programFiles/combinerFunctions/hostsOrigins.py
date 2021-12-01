from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, getNewID, checkPre12, checkPost62
from programFiles.combinerFunctions.Supplementary.otherFunctions import originsGetPrefixHost
from programFiles.combinerFunctions.combineLoops import combineLoops

import programFiles.globalVars as g
	

def mozHosts_Origins(curMain):
	dbInsPre12 = checkPre12(curMain, 'main')
	dbExtPre12 = checkPre12(curMain, 'dbExt')
	dbInsPost62 = checkPost62(curMain, 'main')
	dbExtPost62 = checkPost62(curMain, 'dbExt')

	# moz_hosts doesn't exist before FF 12.0 (db version 17), and moz_origins exists only after FF 62.0 (db version 52).
	# Therefore if both tables don't exist (which would only be the case in a db older than 17), move on.
	if dbInsPre12 == True or dbExtPre12 == True:
		print('\nEither DB extract or DB insert is older than Firefox 12.0\nand neither moz_hosts nor moz_origins exist in such databases. Skipping.\n')
		curMain.connection.commit()
		return

	# If moz_origins doesn't exist but moz_hosts does, that means the FF version is somewhere between 12.0 and 62.0 (db version 17 and 52).
	elif dbInsPre12 == False and dbExtPre12 == False:
		print('*moz_hosts*')

		# Default value for each column
		typed = 0
		prefix = None

		loopDetails = {'tableName': 'main.moz_hosts', 'dbExtName': 'dbExt', 'defaultValues': [typed, prefix],
					   'oldEntries': {'tables': ['moz_hosts']},
					   'newEntries': {'SQL': 'SELECT * from dbExt.moz_hosts', 'schema': 'entry[0]: list(entry)', 'blockSize': 1000},
					   'duplicateExec': 'if entry[1] in oldEntries.keys(): continue'}

		combineLoops(curMain, loopDetails)


	# If we're dealing with moz_origins in DB Extract and moz_hosts in DB Insert, then moz_origins needs converting to moz_hosts
	elif dbExtPost62 == True and dbInsPre12 == False:
		print('*moz_origins* ---> *moz_hosts*')
		newOrigins = getAllEntries(cur = curMain, SQL = 'SELECT id, host, frecency, prefix from dbExt.moz_origins order by prefix desc', 
								   dictSchema = 'entry[1]: list(entry)')

		oldHostNames = g.oldEntries.get('moz_hosts')

		newOriginsEdited = {}
		for origin in newOrigins.values():
			if origin[3] == "http://": origin[3] = None

			# 'moz_hosts' 'host' column entries never have 'www.', so this part is transferred to 'prefix'.
			if origin[1][:4] == "www.":
				origin[1] = origin[1][4:]
				if origin[3] is None: origin[3] = "www."
				elif origin[3] == "https://": origin[3] += "www."

			# Skip the entry if the host already exists, is blank or its prefix is none of the below (prefix is very often blank, i.e. 'None').
			if (origin[1] in oldHostNames.keys() or origin[1] == ""
				or origin[3] not in ("www.", "https://", "https://www.", None)): continue

			newOriginsEdited.update({origin[1]: origin})

		newOriginsEdited = getAllEntries(entries = newOriginsEdited, blockSize = 1000)

		# Default value for each column
		typed = 0

		loopDetails = {'tableName': 'main.moz_hosts', 'dbExtName': 'dbExt', 'defaultValues': [],
					   'oldEntries': {'tables': ['moz_hosts']},
					   'newEntries': {'entries': newOriginsEdited},
					   'Insert': {'functions': [], 'pos': [3], 'cols': [typed]}}
				  
		combineLoops(curMain, loopDetails)


	# It doesn't matter if moz_hosts exists or not in this case, because if both tables exist in either DB 
	# then the moz_hosts table will have been migrated across and its contents transferred to moz_origins in the process.
	# But equally if it's a newly created DB (one newer than or equal to version 52) which doesn't have moz_hosts, it doesn't matter. 
	# The table is either absent (case of the latter), or its contents are absent (case of the former).
	# But, if the DB has been downgraded to pre 62 but post 55.... It would never be downgraded to pre 55 in general as none of the icons would be present!
	# Although tbf, someone may try it and discover this...
	elif dbInsPost62 == True and dbExtPost62 == True:
		print('*moz_origins*')

		loopDetails = {'tableName': 'main.moz_origins', 'dbExtName': 'dbExt', 'defaultValues': [],
					   'oldEntries': {'tables': ['moz_origins']},
					   'newEntries': {'SQL': 'SELECT * from dbExt.moz_origins', 'schema': 'entry[0]: list(entry)', 'blockSize': 1000}}

		# 'moz_origins' added more 'prefix' values, meaning that there can be 2 or more of the same 'host' name with different 'prefix' values.
		# Therefore it is necessary to check against both columns for duplicates.
		loopDetails.update({'duplicateExec': 'if (entry[1], entry[2]) in oldEntries.keys(): continue'})
		combineLoops(curMain, loopDetails)


	# If DB extract is below FF 62.0 and DB Insert is above, 'moz_hosts' needs converting to 'moz_origins'.
	elif dbInsPost62 == True and dbExtPost62 == False:
		print('*moz_hosts* ---> *moz_origins*')

		placesForOriginsGet = curMain.execute('SELECT id, url, frecency from dbExt.moz_places').fetchall()
		placesForOrigins = {originsGetPrefixHost(place[1]): [place[0], *originsGetPrefixHost(place[1]), place[2]] for place in placesForOriginsGet}
		placesForOrigins = getAllEntries(entries = placesForOrigins, blockSize = 1000)

		loopDetails = {'tableName': 'main.moz_origins', 'dbExtName': 'dbExt', 'defaultValues': [],
					   'oldEntries': {'tables': ['moz_origins']},
					   'newEntries': {'entries': placesForOrigins},
					   'duplicateExec': 'if tuple(entry[1:3]) in oldEntries.keys(): continue'}

		combineLoops(curMain, loopDetails)