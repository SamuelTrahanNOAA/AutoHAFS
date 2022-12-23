#! /usr/bin/env python3

def main():
    # Target number of gridpoints in each domain:
    gridpoints=[601*601,
                1201*1201]

    # How close the number of gridpoints must be to those numbers in percent.
    accuracy=1

    # Allowed ranges of possible grid side lengths for each domain:
    xyranges=[ [588,612],
               [1176,1224] ]
    nodes=45

    # Number of inner domain nodes:
    inner=[12,13,14,15,16,17,18,19,20]

    # Number outer domain nodes:
    outer=[ nodes-i for i in inner]

    # Number of MPI ranks per node on fv3 compute nodes
    ppn=42

    for isize in range(len(inner)):
        print('%d inner nodes, %d outer nodes ppn=%d:'%(inner[isize],outer[isize],ppn))
        for igrid in range(len(gridpoints)):
            print('  Grid %d'%(igrid,))
            gridrange=[ int(gridpoints[igrid]*(100-accuracy))//100,
                        int(gridpoints[igrid]*(100+accuracy))//100 ]
            grid=closest(gridrange,xyranges[igrid],inner[isize],ppn,'    ')
            
def closest(gridrange,xyrange,nodes,ppn,indent):
    ppes=nodes*ppn
    for xval in range(xyrange[0],xyrange[1]+1):
        for yval in range(xyrange[0],xyrange[1]+1):
            xyval=xval*yval
            if not xyval%ppes and xyval<=gridrange[1] and xyval>=gridrange[0]:
                print('%sgrid dims = %d, %d'%(indent,xval,yval))

if __name__ == '__main__':
    main()
