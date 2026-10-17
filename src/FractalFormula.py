import inspect
import torch
import diyfunctions as fn

class FractalFormula:
    def __init__(self,coordinates):
        self.xcoord, self.ycoord, self.zcoord = coordinates
        self.initvalues()
        self.fnlist = [fn.real,fn.imag, torch.conj, fn.abs,
                       fn.angle,  torch.sin, torch.cos, torch.tan,
                       torch.sinh, torch.cosh, torch.tanh, torch.exp,
                       torch.log, torch.log10, torch.sqrt,fn.square,fn.cubic,fn.parallel]
        self.fndict = {}
        self.fndictindex = {}
        self.totalincrement = 0
        self.initfns()
    def initvalues(self):
        self.z = self.xcoord.clone() + self.ycoord.clone()
        self.c = self.zcoord.clone()

    def initfns(self):
        self.fndict['fn1'] = self.fnlist[0]
        self.fndictindex['fn1'] = 0
        self.fndict['fn2'] = self.fnlist[0]
        self.fndictindex['fn2'] = 0
        self.fndict['fn3'] = self.fnlist[0]
        self.fndictindex['fn3'] = 0
        self.fndict['fn4'] = self.fnlist[0]
        self.fndictindex['fn4'] = 0

    def incrementformula(self):
        for key, value in self.fndictindex.items():
            if value >= len(self.fnlist)-1:
                self.fndictindex[key]=0
            else:
                self.fndictindex[key]+=1
                break
        isfinished = True
        for value in self.fndictindex.values():
            if value < len(self.fnlist)-1:
                isfinished = False
                break
        print(self.fndictindex)
        for key in self.fndict.keys():
            self.fndict[key] = self.fnlist[self.fndictindex[key]]
        print(self.fndict)
        self.totalincrement += 1
        self.initvalues()
        if isfinished:
            print("Total increments = ",self.totalincrement)
            exit()

    def applyformula(self):
        fn1,fn2,fn3,fn4 = self.fndict['fn1'],self.fndict['fn2'],self.fndict['fn3'],self.fndict['fn4']
        self.z =  fn4(fn1(self.c) * fn2(self.c) + fn3(self.z))

        return self.z

    def __str__(self):
        returnvalue = inspect.getsource(self.applyformula)

        for key, value in self.fndict.items():
            returnvalue += str(key) + " = " + str(value) +"\n"
        return returnvalue