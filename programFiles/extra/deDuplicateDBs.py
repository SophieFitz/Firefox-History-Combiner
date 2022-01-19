import sqlite3


def getAllEntries(**args):
    cur = args.get('cur')
    SQL = args.get('SQL')
    dictSchema = args.get('dictSchema')

    entries = {}
    entriesGet = cur.execute(SQL).fetchall()
    mainKeyCol = dictSchema.split(':')[0]

    entriesExec = ('i = 1\n'
                   'for entry in entriesGet:\n\t'
                   'if ' + mainKeyCol + 'in entries.keys(): continue\n\t'
                                        'entries.update({' + dictSchema + '})\n\t'
                                                                          'i += 1\n\t')
    exec(entriesExec)
    return entries


dbMain = sqlite3.connect('places.sqlite')
curMain = dbMain.cursor()
curMain.execute('attach "favicons.sqlite" as mainIcons')

allVisits = getAllEntries(cur = curMain, SQL ='SELECT * from main.moz_historyvisits order by id desc', dictSchema ='entry[0]: list(entry)')

dupSQL = 'SELECT from_visit, place_id, visit_date, id, COUNT(*) Num FROM moz_historyvisits group by from_visit, place_id, visit_date having Num > 1'
duplicateVisits = getAllEntries(cur = curMain, SQL = dupSQL, dictSchema ='(entry[0], entry[1], entry[2]): [entry[3], entry[4]]')


done = []
for visit in allVisits.values():
    if (visit[1], visit[2], visit[3]) in duplicateVisits.keys() and (visit[1], visit[2], visit[3]) not in done:
        lowestID, numDuplicates = duplicateVisits[(visit[1], visit[2], visit[3])][:]
        curMain.execute('DELETE from main.moz_historyvisits where from_visit = ? and place_id = ? and visit_date = ? and id > ?', (visit[1], visit[2], visit[3], lowestID))
        done.append((visit[1], visit[2], visit[3]))


curMain.connection.commit()
curMain.close()