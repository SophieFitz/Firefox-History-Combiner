from PyQt5.QtWidgets import QCheckBox
import programFiles.globalVars as g

class createCheckbox(QCheckBox):
	def __init__(self, text, iniSection, option, *triState):
		super().__init__(text)

		self.iniSection = iniSection
		self.option = option

		if triState: self.setTristate(True)
		self.setCheckState(g.combinerConfig.getint(iniSection, option))

		self.stateChanged.connect(lambda: g.combinerConfig.set(iniSection, option, str(self.checkState())))

	def resetState(self):
		self.setCheckState(g.combinerConfig.getint(self.iniSection, self.option))