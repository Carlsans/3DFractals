include <fractalarray.scad>;
for(x = [0:xsize-1]){
    for(y = [0:ysize-1]){
        for(z = [0:zsize-1]){
        //echo(fractalarray[x][y][z]);
        if((fractalarray[x][y][z]+1)%3 == 0){
            translate([x,y,z])cube([1,1,1]);
        }
            
        }
    }
}