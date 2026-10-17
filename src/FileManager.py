import glob
import re


class FileManager:
    def __init__(self,parameters):
        self.parameters = parameters
    def getFractalIndex(self):
        # Keep only the index of the fractal that still are in the output directory
        # You should delete every uninteresting results before
        mylist = [f for f in glob.glob(self.parameters.basedirectory + "*.stl")]
        #print(self.parameters.basedirectory + "*.stl")
        #print(mylist)
        # Keep only name
        mylist =[f[-1:0:-1].split('/',1)[0][-1:0:-1] for f in mylist]
        mylist = [re.sub(r"\D", "", f) for f in mylist]
        mylist = list(set(mylist))
        #print(mylist)
        if '' in mylist:
            mylist.remove('')
        mylist = [int(f) for f in mylist]
        #print(mylist)
        return mylist