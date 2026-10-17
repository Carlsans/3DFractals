import torch
class Openscad:
    def saveFractaltoFile(self,fractal):
        print("Saving fractal tensor....")
        with open("fractalarray.scad", "w") as text_file:
            torch.set_printoptions(profile="full")
            fractaltensor = str(fractal)
            start,end = fractaltensor.find('[[['),fractaltensor.find("]]]")+3
            print(start,end)

            fractaltensor = "fractalarray = " + fractaltensor[start:end] +";\n"
            text_file.write(fractaltensor)
            text_file.write("xsize = " + str(fractal.shape[0]) + ";\n")
            text_file.write("ysize = " + str(fractal.shape[1]) + ";\n")
            text_file.write("zsize = " + str(fractal.shape[2]) + ";\n")
            torch.set_printoptions(profile="default")
