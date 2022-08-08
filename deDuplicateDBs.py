from programFiles.combinerFunctions.Supplementary.sqlFunctions import getAllEntries
from pathlib import Path
import sqlite3


if Path.cwd().joinpath('places.sqlite').is_file() == False:
    print('There is no places.sqlite DB in this folder. Please copy the file here and rerun this program.')

elif Path.cwd().joinpath('places.sqlite').is_file() == True:
    print('Analysing database')

    dbMain = sqlite3.connect('places.sqlite')
    curMain = dbMain.cursor()

    dupSQL = 'SELECT from_visit, place_id, visit_date, id, COUNT(*) Num FROM moz_historyvisits group by from_visit, place_id, visit_date having Num > 1'
    duplicateVisits = getAllEntries(cur = curMain, SQL = dupSQL, dictSchema = [(0, 1, 2), [3, 4]])

    numDuplicates = 0
    for dup in duplicateVisits.values():
        numDuplicates += dup[1]

    numDuplicates -= len(duplicateVisits)

    if numDuplicates > 0:
        print(f'Removing {numDuplicates} duplicate history entries...')

        done = []
        allVisits = getAllEntries(cur = curMain, SQL ='SELECT * from main.moz_historyvisits order by id desc', dictSchema = [0, 'list'])

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
