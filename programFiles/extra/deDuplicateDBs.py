from pathlib import Path
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

if Path.cwd().joinpath('places.sqlite').is_file() == False:
    print('There is no places.sqlite DB in this folder. Please copy the file here and rerun this program.')

elif Path.cwd().joinpath('places.sqlite').is_file() == True:
    dbMain = sqlite3.connect('places.sqlite')
    curMain = dbMain.cursor()

    dupSQL = 'SELECT from_visit, place_id, visit_date, id, COUNT(*) Num FROM moz_historyvisits group by from_visit, place_id, visit_date having Num > 1'
    duplicateVisits = getAllEntries(cur = curMain, SQL = dupSQL, dictSchema ='(entry[0], entry[1], entry[2]): [entry[3], entry[4]]')

    numDuplicates = 0
    for dup in duplicateVisits.values():
        numDuplicates += dup[1]

    numDuplicates -= len(duplicateVisits)

    if numDuplicates > 0:
        print(f'Removing {numDuplicates} duplicate entries...')

        done = []
        allVisits = getAllEntries(cur = curMain, SQL ='SELECT * from main.moz_historyvisits order by id desc', dictSchema ='entry[0]: list(entry)')

        for visit in allVisits.values():
            if (visit[1], visit[2], visit[3]) in duplicateVisits.keys() and (visit[1], visit[2], visit[3]) not in done:
                lowestID = duplicateVisits[(visit[1], visit[2], visit[3])][0]
                curMain.execute('DELETE from main.moz_historyvisits where from_visit = ? and place_id = ? and visit_date = ? and id > ?', (visit[1], visit[2], visit[3], lowestID))
                done.append((visit[1], visit[2], visit[3]))


        input('\nDone.')

    elif numDuplicates == 0:
        print('No duplicate entries found.')

    curMain.connection.commit()
    curMain.close()
