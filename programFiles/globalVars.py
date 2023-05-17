from configparser import ConfigParser
from pathlib import Path

combinerConfig = ConfigParser()

# If Settings.ini isn't present, create it.
if Path.cwd().joinpath('Settings.ini').is_file() == False:
	with open('Settings.ini', 'w') as settingsFile: combinerConfig.write(settingsFile)

combinerConfig.read_file(open('Settings.ini'))
combinerConfigOptions = {
	'History Combiner': {
		'Bookmarks': 'Checked',
		'Folders above': 'Unchecked',
		'Inputhistory': 'Checked',
		'Keywords': 'Checked',
		'Include downloads': 'Unchecked', # DB versions older than FF 20.0 use 'downloads.sqlite'. I'm not including provision for this unless absolutely necessary.
		'Update frecency': 'Unchecked',
		'Primary DB folder': str(Path.home().joinpath('AppData\\Roaming\\Mozilla\\Firefox\\Profiles')),
		'DB folders': '[]'
		# 'Recursive': 'Checked' # Search all subfolders
		# 'Folder positions': {'Menu': {'Before': False, 'After': False, 'Don\'t change': True},
		#                   'Toolbar': {'Before': False, 'After': False, 'Don\'t change': True}}
		},

	'Reminder dialogs': {
		'Downloads': 'Unchecked',
		'Number DBs': 'Unchecked',
		'Overwrite DB': 'Unchecked',
		'Stop combining': 'Unchecked',
		'Welcome': 'Unchecked',
		'Firefox close': 'Unchecked',
		},

	'GUI': {
		'Folders - Last selected directory': '',
		'Settings - Last selected tab': 'Unchecked',
		'Stop pressed': 'Unchecked',
		'Auto-size folder dialog width': 'Checked'
		},

	'Backup': {
		'Finished DBs': 'Checked',
		'Date/time': 'Unchecked',
		'Open folder': 'Checked'
		},

	'Debugging': {
		'Enabled': 'Checked',
		'Debug level': '10', # logging.ERROR is 40, logging.INFO is 20 and logging.DEBUG is 10
		'Log personal info': 'Checked',
		'Log table schemas': 'Unchecked'
		},

	'Misc': {
		'Delete crashed py-installer files': 'Checked'
		}

	}

# Populate values if file is empty / for upgrading versions
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