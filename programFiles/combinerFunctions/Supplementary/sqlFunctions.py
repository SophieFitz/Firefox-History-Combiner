from programFiles.guiClasses.misc import checkStopPressed
import programFiles.globalVars as g
import sqlite3


def getAllEntries(**args):
	cur = args.get('cur')
	SQL = args.get('SQL')
	dictSchema = args.get('dictSchema')
	blockSize = args.get('blockSize')
	entries = args.get('entries')

	# Get new entries from DB if cur is not None and entries is None
	# If entries have not been passed in, get new entries. The only time they are passed in is when they need converting to blocks.
	if cur is not None:
		entries = {}
		entriesGet = cur.execute(SQL).fetchall()
		mainKeyCol = dictSchema.split(':')[0]

		# If there are no entries in DB insert, get columns manually? (maybe just get them this way anyway and don't bother with sqlite3.Row?)
		# colNames = entriesGet[0].keys()


		entriesExec = ( 'i = 1\n'
						'for entry in entriesGet:\n\t'
							# Remove duplicate entries as dicts overwrite old duplicates with new ones rather than skipping the new ones.
						   'if ' + mainKeyCol + 'in entries.keys(): continue\n\t'
					       'entries.update({' + dictSchema + '})\n\t'
					       'i += 1\n\t'
					       'if i % 1000 == 0:\n\t\t' # Check for stop pressed after every 1000 entries to ensure Stop button's responsiveness.
							  'checkStopPressed()\n\t\t')

		exec(entriesExec)

	# Convert entries to blocks if blockSize is not None.
	if blockSize is not None:
		entriesAsBlocks = {}
		blocksExec = ('i = 1\n'
					  'block = 1\n'
					  'for key, entry in entries.items():\n\t'
						  'if entriesAsBlocks.get(block) == None: entriesAsBlocks.update({block: {}})\n\t'
						   
						  'entriesAsBlocks[block].update({key: entry})\n\t'
						  'i += 1\n\t'
						   
						  'if i % blockSize == 0:\n\t\t' # Move on to next block
							  'checkStopPressed()\n\t\t'
							  'block += 1')

		exec(blocksExec)
		entries = entriesAsBlocks

	return entries

def blocksToNormal(entries):
	entriesNormalised = {}
	for blockData in entries.values():
		entriesNormalised.update({**blockData})

	return entriesNormalised

def checkUTF8(cur, origSQL, dictSchema, colsToCheck, *blockSize):
	# This function takes a dict of entries without a specified column(s) and combines it
	# with a dict that has the column(s) but is set to ignore all non-utf-8 encodable characters.
	# If the entry was ignored then its value is reset to default.

	# May need to adjust function if the primary key isn't entry[0]...

	
	def insertCol(schema, insCol):
		schema.insert(index, insCol)

		schemaStr = ''
		for col in schema: schemaStr += f'{col}, '
		schemaStr = schemaStr[:-2]
		return schemaStr

	tableSchema = cur.execute(origSQL).fetchone().keys()
	tableSchemaStr = ''
	missingCols = {}

	for col, info in colsToCheck.items():
		try: index = tableSchema.index(col)
		except: missingCols.update({col: info}); continue

		colsToCheck[col].insert(0, index)
		del tableSchema[index]


	for col in tableSchema: tableSchemaStr += f'{col}, '
	tableSchemaStr = tableSchemaStr[:-2]
	SQL = origSQL.replace('*', tableSchemaStr) # Won't always be *... may need to alter this in future

	# Has all entries but minus a certain column(s).
	mainEntries = getAllEntries(cur = cur, SQL = SQL, dictSchema = dictSchema)

	# See: https://stackoverflow.com/questions/23508153/python-encoding-could-not-decode-to-utf8/58891247#58891247
	g.dbMain.text_factory = lambda col: col.decode(errors = 'ignore')
	tempCur = g.dbMain.cursor()
	for col, info in colsToCheck.items():
		# Only copy the column(s) if they are present in dbMain
		if col in missingCols.keys(): continue

		index, defValue = info

		SQL = origSQL.replace('*', insertCol(tableSchema, col)) # Again, won't necessarily be a *....

		# Has all columns but minus non-utf8 entries.
		colEntries = getAllEntries(cur = tempCur, SQL = SQL, dictSchema = dictSchema)

		skippedEntries = {key: value for key, value in mainEntries.items() if key not in colEntries.keys()}

		# The missing column(s) are copied into the mainEntries dict!
		for entry in colEntries.values():
			mainEntries[entry[0]].insert(index, entry[index])

		for entry in skippedEntries.values():
		# If the entry was skipped because of invalid UTF-8 encoding, populate it with its default value instead.
			entry[index] = defValue
			exec('mainEntries.update({' + dictSchema + '})')


	g.dbMain.text_factory = str
	tempCur.close()

	if blockSize:
		mainEntries = getAllEntries(entries = mainEntries, blockSize = blockSize[0])
	
	return mainEntries

def getNewID(cur, table):
	SQL = f'SELECT max(id) from {table}'
	newID = cur.execute(SQL).fetchone()[0]

	if newID is None: newID = 1
	elif newID is not None: newID += 1

	return newID

def tablePresent(cur, dbName, tableToCheck):
	SQL = f'SELECT exists (SELECT name from {dbName}.sqlite_master where type = ? and name = ?)'
	tableExists = cur.execute(SQL, ('table', tableToCheck)).fetchone()[0]
	
	return tableExists

def columnPresent(cur, dbName, table, colToCheck):
	tableExists = tablePresent(cur, dbName, table)

	if tableExists == False: return False
	elif tableExists == True:
		SQL = f'pragma {dbName}.table_info({table})'
		tableColsGet = cur.execute(SQL).fetchall()
		tableCols = [col[1] for col in tableColsGet]

		if colToCheck in tableCols: return True
		else:                       return False

def getDBExtPath(cur, dbExtName):
	dbList = cur.execute('pragma database_list').fetchall()
	for db in dbList: 
		if db[1] == dbExtName: dbExtPath = db[2]

	return dbExtPath

def removeFaviconIDCol(cur):
	cur.execute('pragma foreign_keys=off')
	cur.execute('begin')

	placesCreate = cur.execute('SELECT sql from sqlite_master where type = ? and name = ?', ('table', 'moz_places')).fetchone()[0]
	placesCreate = placesCreate.replace('moz_places', 'placesPlaceholder')
	placesCreate = placesCreate.replace(', favicon_id INTEGER', '')

	placesColsGet = cur.execute('pragma table_info(moz_places)').fetchall()
	placesCols = [col[1] for col in placesColsGet if col[1] != 'favicon_id']
	colsStr = ''

	for col in placesCols: colsStr += f'{col}, '
	colsStr = colsStr[:-2] # Get rid of trailing comma and space.

	newTableSQL = f'INSERT into placesPlaceholder({colsStr}) SELECT {colsStr} from moz_places'
	cur.execute(placesCreate)
	cur.execute(newTableSQL)
	cur.execute('drop table moz_places')
	cur.execute('alter table placesPlaceholder rename to moz_places')

	cur.execute('pragma foreign_keys=on')
	cur.connection.commit()

def removeReorderColumns(cur, dbName, tableName, columns):
	# Remove and/or change the order of the given table's column(s).

	cur.execute('pragma foreign_keys=off')
	cur.connection.commit()
	cur.execute('begin')

	sql = f'SELECT sql from {dbName}.sqlite_master where type = ? and name = ?'
	createTableSQL = cur.execute(sql, ('table', f'{tableName}')).fetchone()[0]
	createTableSQL = createTableSQL.replace(tableName, 'tablePlaceholder')
	
	sql = f'pragma {dbName}.table_info({tableName})'
	colsGet = cur.execute(sql).fetchall()
	cols = None


	colsToRemove = columns.get('remove')
	colsToReorder = columns.get('reorder')

	if colsToRemove is not None:
		for col in colsToRemove:
			createTableSQL = createTableSQL.replace(col, '')

		cols = [col[1] for col in colsGet if col[1] not in colsToRemove]

	if colsToReorder is not None:
		# If I'm doing multiple columns at once, need to factor-in the altered numbers of the columns.
		if cols is None: cols = [col[1] for col in colsGet]
		createTableCols = createTableSQL.split('(', 1)[1].split(',')
		createTableCols[-1] = createTableCols[-1][:-1] # Get rid of trailing parentheses bracket.

		for colName_Type, colTo in colsToReorder.items():
			colName = colName_Type.split(' ')[0]
			if colName not in cols: continue

			colFrom = cols.index(colName)
			if colTo == colFrom: continue # If the column is already correctly positioned, continue

			del createTableCols[colFrom]
			del cols[colFrom]

			createTableCols.insert(colTo, colName_Type)
			cols.insert(colTo, colName)

		createTableSQL = f'CREATE TABLE {dbName}.tablePlaceholder ('
		for colSQL in createTableCols: createTableSQL += f'{colSQL.strip()}, '
		createTableSQL = createTableSQL[:-2] + ')' # Add parentheses back in.

		
	colsStr = ''
	for col in cols: colsStr += f'{col}, '
	colsStr = colsStr[:-2] # Get rid of trailing comma and space.

	newTableSQL = f'INSERT into {dbName}.tablePlaceholder({colsStr}) SELECT {colsStr} from {dbName}.{tableName}'
	cur.execute(createTableSQL)
	cur.execute(newTableSQL)

	sql = f'drop table {dbName}.{tableName}'
	sql2 = f'alter table {dbName}.tablePlaceholder rename to {tableName}'
	cur.execute(sql)
	cur.execute(sql2)


	cur.execute('pragma foreign_keys=on')
	cur.connection.commit()

def allOldEntriesGet(curMain):
	print('\nGetting all old entries in preparation for combining')

	# Reset to empty
	g.oldEntries = {}

	pre12 = checkPre12(curMain, 'main')
	pre55 = checkPre55(curMain, 'main')
	post62 = checkPost62(curMain, 'main')
	
	hosts_Origins = {}
	bookmarksGUID = columnPresent(curMain, 'main', 'moz_bookmarks', 'guid')

	tables_sqlSchema = {'moz_places':               ['SELECT guid, last_visit_date, id from main.moz_places',       'entry[0]: (entry[1], entry[2])',
													{'description': [None]}], 

						'moz_historyvisits':        ['SELECT visit_date from main.moz_historyvisits',               'entry[0]: ""'],
						'moz_annos':                ['SELECT place_id, anno_attribute_id from main.moz_annos',      'tuple(entry): ""'],
						'moz_items_annos':          ['SELECT item_id, anno_attribute_id from main.moz_items_annos', 'tuple(entry): ""']}

	if bookmarksGUID == True: 
		tables_sqlSchema.update({'moz_bookmarks':   ['SELECT guid from main.moz_bookmarks', 						'entry[0]: ""']})

	if pre12 == False:
		hosts_Origins = {'moz_hosts':               ['SELECT host from main.moz_hosts',                             'entry[0]: ""']}

	elif post62 == True:
		hosts_Origins = {'moz_origins':             ['SELECT prefix, host, id from main.moz_origins',              '(entry[0], entry[1]): entry[2]']}

	if pre55 == True:
		tables_sqlSchema = {'moz_favicons':         ['SELECT url, id from main.moz_favicons',                       'entry[0]: entry[1]'],
													**hosts_Origins, **tables_sqlSchema}

	elif pre55 == False:
		tables_sqlSchema = {'moz_icons':            ['SELECT icon_url, width, id from mainIcons.moz_icons',        '(entry[0], entry[1]): entry[2]'],
							'newlyCombinedIcons':   ['SELECT icon_url, id from mainIcons.moz_icons',                'entry[0]: entry[1]'],
							'moz_pages_w_icons':    ['SELECT page_url, id from mainIcons.moz_pages_w_icons',        'entry[0]: entry[1]'],
													**hosts_Origins, **tables_sqlSchema}

	for table, info in tables_sqlSchema.items():
		if len(info) == 2: entries = getAllEntries(cur = curMain, SQL = info[0], dictSchema = info[1])
		elif len(info) == 3: entries = checkUTF8(curMain, info[0], info[1], info[2]) # Check and get utf-8 encodable entries
		
		g.oldEntries.update({table: entries})

def checkPre12(cur, dbName):
	originsExist = tablePresent(cur, dbName, 'moz_origins')
	hostsExist = tablePresent(cur, dbName, 'moz_hosts')

	if hostsExist == False and originsExist == False:  return True # When neither moz_hosts or moz_origins exist, DB is pre FF 12.0
	elif hostsExist == True and originsExist == False: return False # If moz_hosts exists but moz_origins doesn't, DB is between FF 12.0 and FF 62.0

def checkDBPost34():
	primaryDBPath = g.primaryDBFolder.joinpath('places.sqlite')
	# If the user has selected the primary DB folder without first putting a DB inside of it, 
	# this function returns True to prevent the FF 21.0 Downloads message being unnecessarily displayed.
	if primaryDBPath.is_file() == False: return True

	dbMain = sqlite3.connect(primaryDBPath)
	curMain = dbMain.cursor()

	dbMainPost34 = columnPresent(curMain, 'main', 'moz_places', 'foreign_count')
		
	dbMain.commit()
	curMain.close()

	return dbMainPost34

def checkPre55(cur, dbName):
	# If favicons table is empty, FF version is definitely 55.0 or higher.
	# If the table isn't there at all, then the DB was created in an FF version higher than 55.0. 
	# Both instances are covered by this function.

	tableExists = tablePresent(cur, dbName, 'moz_favicons')

	if tableExists == True:
		# Should be either False, or have a value (making it not False, but not True either....)
		entriesExistSQL = f'SELECT count(1) from {dbName}.moz_favicons'
		entriesExist = cur.execute(entriesExistSQL).fetchone()[0]

		if entriesExist != False:   return True # If there are entries, it is definitely pre FF 55 (moz_favicons always has 4 or 5 entries by default).
		elif entriesExist == False: return False # Post FF 55, the table may exist but without its entries.

	elif tableExists == False:      return False # If the table doesn't exist it's definitely a post FF 55 DB.

def checkPost62(cur, dbName):
	# moz_origins only exists in DBs from FF 62.0 and above.
	# moz_hosts is present before FF 62.0. It always has at least 1 entry. If a DB is upgraded to the FF 62.0 schema, 
	# moz_hosts is transferred to moz_origins. The original table is preserved, its contents are deleted.

	return tablePresent(cur, dbName, 'moz_origins') # Return either True or False

def checkPost96(cur, dbName): 
	# Firefox 96 has just entered Beta (07-12-21). I frequently check the source code and they recently added this:
	# https://searchfox.org/mozilla-central/source/toolkit/components/places/Database.cpp#2320
	return columnPresent(cur, dbName, 'moz_places', 'site_name')

def remove_RemakeIndeces(cur, mainDBName, table, action):
	# For a significant performance increase, remove all non-unique indeces from the required table.
	# Specifically, remove the indeces before all INSERT statements. Then recreate them afterwards to avoid any potential problems. 
	# Indeces increase performance of SELECT queries and WHERE clauses. They slow down INSERT and UPDATE statements significantly.
	# See: https://www.tutorialspoint.com/sqlite/sqlite_indexes.htm

	if action == 'Remove':
		nonUniqueSQL = f'pragma {mainDBName}.index_list({table})'
		nonUniqueIndecesGet = cur.execute(nonUniqueSQL).fetchall()

		g.nonUniqueIndeces = {entry[1] for entry in nonUniqueIndecesGet if entry[2] == 0}

		sql = f'SELECT name, sql from {mainDBName}.sqlite_master where type = ? and tbl_name = ?'
		g.indexName_SQL = cur.execute(sql, ('index', table)).fetchall()

		for i in g.indexName_SQL:
			if i[0] in g.nonUniqueIndeces:
				dropSQL = f'drop index {i[0]}'
				cur.execute(dropSQL)

	elif action == 'Remake':
		for i in g.indexName_SQL:
			if i[0] in g.nonUniqueIndeces:
				index = i[1].replace('INDEX ', f'INDEX {mainDBName}.')
				cur.execute(index)