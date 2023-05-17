from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt

import programFiles.globalVars as g

class createCheckbox(QCheckBox):
	def __init__(self, text, iniSection, option, *triState):
		super().__init__(text)

		self.iniSection = iniSection
		self.option = option

		if triState: self.setTristate(True)
		self.setCheckState(Qt.CheckState[g.combinerConfig.get(iniSection, option)])

		self.stateChanged.connect(lambda: g.combinerConfig.set(iniSection, option, str(self.checkState()).split('.')[1]))

	def resetState(self):
		self.setCheckState(Qt.CheckState[g.combinerConfig.get(self.iniSection, self.option)])