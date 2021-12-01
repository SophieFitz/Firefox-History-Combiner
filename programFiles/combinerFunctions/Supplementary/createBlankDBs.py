import sqlite3

def createDB53(currDir):
	db53Path = currDir.joinpath('db53forConversion.sqlite')
	if db53Path.is_file() == True: db53Path.unlink() # Remove orphaned file

	db53 = sqlite3.connect(currDir.joinpath('db53forConversion.sqlite')) # Create new db
	cur53 = db53.cursor()
	
	cur53.execute('pragma auto_vacuum = 0')
	cur53.execute('pragma automatic_index = on')
	cur53.execute('pragma case_sensitive_like = off')
	cur53.execute('pragma checkpoint_fullfsync = off')
	cur53.execute('pragma foreign_keys = on')
	cur53.execute('pragma fullfsync = off')
	cur53.execute('pragma ignore_check_constraints = off')
	cur53.execute('pragma journal_size_limit = -1')
	cur53.execute('pragma locking_mode = normal')
	cur53.execute('pragma max_page_count = 1073741823')
	cur53.execute('pragma page_size = 32768')
	cur53.execute('pragma recursive_triggers = off')
	cur53.execute('pragma secure_delete = off')
	cur53.execute('pragma synchronous = 2')
	cur53.execute('pragma temp_store = 0')
	cur53.execute('pragma user_version = 36')
	cur53.execute('pragma journal_mode = wal') # Journal mode set here as it interferes with 'page_size'
	cur53.execute('pragma wal_autocheckpoint = 1000')
	
	cur53.connection.commit()


	cur53.execute('begin')
	cur53.execute('CREATE TABLE moz_anno_attributes (id INTEGER PRIMARY KEY, name VARCHAR(32) UNIQUE NOT NULL)')
	cur53.execute('CREATE TABLE moz_annos (id INTEGER PRIMARY KEY, place_id INTEGER NOT NULL,'
						'anno_attribute_id INTEGER, mime_type VARCHAR(32) DEFAULT NULL, content LONGVARCHAR,' 
						'flags INTEGER DEFAULT 0, expiration INTEGER DEFAULT 0, type INTEGER DEFAULT 0, dateAdded INTEGER DEFAULT 0,'
						'lastModified INTEGER DEFAULT 0)')

	cur53.execute('CREATE TABLE moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER DEFAULT NULL, parent INTEGER,' 
						'position INTEGER, title LONGVARCHAR, keyword_id INTEGER, folder_type TEXT, dateAdded INTEGER,'
						'lastModified INTEGER, guid TEXT, syncStatus INTEGER NOT NULL DEFAULT 0, syncChangeCounter INTEGER NOT NULL DEFAULT 1)')

	cur53.execute('CREATE TABLE moz_bookmarks_deleted (guid TEXT PRIMARY KEY, dateRemoved INTEGER NOT NULL DEFAULT 0)')
	cur53.execute('CREATE TABLE moz_favicons (id INTEGER PRIMARY KEY, url LONGVARCHAR UNIQUE, data BLOB, mime_type VARCHAR(32), expiration LONG)')
	cur53.execute('CREATE TABLE moz_historyvisits (id INTEGER PRIMARY KEY, from_visit INTEGER, place_id INTEGER,'
						'visit_date INTEGER, visit_type INTEGER, session INTEGER)')

	cur53.execute('CREATE TABLE moz_hosts (id INTEGER PRIMARY KEY, host TEXT NOT NULL UNIQUE, frecency INTEGER, typed INTEGER NOT NULL DEFAULT 0, prefix TEXT)')
	cur53.execute('CREATE TABLE moz_inputhistory (place_id INTEGER NOT NULL, input LONGVARCHAR NOT NULL, use_count INTEGER, PRIMARY KEY (place_id, input))')
	cur53.execute('CREATE TABLE moz_items_annos (id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, anno_attribute_id INTEGER,'
						'mime_type VARCHAR(32) DEFAULT NULL, content LONGVARCHAR, flags INTEGER DEFAULT 0, expiration INTEGER DEFAULT 0,' 
						'type INTEGER DEFAULT 0, dateAdded INTEGER DEFAULT 0, lastModified INTEGER DEFAULT 0)')

	cur53.execute('CREATE TABLE moz_keywords (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT UNIQUE, place_id INTEGER, post_data TEXT)')
	cur53.execute('CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url LONGVARCHAR, title LONGVARCHAR, rev_host LONGVARCHAR,' 
						'visit_count INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0 NOT NULL, typed INTEGER DEFAULT 0 NOT NULL, favicon_id INTEGER,' 
						'frecency INTEGER DEFAULT -1 NOT NULL, last_visit_date INTEGER , guid TEXT, foreign_count INTEGER DEFAULT 0 NOT NULL,'
						'url_hash INTEGER DEFAULT 0 NOT NULL )')

	cur53.execute('CREATE UNIQUE INDEX moz_annos_placeattributeindex ON moz_annos (place_id, anno_attribute_id)')
	cur53.execute('CREATE UNIQUE INDEX moz_bookmarks_guid_uniqueindex ON moz_bookmarks (guid)')
	cur53.execute('CREATE INDEX moz_bookmarks_itemindex ON moz_bookmarks (fk, type)')
	cur53.execute('CREATE INDEX moz_bookmarks_itemlastmodifiedindex ON moz_bookmarks (fk, lastModified)')
	cur53.execute('CREATE INDEX moz_bookmarks_parentindex ON moz_bookmarks (parent, position)')
	cur53.execute('CREATE INDEX moz_historyvisits_dateindex ON moz_historyvisits (visit_date)')
	cur53.execute('CREATE INDEX moz_historyvisits_fromindex ON moz_historyvisits (from_visit)')
	cur53.execute('CREATE INDEX moz_historyvisits_placedateindex ON moz_historyvisits (place_id, visit_date)')
	cur53.execute('CREATE UNIQUE INDEX moz_items_annos_itemattributeindex ON moz_items_annos (item_id, anno_attribute_id)')
	cur53.execute('CREATE UNIQUE INDEX moz_keywords_placepostdata_uniqueindex ON moz_keywords (place_id, post_data)')
	cur53.execute('CREATE INDEX moz_places_faviconindex ON moz_places (favicon_id)')
	cur53.execute('CREATE INDEX moz_places_frecencyindex ON moz_places (frecency)')
	cur53.execute('CREATE UNIQUE INDEX moz_places_guid_uniqueindex ON moz_places (guid)')
	cur53.execute('CREATE INDEX moz_places_hostindex ON moz_places (rev_host)')
	cur53.execute('CREATE INDEX moz_places_lastvisitdateindex ON moz_places (last_visit_date)')
	cur53.execute('CREATE INDEX moz_places_url_hashindex ON moz_places (url_hash)')
	cur53.execute('CREATE INDEX moz_places_visitcount ON moz_places (visit_count)')


	attributes = ((1, 'mobile/bookmarksRoot'), (2, 'bookmarkProperties/description'), (3, 'Places/SmartBookmark'))
	cur53.executemany('insert into moz_anno_attributes values (?, ?)', attributes)

	bookmarks = ((1, 2, None, 0, 0, '', None, None, 1553191408243000, 1553191409221000, '', 1, 1), 
			   (2, 2, None, 1, 0, 'Bookmarks Menu', None, None, 1553191408243000, 1553191409221000, 'menu________', 1, 5), 
			   (3, 2, None, 1, 1, 'Bookmarks Toolbar', None, None, 1553191408243000, 1553191409080000, 'toolbar_____', 1, 5), 
			   (4, 2, None, 1, 2, 'Tags', None, None, 1553191408243000, 1553191408243000, 'tags________', 1, 1), 
			   (5, 2, None, 1, 3, 'Other Bookmarks', None, None, 1553191408243000, 1553191409040000, 'unfiled_____', 1, 2), 
			   (6, 2, None, 1, 4, 'mobile', None, None, 1553191408243000, 1553191408243000, 'mobile______', 1, 1))

	cur53.executemany('insert into moz_bookmarks values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', bookmarks)

	itemAnnos = ((1, 6, 1, None, 1, 0, 4, 1, -1909976776, -1909976776), 
			   (2, 3, 2, None, 'Add bookmarks to this folder to see them displayed on the Bookmarks Toolbar', 0, 4, 3, 1553191409040000, 1553191409040000))

	cur53.executemany('insert into moz_items_annos values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', itemAnnos)
	cur53.connection.commit()
	cur53.close()


def createBlankFaviconsDB(mainFaviconsPath, curMain):
	dbCon = sqlite3.connect(mainFaviconsPath)
	cur = dbCon.cursor()

	cur.execute('pragma auto_vacuum = 2')
	cur.execute('pragma automatic_index = on')
	cur.execute('pragma case_sensitive_like = off')
	cur.execute('pragma checkpoint_fullfsync = off')
	cur.execute('pragma foreign_keys = on')
	cur.execute('pragma fullfsync = off')
	cur.execute('pragma ignore_check_constraints = off')
	cur.execute('pragma journal_size_limit = -1')
	cur.execute('pragma locking_mode = normal')
	cur.execute('pragma max_page_count = 1073741823')
	cur.execute('pragma page_size = 32768')
	cur.execute('pragma recursive_triggers = off')
	cur.execute('pragma secure_delete = off')
	cur.execute('pragma synchronous = 2')
	cur.execute('pragma temp_store = 0')
	cur.execute('pragma user_version = 0')
	cur.execute('pragma journal_mode = wal') # Journal mode set here as it interferes with 'page_size'
	cur.execute('pragma wal_autocheckpoint = 1000')
	cur.connection.commit()

	cur.execute('begin')
	cur.execute('CREATE TABLE moz_icons(id INTEGER PRIMARY KEY, icon_url TEXT NOT NULL, fixed_icon_url_hash INTEGER NOT NULL,'
								 'width INTEGER NOT NULL DEFAULT 0, root INTEGER NOT NULL DEFAULT 0, color INTEGER,'
								 'expire_ms INTEGER NOT NULL DEFAULT 0, data BLOB)')

	iconstoPagesCreate = ('CREATE TABLE moz_icons_to_pages (page_id INTEGER NOT NULL, icon_id INTEGER NOT NULL, expire_ms INTEGER NOT NULL DEFAULT 0,'
						  'PRIMARY KEY (page_id, icon_id), FOREIGN KEY (page_id) REFERENCES moz_pages_w_icons ON DELETE CASCADE,'
						  'FOREIGN KEY (icon_id) REFERENCES moz_icons ON DELETE CASCADE) WITHOUT ROWID')

	cur.execute('CREATE TABLE moz_pages_w_icons ( id INTEGER PRIMARY KEY, page_url TEXT NOT NULL, page_url_hash INTEGER NOT NULL )')

	userVersion = curMain.execute('pragma user_version').fetchone()[0]
	if userVersion < 54: iconstoPagesCreate.replace(', expire_ms INTEGER NOT NULL DEFAULT 0', '')
	cur.execute(iconstoPagesCreate)

	cur.execute('CREATE INDEX moz_icons_iconurlhashindex ON moz_icons (fixed_icon_url_hash)')
	cur.execute('CREATE INDEX moz_pages_w_icons_urlhashindex ON moz_pages_w_icons (page_url_hash)')

	cur.connection.commit()
	cur.close()