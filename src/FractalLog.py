import os

from src.FractalParameters import FractalParameters


class FractalLog:
    def __init__(self):
        self.parameters = FractalParameters()
        self.logcontent = ""

    def addtolog(self,content):
        self.logcontent += content

    def clearlog(self):
        self.logcontent = ""

    def savelog(self,filename = ""):
        if filename == "":
            return
        with open(self.parameters.basedirectory+filename, 'w') as filetowrite:
            filetowrite.write(self.logcontent)