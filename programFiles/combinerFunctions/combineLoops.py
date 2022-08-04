import logging, time
import programFiles.globalVars as g

from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries, blocksToNormal, getNewID, remove_RemakeIndeces, getDBExtPath
from programFiles.combinerFunctions.Supplementary.getModifyValues import updateOldEntries
from programFiles.guiClasses.misc import checkStopPressed

combinerLogger = logging.getLogger('Combiner')

def combineLoops(curMain, allDetails):
	defaultValues = allDetails.get('defaultValues')
	tableName = allDetails.get('tableName')
	dbExtName = allDetails.get('dbExtName')
	dupExec = allDetails.get('duplicateExec')

	oldEntries = allDetails.get('oldEntries')
	newEntries = allDetails.get('newEntries')
	oldEntryTables = oldEntries.get('tables')
	
	insertDetails = allDetails.get('Insert')
	modifyDetails = allDetails.get('Modify')
	conditionalDetails = allDetails.get('Conditional')

	curMain.execute('begin')

	if oldEntries.get('entries') is not None: oldEntries = oldEntries.get('entries')
	elif oldEntryTables          is not None: oldEntries = g.oldEntries.get(oldEntryTables[0]) # Get old entries from globalVars

	if newEntries.get('entries') is not None: newEntries = newEntries.get('entries')
	elif newEntries.get('SQL')   is not None: newEntries = getAllEntries(cur = curMain, SQL = newEntries.get('SQL'), 
																		 dictSchema = newEntries.get('schema'), 
																		 blockSize = newEntries.get('blockSize'))

	# Set dupExec to empty string if it's None
	if dupExec is None: dupExec = ''

	lastID = getNewID(curMain, tableName)
	newEntriesEdited = {key: {} for key in newEntries.keys()}
	removeDuplicates = ('i = 0\n'
						'for blockNum, blockData in newEntries.items():\n\t'
							'checkStopPressed()\n\t'
								
							'for key, entry in blockData.items():\n\t\t'
								+ dupExec + '\n\t\t'
								'entry[0] = i + lastID; i += 1\n\t\t'
								'newEntriesEdited[blockNum].update({key: entry})')
	
	# Remove duplicate entries and set IDs.
	exec(removeDuplicates)

	
	# Insert new values 
	if insertDetails is not None:
		funcs = insertDetails.get('functions')
		cols = insertDetails.get('cols')
		pos = insertDetails.get('pos')

		# Insert values from functions, remove each pos and col.
		for func in funcs:
			for blockNum, blockData in newEntriesEdited.items():
				checkStopPressed()

				for key, entry in blockData.items():
					entry.insert(pos[0], func(entry[cols[0]]))
					newEntriesEdited[blockNum].update({key: entry})

			del cols[0]
			del pos[0]

		# If any values from pos and col are left, insert them
		for i in range(len(pos)):
			vals = cols
			for blockNum, blockData in newEntriesEdited.items():
				checkStopPressed()

				for key, entry in blockData.items():
					entry.insert(pos[i], vals[i])
					newEntriesEdited[blockNum].update({key: entry})
					if type(entry[0]) is str: del entry[0]


	# Modify existing values with functions
	if modifyDetails is not None:
		funcs = modifyDetails.get('functions')
		cols = modifyDetails.get('cols')

		for i in range(len(funcs)):
			for blockNum, blockData in newEntriesEdited.items():
				checkStopPressed()

				for key, entry in blockData.items():
					fromCol = cols[i][0]
					toCol = cols[i][1]
					entry[toCol] = funcs[i](entry[fromCol])
					newEntriesEdited[blockNum].update({key: entry})
		
	# Modify existing values with conditions
	if conditionalDetails is not None:
		for condition in conditionalDetails.values():
			condExec = ('for blockNum, blockData in newEntriesEdited.items():\n\t'
							'checkStopPressed()\n\t'

							'for key, entry in blockData.items():\n\t\t'
								+ condition + '\n\t\t'
								'newEntriesEdited[blockNum].update({key: entry})')

			exec(condExec)


	mainDBName, table = tableName.split('.')
	sql = f'pragma {mainDBName}.table_info({table})'

	insLen = len(curMain.execute(sql).fetchall())
	extLen = insLen # Default difference will be 0, therefore no values are changed.

	# If there are any new entries
	# Prior to this, 'newEntries' was polled for its length. However, this is not fullproof.
	if len(blocksToNormal(newEntries)) > 0:
		for value in blocksToNormal(newEntries).values(): extLen = len(value); break


	# Compare lengths and extend/shorten
	lenDiff = insLen - extLen

	# If lenDiff is more than 0, extend the entry
	if lenDiff > 0:
		for blockNum, blockData in newEntriesEdited.items():
			checkStopPressed()

			for key, entry in blockData.items():
				entry.extend(defaultValues[-lenDiff:])
				newEntriesEdited[blockNum].update({key: entry})

	# If lenDiff is less than 0, shorten the entry
	elif lenDiff < 0:
		for blockNum, blockData in newEntriesEdited.items():
			checkStopPressed()

			for key, entry in blockData.items():
				entry = entry[:lenDiff]
				newEntriesEdited[blockNum].update({key: entry})

	# Final loop: insert!
	remove_RemakeIndeces(curMain, mainDBName, table, 'Remove')
	insertSQL = ('?, ' * insLen)[:-2]
	insertSQL = f'INSERT into {mainDBName}.{table} values({insertSQL})'
	for blockData in newEntriesEdited.values():
		checkStopPressed()

		for key, entry in blockData.items():
			try:
				curMain.execute(insertSQL, entry)

			except Exception as e:
				raise g.insertException({'new': entry, 'dbExtPath': getDBExtPath(curMain, dbExtName), 'mainDBName': mainDBName, 'errorTrace': e, 'type': 'insertExc'})

	remove_RemakeIndeces(curMain, mainDBName, table, 'Remake')
	curMain.connection.commit()

	if oldEntryTables is not None:
		newEntriesEdited = blocksToNormal(newEntriesEdited)
		updateOldEntries(curMain, oldEntryTables, newEntriesEdited)