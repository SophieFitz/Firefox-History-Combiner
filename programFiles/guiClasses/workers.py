from PyQt6.QtCore import QObject, pyqtSignal
from combiner import combiner

import psutil, time, warnings, traceback
import programFiles.globalVars as g


class combinerWorker(QObject):
	finished = pyqtSignal()
	backup = pyqtSignal()
	error = pyqtSignal(tuple)
	updateProgBar = pyqtSignal(int)

	def __init__(worker):
		super().__init__()

	def runCombinerProc(worker):
		# Run the combiner in a separate process as if/when something goes wrong and an exception is thrown, I want the process to terminate immediately.
		# If I were to terminate without using subprocess, the whole program (including the GUI) would freeze and quit.
		# worker.combinerProc = subprocess.Popen(('./dist/combiner.exe'), stderr = subprocess.PIPE, universal_newlines = True)
		# worker.combinerProc = subprocess.Popen(('python', 'combiner.py'), stderr = subprocess.PIPE, universal_newlines = True)
		# returnCode = worker.combinerProc.wait()
		# while worker.combinerProc.poll() == None:

		# g.finishedSig = worker.finished
		# g.backupSig = worker.backup
		# g.errorSig = worker.error

		g.updateProgBar = worker.updateProgBar


		try:
			# Ignore all warnings, such as "Image was not the expected size".
			with warnings.catch_warnings():
				warnings.simplefilter('ignore')
				combiner()

		except Exception as errorMessage:
			customExceptionTypes = ['programFiles.globalVars.combiningStopped', 'programFiles.globalVars.insertException', 'programFiles.globalVars.dictException']
			custom = False

			for c in customExceptionTypes:
				if c in traceback.format_exc(): custom = True

			# If the user did press the Stop button, then no error dialog is displayed.
			if type(errorMessage) is not g.combiningStopped:
				if custom is False: errorMessage = (traceback.format_exc(),) # Make a tuple so emit doesn't throw an error
				elif custom is True: errorMessage = errorMessage.args

				worker.error.emit(errorMessage)
		
		finally:
			worker.finished.emit()
			worker.backup.emit()


class ffOpenWorker(QObject):
	finished = pyqtSignal()

	def __init__(worker):
		super().__init__()

	def check(worker):
		while True:
			procsOpen = []
			time.sleep(0.1)
			for proc in psutil.process_iter():
				try:
					if 'firefox.exe' == proc.name().lower(): procsOpen.append(proc.name().lower())

				except psutil.AccessDenied: # Not all processes are accessible, therefore skip over any that aren't.
					pass

			if 'firefox.exe' not in procsOpen: break

		worker.finished.emit()
	