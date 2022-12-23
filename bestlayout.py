#! /usr/bin/env python3

import sys

def main():
    # Target number of gridpoints in each domain:
    gridpoints=[600*600,
                1200*1200]

    # How close the number of gridpoints must be to those numbers in percent.
    accuracy=1.5

    # Allowed ranges of possible grid side lengths for each domain:
    xyranges=[ [580,620],
               [1160,1240] ]

    print('must be within %.2f%% of target gridpoints: inner=%d outer=%d'%(accuracy,gridpoints[0],gridpoints[1]))
    
    # Number of FV3 compute nodes:
    nodes=45

    # Number of inner domain nodes.
    # The ideal number is around 1/3 of the nodes
    diff=range(-6,7)
    mid=int(nodes*0.33333333)
    inner=[ mid+x for x in diff ]

    # Number outer domain nodes:
    outer=[ nodes-i for i in inner]
    
    # Number of MPI ranks per node on fv3 compute nodes
    # Reasonable numbers are 32, 42, 60, 62, or 64. Anything else has no options for good performance.
    ppn=42

    # This seems to get the best performance:
    layout_algo = reversed_most_square_layout_that_integer_divides_ppn

    # Another option, but slightly worse performance:
    #layout_algo = most_square_layout

    print('%d fv3 compute nodes with %d MPI ranks per node'%(nodes,ppn))
    print('inner domain node counts: '+str(inner))
    print('outer domain node counts: '+str(outer))
    print()
    
    for isize in range(len(inner)):
        answers=['','']
        print('%d inner nodes, %d outer nodes ppn=%d:'%(inner[isize],outer[isize],ppn))
        for igrid in range(len(gridpoints)):
            gridrange=[ gridpoints[igrid]*(100.-accuracy)/100.,
                        gridpoints[igrid]*(100.+accuracy)/100. ]
            answers[igrid]=closest(gridrange,xyranges[igrid],inner[isize],ppn,'    ',gridpoints[igrid],igrid,layout_algo)
        if answers[0] and answers[1]:
            sys.stdout.write('  Inner domain\n'+answers[0])
            sys.stdout.write('  Outer domain\n'+answers[1])
        else:
            print('  No options.')

def closest(gridrange,xyrange,nodes,ppn,indent,target,igrid,layout_algo):
    ppes=nodes*ppn
    answer = ''
    for xval in range(xyrange[0],xyrange[1]+1):
        if igrid==0 and xval%3:
            continue
        for yval in range(xyrange[0],xyrange[1]+1):
            if igrid==0 and yval%3:
                continue
            xyval=xval*yval
            if not xyval%ppes and xyval<=gridrange[1] and xyval>=gridrange[0]:
                layout = layout_algo(nodes,ppn,xval,yval)
                badness = max(layout[0]/layout[1], layout[1]/layout[0])
                if badness<2:
                    answer += '%sgrid dims = %4d,%4d = %4d,%4d in input.nml;  layout = %2d,%2d;  mpi patch = %.1f,%.1f;  gridpoints = %7d = %7.3f%% of target\n'%(
                        indent,
                        xval,yval,
                        xval+1,yval+1,
                        layout[0],layout[1],
                        xval/float(layout[0]),
                        yval/float(layout[1]),
                        xyval,
                        xyval/float(target)*100
                    )
    return answer

def reversed_most_square_layout_that_integer_divides_ppn(nodes,ppn,nx,ny):
    [ layout_y, layout_x ] = most_square_layout_that_integer_divides_ppn(nodes,ppn,ny,nx)
    return [ layout_x, layout_y ]

def most_square_layout_that_integer_divides_ppn(nodes,ppn,nx,ny):
    tasks=nodes*ppn
    bestx=ppn
    besty=nodes
    bestscore=abs(bestx-besty)
    for layout_x_2 in range(ppn-1):
        layout_x = layout_x_2+2
        if ppn%layout_x:
            continue
        if nx%layout_x:
            continue
        layout_y = tasks//layout_x
        if tasks!=layout_x*layout_y:
            continue
        if ny%layout_y:
            continue
        badness = max(float(layout_x)/layout_y, float(layout_x)/layout_y)
        if badness>=2:
            continue
        score=abs(layout_x-layout_y)
        if score<bestscore:
            bestx=layout_x
            besty=layout_y
            bestscore=score
    return [ bestx, besty ]

def most_square_layout(nodes,ppn,nx,ny):
    tasks=nodes*ppn
    bestx=1
    besty=tasks
    bestscore=abs(besty-bestx)
    for n in range(tasks-1):
        tx=n+2
        ty=tasks//tx
        badness = max(float(tx)/ty,float(ty)/tx)
        if badness>=2:
            continue
        if tx*ty==tasks:
            if nx%tx or ny%ty:
                continue
            score=abs(ty-tx)
            if score<bestscore:
                bestx=tx
                besty=ty
                bestscore=score
    return [ bestx, besty ]

if __name__ == '__main__':
    main()
