import os

from src.FileManager import FileManager


class FractalParameters:
    def __init__(self):
        self.basedirectory = os.path.dirname(os.path.realpath(__file__)) + "/output/"
        self.filemanager = FileManager(self)
        ## General behavior
        self.mode = "issearching" # issearching,isdrawing
        self.mode = "isdrawing"
        self.mode = "isrendering"
        ## FRACTAL PARAMETERS
        cubicresolution = 50
        self.resolution = (cubicresolution,cubicresolution,cubicresolution)
        self.decimationratio = None
        layerpermm = int(cubicresolution / 0.2)
        extrusionwidth = int(cubicresolution / 0.4)
        #self.resolution = (extrusionwidth, extrusionwidth, layerpermm)
        divider = 1
        self.rangex = [-2/divider, 2/divider]
        self.rangey = [-1.5/divider, 1.5/divider]
        self.rangez = [-2+2j, 2-2j]
        self.maxiter = 100
        ## STL GENERATION OPTIONS
        self.stlslice = False
        self.stladdvolume = 0
        self.minimumwatertightratio = 0.15
        self.selectedfew = []
        if self.mode == "isdrawing":
            self.selectedfewbypass()
        if self.mode == "isrendering":
            self.renderforprint()

    def renderforprint(self):
        self.maxiter = 100
        self.modeldimensions = [100,100,100]
        self.layerheight = 0.2
        self.nozzlediameter = 0.4
        self.extrusionwidth = self.nozzlediameter
        self.decimationratio = 0.2
        scaling = .5 # Augment if the model is too heavy !
        self.layerheight *= scaling
        self.extrusionwidth *= scaling
        self.resolution = [int(self.modeldimensions[0]//self.extrusionwidth),int(self.modeldimensions[1]//self.extrusionwidth),int(self.modeldimensions[2]//self.layerheight)]
        print("Rendering resolution : ",self.resolution)
        self.selectedfew = [16994]#[20347,20215,20194,20062,20072,19768,17159,17122,16994,16936,16844] # Enter the id to the fractals to render
        # input("Press enter")
        self.basedirectory = os.path.dirname(os.path.realpath(__file__)) + "/output/render/"


    def selectedfewbypass(self):
        cubicresolution = 120
        self.resolution = (cubicresolution, cubicresolution, cubicresolution)
        self.selectedfew = self.filemanager.getFractalIndex()
        print("Selected few count",str(len(self.selectedfew)))
        #input("Press enter")
        self.basedirectory = os.path.dirname(os.path.realpath(__file__)) + "/output/selectedfews/"

    def __str__(self):
        returnvalue = "Resolution : " + str(self.resolution) + "\n"
        returnvalue += "X range : " + str(self.rangex) + "\n"
        returnvalue += "Y range : " + str(self.rangey) + "\n"
        returnvalue += "Z range : " + str(self.rangez) + "\n"
        returnvalue += "Max iterations : " + str(self.maxiter) + "\n"
        returnvalue += "Is slicing ? : " + str(self.stlslice) + "\n"
        returnvalue += "Added volume : " + str(self.stladdvolume) + "\n"
        returnvalue += "Minimum Watertight faces ratio : " + str(self.minimumwatertightratio) + "\n"
        return returnvalue