#pip install torch numpy trimesh PyMCubes numpy-stl
import os
import time

import numpy as np
import torch

from src.FractalParameters import FractalParameters
from src.VisualizeFractal import VisualizeFractal
from src.Openscad import Openscad
from src.StlGenerator import StlGenerator
from src.FractalLog import FractalLog
from src.FractalFormula import FractalFormula

class FractalGenerator3D:
    def __init__(self):
        self.parameters = FractalParameters()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print("Using",self.device)
        self.visualizer = VisualizeFractal()
        self.openscad = Openscad()
        self.stlgenerator = StlGenerator()
        self.log = FractalLog()

    def computeFractal(self):
        formula = FractalFormula(self.getStartingCoordinates())
        print(formula)

        #xcoord,ycoord,zcoord = self.getStartingCoordinates()
        #z = xcoord + ycoord
        #c = zcoord
        #print(z)
        #print(z.shape)

        while True:
            if not self.parameters.selectedfew == []:
                if not (formula.totalincrement in self.parameters.selectedfew):
                    formula.incrementformula()
                    continue
            result = torch.zeros((self.parameters.resolution),dtype=torch.int16)

            for i in range(self.parameters.maxiter):
                if i % (self.parameters.maxiter //10) == 0:
                    print("iteration",i,"on",self.parameters.maxiter)
                z = formula.applyformula()
                result[z.real + z.imag > 4] = i
                z[z.real+z.imag > 4] = float('nan')

                #print(z.shape)
            #print("result",result)
            #if str(self.device) == "cuda":
            #self.visualizer.drawVoxelTorchTensor(result)
            #    exit()
            #beforetime = time.time()
            #self.stlgenerator.generateStlCubic(result)
            #print("First cubic generation",time.time()-beforetime)
            beforetime = time.time()
            filename = "fractal"+ str(formula.totalincrement)
            stlresult = self.stlgenerator.generateStlCubic2(result,filename=filename+".stl")

            if not stlresult is None:
                print("Cubic generation", time.time() - beforetime)
                self.log.addtolog(str(self.parameters))
                self.log.addtolog(str(formula))
                self.log.savelog(filename=filename+"log.txt")
            else:
                os.remove(self.parameters.basedirectory + filename+".stl") if os.path.exists(self.parameters.basedirectory + filename+".stl") else None
                os.remove(self.parameters.basedirectory + filename + ".png") if os.path.exists(self.parameters.basedirectory + filename + ".png") else None
                os.remove(self.parameters.basedirectory + filename + "log.txt") if os.path.exists(self.parameters.basedirectory + filename + "log.txt") else None
            self.log.clearlog()
            if self.parameters.mode == "isrendering":
                self.stlgenerator.generateStlCubicbySteps(result,dirname="fractalstep"+filename+"/",takephoto = 2)
            # Select every pair only
            stlresult = self.stlgenerator.generateStlCubic2(np.where(result % 2 == 0, result, False).astype(bool),
                                               filename + "Odd.stl")
            print("Generated stl for odd values")
            if self.parameters.mode == "isdrawing":
                self.stlgenerator.generateObjectPhoto(stlresult, filename)
            #self.stlgenerator.generateStlCubicbySteps(result,overlap=2)
            self.stlgenerator.generateStlsbyRules(result,filename=filename)

            #self.openscad.saveFractaltoFile(result)
            #print("Generating mesh 1 ...")
            #self.stlgenerator.generateStlFromTensor(result)
            #print("Generating mesh 2 ...")
            #self.stlgenerator.generateStlFromTensor2(result)
            formula.incrementformula()

    def getStartingCoordinates(self):
        xcoordinates = torch.linspace(self.parameters.rangex[0], self.parameters.rangex[1],
                                      steps=self.parameters.resolution[0],device=self.device)
        xcoordinates = xcoordinates.view(self.parameters.resolution[0],1,1)

        print("xcoordinates", xcoordinates.shape)
        ycoordinates = torch.linspace(self.parameters.rangey[0], self.parameters.rangey[1],
                                      steps=self.parameters.resolution[1],device=self.device) * 1j

        ycoordinates = ycoordinates.view(1,self.parameters.resolution[1],1)
        zreal = torch.linspace(self.parameters.rangez[0].real, self.parameters.rangez[1].real,
                                      steps=self.parameters.resolution[2],device=self.device)
        zimag = torch.linspace(self.parameters.rangez[0].imag, self.parameters.rangez[1].imag,
                               steps=self.parameters.resolution[2], device=self.device)
        zcoordinates = zreal + zimag * 1j

        zcoordinates = zcoordinates.view(1,1,self.parameters.resolution[2])
        #zcoordinates = self.getzlinear(self.parameters.zSlope,self.parameters.zIntercept)
        return xcoordinates,ycoordinates,zcoordinates

    def getzlinear(self,A=1, B=0):
        # y = Ax + B
        x = torch.linspace(self.parameters.rangez[0], self.parameters.rangez[1], steps=self.parameters.resolution[2],device=self.device)
        y = x * A + B
        z = x + y * 1j
        return z.view(1,1,self.parameters.resolution[2])

fractalgenerator = FractalGenerator3D()

fractalgenerator.computeFractal()