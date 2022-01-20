from configparser import ConfigParser
from pathlib import Path

combinerConfig = ConfigParser()

# If Settings.ini isn't present, create it.
if Path.cwd().joinpath('Settings.ini').is_file() == False:
	with open('Settings.ini', 'w') as settingsFile: combinerConfig.write(settingsFile)

if Path.cwd().joinpath('Settings.ini').is_file() == True:
	combinerConfig.read_file(open('Settings.ini'))
	combinerConfigOptions = {
		'History Combiner': {
			'Bookmarks': '2',
			'Folders above': '0',
			'Inputhistory': '2',
			'Keywords': '2',
			'Include downloads': '0', # DB versions older than FF 20.0 use 'downloads.sqlite'. I'm not including provision for this unless absolutely necessary.
			'Update frecency': '0',
			'Primary DB folder': str(Path.home().joinpath('AppData\\Roaming\\Mozilla\\Firefox\\Profiles')),
			'DB folders': '{}'
			# 'Recursive': '2' # Search all subfolders
			# 'Folder positions': {'Menu': {'Before': False, 'After': False, 'Don\'t change': True}, 
			#                   'Toolbar': {'Before': False, 'After': False, 'Don\'t change': True}}
			},

		'Reminder dialogs': {
			'Downloads': '0',
			'Number DBs': '0',
			'Overwrite DB': '0',
			'Stop combining': '0',
			'Welcome': '0',
			'Firefox close': '0',
			},

		'GUI': {
			'Folders - Last selected directory': '',
			'Settings - Last selected tab': '0',
			'Stop pressed': '0',
			'Auto-size folder dialog width': '2'
			},

		'Backup': {
			'Finished DBs': '2',
			'Date/time': '0',
			'Open folder': '2'
			},

		'Debugging': {
			'Enabled': '2',
			'Debug level': '10', # logging.ERROR is 40, logging.INFO is 20 and logging.DEBUG is 10
			'Log personal info': '2'
			},

		'Misc': {
			'Delete crashed py-installer files': '2'
			}

		}

	for section, options in combinerConfigOptions.items():
		if combinerConfig.has_section(section) == False: combinerConfig.add_section(section)

		for option, value in options.items():
			if combinerConfig.has_option(section, option) == False: combinerConfig.set(section, option, value)

	with open('Settings.ini', 'w') as settingsFile: combinerConfig.write(settingsFile)



combinerConfig.read_file(open('Settings.ini'))

primaryDBFolder = Path(combinerConfig.get('History Combiner', 'Primary DB folder'))
(indexName_SQL, nonUniqueIndeces) = [], []

oldEntries = {}

class combiningStopped(Exception):
	def __init__(self):
		super().__init__('')

class insertException(Exception):
	def __init__(self, errorMessage):
		super().__init__(errorMessage)

class dictException(Exception):
	def __init__(self, errorMessage):
		super().__init__(errorMessage)