#! /usr/bin/env python3

import sys
import os
import tempfile
import subprocess
import math

def main():

    where={
        'noscrub':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/',
        'HAFS':   '/lfs/h2/oar/esrl/noscrub/samuel.trahan/hafsv1_phase3/',
        'exebase':'supafast',
        'template_dir':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/junghoon-reference/',
        'autohafs_dir': os.path.join(os.path.dirname(os.path.realpath(__file__)),'junghoon-reference'),
    }

    #        'scrub':  '/lfs/h2/oar/ptmp/samuel.trahan/',

    with128nodes(dt=72,**where)
    
########################################################################

def decomp_tests(**kwargs):
    replace=make_hash(queue='debug',walltime='00:30:00',
              inner_nodes=15,outer_nodes=30,
              comp_ppn=60,comp_tpp=2,
              inner_layout=[15,60],
              outer_layout=[120,15],
              best_layout=None,
              more_prefix='decomp-test-',**kwargs)
    generate_and_submit(replace)
    replace=make_hash(queue='debug',walltime='00:30:00',
              inner_nodes=25,outer_nodes=25,
              comp_ppn=40,comp_tpp=3,
              inner_layout=[25,40],
              outer_layout=[40,25],
              best_layout=None,
              more_prefix='decomp-test-',**kwargs)
    generate_and_submit(replace)

def with128nodes(dt,**kwargs):
    fv3_compute_nodes=46
    inner_nodes_list=[ 14 ]
    isubmit=0
    layouts = {
        #'lay-divppn-': most_square_layout_that_integer_divides_ppn,
        #'lay-revppn-': reversed_most_square_layout_that_integer_divides_ppn,
        'lay-square-': most_square_layout,
    }
    blocksizes = {
        'bsth-': blocksize_with_one_block_per_thread,
        '': blocksize_with_lowest_remainder,
    }
    blocksize_prefix=''
    best_blocksize=blocksizes[blocksize_prefix]
    scrub='/lfs/h2/oar/stmp/samuel.trahan/'
    for i in 'q':
        for layout_prefix, best_layout in layouts.items():
            for inner_nodes in inner_nodes_list:
                outer_nodes=fv3_compute_nodes-inner_nodes
                replace=make_hash(inner_nodes=inner_nodes,
                                  outer_nodes=outer_nodes,
                                  scrub=scrub,
                                  comp_ppn=32,
                                  comp_tpp=4,
                                  write_tasks_per_group=8,
                                  io_ppn=16,
                                  io_tpp=8,
                                  io_omp_num_threads=4,
                                  outer_k_split=2,
                                  outer_n_split=4,
                                  inner_k_split=4,
                                  inner_n_split=9,
                                  dt_atmos=dt,
                                  best_layout=best_layout,
                                  best_blocksize=best_blocksize,
                                  OMP_STACKSIZE="128M",
                                  walltime="02:20:00",
                                  more_prefix='dt%d-st128-%s%s'%(dt,layout_prefix,blocksize_prefix),
                                  **kwargs)
                generate_and_submit(replace)


########################################################################

# Quasi-shell commands
    
def generate_and_submit(replace):
    # Generate the run area, chdir there, and submit the job.
    generate(replace)
    oldcwd=os.getcwd()
    print('chdir',replace["%dir%"])
    os.chdir(replace["%dir%"])
    qsub(replace)
    print('chdir',oldcwd)
    os.chdir(oldcwd)
    
def generate(replace):
    # Generate the run area
    fill_auto_files(replace)
    print('will run in dir',replace['%dir%'])
    rsync(replace)

def rsync(replace):
    # Copy template directory contents to run area.
    rsync_command=[ "rsync", "-arv", "--ignore-existing",
                    os.path.join(replace["%template_dir%"],"."),
                    os.path.join(replace['%dir%'],'.') ]
    print('execute',rsync_command)
    sys.stdout.flush()
    subprocess.run(rsync_command,check=True)

def qsub(replace):
    # Submit the job in the run area. Must chdir first.
    qsub_command=[ "qsub", "hafs_forecast.sh" ]
    print('execute',qsub_command)
    sys.stdout.flush()
    subprocess.run(qsub_command,check=True)

########################################################################

# Text file processing.

def fill_auto_files(replace):
    outdir=tempfile.mkdtemp(prefix=replace['%prefix%'], dir=replace['%scrub%'])
    indir=replace['%autohafs_dir%']
    replace['%name%'] = str(os.path.basename(outdir))
    replace['%dir%'] = str(outdir)
    if not os.access(replace['%exe%'],os.X_OK):
        sys.stderr.write(replace['%exe%']+': cannot execute\n')
    files=[ 'hafs_forecast.sh', 'input_nest02.nml', 'input.nml',
            'model_configure', 'nems.configure', 'clean.sh', 'lookit.sh' ]
    exe=[ 'clean.sh', 'lookit.sh' ]
    parse_files(indir,outdir,replace,files)
    for afile in files:
        fullfile=os.path.join(outdir,afile)
        if not os.path.exists(fullfile):
            sys.stderr.write(fullfile+": does not exist")
        if not os.path.getsize(fullfile)>0:
            sys.stderr.write(fullfile+": is empty")
        if afile in exe:
            os.chmod(fullfile,0o755)

def parse_files(indir,outdir,replace,files):
    # For each file in `files`, replace text via the `replace` hash
    # from the *.auto version of the file in `indir` and write the
    # result to the corresponding file in `outdir` (without ".auto.")
    for afile in files:
        infile=os.path.join(indir,afile+".auto")
        outfile=os.path.join(outdir,afile)
        with open(infile,'rt') as fd:
            indata=fd.read()
        outdata=replacetxt(indata,replace)
        with open(outfile,'wt') as fd:
            fd.write(outdata)

def replacetxt(intext,replace):
    # Apply all text replacements in the `replace` hash to the `intext` string.
    outtext=str(intext)
    for rep in replace:
        outtext=outtext.replace(rep,replace[rep])
    return outtext

########################################################################

# Calculate variables to replace in text files.

def most_square_layout_that_integer_divides_ppn(nodes,ppn,nx):
    ngrid=nx*nx
    tasks=nodes*ppn
    bestx=ppn
    besty=nodes
    bestscore=abs(bestx-besty)
    for layout_x_2 in range(ppn-1):
        layout_x = layout_x_2+2
        if ppn%layout_x:
            print(ppn,'not divisible by',layout_x)
            continue # ppn not divisible by layout_x
        layout_y = tasks//layout_x
        if layout_x*layout_y != tasks:
            print('bad layout')
            continue # safeguard; should not get here
        score=abs(layout_x-layout_y)
        if score<bestscore:
            bestx=layout_x
            besty=layout_y
            bestscore=score
    return [ bestx, besty ]

def reversed_most_square_layout_that_integer_divides_ppn(nodes,ppn,nx):
    [ layout_y, layout_x ] = most_square_layout_that_integer_divides_ppn(nodes,ppn,nx)
    return [ layout_x, layout_y ]

def most_square_layout(nodes,ppn,nx):
    ngrid=nx*nx
    tasks=nodes*ppn
    bestx=1
    besty=tasks
    bestscore=abs(besty-bestx)
    for n in range(tasks-1):
        tx=n+2
        ty=tasks//tx
        if tx*ty==tasks:
            score=abs(ty-tx)
            if score<bestscore:
                bestx=tx
                besty=ty
                bestscore=score
    return [ bestx, besty ]

def blocksize_with_one_block_per_thread(layout_x,layout_y,nx,tpp):
    big_x=math.ceil(float(nx)/layout_x)
    big_y=math.ceil(float(nx)/layout_y)
    return math.ceil(float(big_x*big_y)/tpp)

def blocksize_with_lowest_remainder(layout_x,layout_y,nx,tpp):
    return max(nx//layout_x,nx//layout_y)
   
def make_hash(
        # These must match the input nml files, inputs, and bcs:
        inner_grid=601,outer_grid=1201,
              
        # execution configuration:
        queue='dev',
        walltime='03:30:00',
        OMP_STACKSIZE='2048M',
        OMP_PLACES='cores',

        # files and directories must be specified by caller:
        noscrub=None, # '/lfs/h2/oar/esrl/noscrub/samuel.trahan/'
        scrub=None, # '/lfs/h2/oar/ptmp/samuel.trahan/'
        HAFS=None, # '/lfs/h2/oar/ptmp/samuel.trahan/hafsv1_phase3/'
        template_dir=None, # '/lfs/h2/oar/ptmp/samuel.trahan/junghoon-reference/'
        autohafs_dir=None, # '/lfs/h2/oar/ptmp/samuel.trahan/AutoHAFS/junghoon-reference/'
        
        # FV3 configuration:
        exebase='32bit', # to find hafs_forecast.fd/tests/compute_(exebase).exe
        inner_nodes=16,
        outer_nodes=29,
        io_ppn=None,
        io_tpp=None,
        io_omp_num_threads=None,
        write_tasks_per_group=None,
        write_groups=2,
        comp_ppn=42,
        comp_tpp=3,
        outer_k_split = 2,
        outer_n_split = 5,
        inner_k_split = 4,
        inner_n_split = 9,
        dt_atmos = 60,
        dt_inner = None,
        inner_layout = None,
        outer_layout = None,
    
        # Choose algorithms:
        best_layout=most_square_layout,
        best_blocksize=blocksize_with_lowest_remainder,
        
        #hycom configuration:
        hycom_nodes=2,
        hycom_pes=120,

        # naming:
        prefix=None,
        more_prefix=None,
        suffix=None ):

    if suffix is None:
        suffix=''

    if dt_inner is None:
        dt_inner = dt_atmos/2

    if io_ppn is None:
        io_ppn=comp_ppn
        
    if io_tpp is None:
        io_tpp=comp_tpp

    if io_omp_num_threads is None:
        io_omp_num_threads=io_tpp
        
    if write_tasks_per_group is None:
        write_tasks_per_group=io_ppn
        
    assert( (dt_atmos%dt_inner)<0.001 )
        
    # Make sure mandatory arguments are specified:
    assert(noscrub)
    assert(scrub)
    assert(os.path.isdir(noscrub))
    assert(os.path.isdir(scrub))
    assert(exebase)
    assert(autohafs_dir)
    assert(os.path.isdir(autohafs_dir))
        
    # Can't configure this one:
    nodesize=128
    
    # directories derived:
    if not template_dir:
        template_dir=os.path.join(noscrub,'junghoon-reference/')
    if not HAFS:
        HAFS=os.path.join(noscrub,'hafsv1_phase3/')
    HAFS_test_dir=os.path.join(HAFS,'sorc/hafs_forecast.fd/tests/')
    module_src_dir=HAFS_test_dir
    modules=( 'modules.fv3_'+exebase, 'cray-pals' )
    module_loads = (' ; '.join([ "module load "+x for x in modules ]))
    module_commands = 'module use '+module_src_dir+' ; ' \
                      + module_loads + ' ; module list'
    exe=os.path.join(HAFS_test_dir,'fv3_'+exebase+'.exe')

    # FV3 compute derived:
    comp_nodes=(inner_nodes+outer_nodes)
    comp_cpus=comp_ppn*comp_tpp
    inner_pes=inner_nodes*comp_ppn
    outer_pes=outer_nodes*comp_ppn
    comp_pes=comp_nodes*comp_ppn
    if inner_layout is None:
        ( inner_layout_x, inner_layout_y ) = best_layout(inner_nodes,comp_ppn,inner_grid)
    else:
        ( inner_layout_x, inner_layout_y ) = inner_layout
        assert(inner_layout_x*inner_layout_y == inner_pes)
    if outer_layout is None:
        ( outer_layout_x, outer_layout_y ) = best_layout(outer_nodes,comp_ppn,outer_grid)
    else:
        ( outer_layout_x, outer_layout_y ) = outer_layout
        assert(outer_layout_x*outer_layout_y == outer_pes)
    inner_blocksize=best_blocksize(inner_layout_x,inner_layout_y,inner_grid,comp_tpp)
    outer_blocksize=best_blocksize(outer_layout_x,outer_layout_y,outer_grid,comp_tpp)

    # FV3 derived:
    io_pes=write_tasks_per_group*write_groups
    io_nodes=(io_pes*io_tpp+nodesize-1)//nodesize
    io_cpus=io_ppn*io_tpp
    assert(io_ppn==io_pes//io_nodes)

    # Hycom derived:
    hycom_ppn=hycom_pes//hycom_nodes
    assert(hycom_ppn*hycom_nodes==hycom_pes)
    hycom_tpp=nodesize//hycom_ppn
    hycom_cpus=hycom_ppn*hycom_tpp
    
    # nems.configure:
    atm_pes=io_pes+comp_pes
    atm_range=( 0, atm_pes-1 )
    ocn_range=( atm_pes, atm_pes+hycom_pes-1 )

    if not prefix:
        prefix="%s-n%do%dp%dt%d-io%dw%dp%d-hy%dt%d-"%(
            exebase,
            inner_nodes, outer_nodes, comp_ppn, comp_tpp,
            write_groups, write_tasks_per_group, io_ppn,
            hycom_pes, hycom_tpp )
    if more_prefix:
        prefix += more_prefix
        
    result={
        '%template_dir%': str(template_dir),
        '%scrub%': str(scrub),
        '%noscrub%': str(noscrub),
        '%prefix%': str(prefix),
        '%suffix%': str(suffix),
        '%ATM_petlist_bounds%': "%04d %04d"%atm_range,
        '%OCN_petlist_bounds%': "%04d %04d"%ocn_range,
        '%MED_petlist_bounds%': "%04d %04d"%ocn_range,
        '%comp_pes%': '%d'%( comp_pes, ),
        '%comp_tpp%': '%d'%( comp_tpp, ),
        '%io_pes%': '%d'%( io_pes, ),
        '%io_tpp%': '%d'%( io_tpp, ),
        '%io_omp_num_threads%': '%d'%( io_omp_num_threads, ),
        '%ocn_pes%': '%d'%( hycom_pes, ),
        '%ocn_tpp%': '%d'%( hycom_tpp, ),
        '%write_tasks_per_group%': "%d"%write_tasks_per_group,
        '%write_groups%': "%d"%write_groups,
        '%outer_blocksize%': "%d"%outer_blocksize,
        '%inner_blocksize%': "%d"%inner_blocksize,
        '%outer_layout%': "%d,%d"%( outer_layout_x, outer_layout_y ),
        '%inner_layout%': "%d,%d"%( inner_layout_x, inner_layout_y ),
        '%grid_pes%': "%d,%d"%( outer_pes, inner_pes ),
        '%select_comp%': "%d:mpiprocs=%d:ompthreads=%d:ncpus=%d"%( comp_nodes,comp_ppn,comp_tpp,comp_cpus ),
        '%select_io%': "%d:mpiprocs=%d:ompthreads=%d:ncpus=%d"%( io_nodes,io_ppn,io_tpp,io_cpus ),
        '%select_ocn%': "%d:mpiprocs=%d:ompthreads=%d:ncpus=%d"%( hycom_nodes,hycom_ppn,hycom_tpp,hycom_cpus ),
        '%queue%': str(queue),
        '%walltime%': str(walltime),
        '%exe%': str(exe),
        '%exebase%': str(exebase),
        '%OMP_STACKSIZE%': str(OMP_STACKSIZE),
        '%OMP_PLACES%': str(OMP_PLACES),
        '%module_commands%': str(module_commands),
        '%autohafs_dir%': str(autohafs_dir),
        '%inner_k_split%': '%d'%(inner_k_split,),
        '%inner_n_split%': '%d'%(inner_n_split,),
        '%outer_k_split%': '%d'%(outer_k_split,),
        '%outer_n_split%': '%d'%(outer_n_split,),
        '%dt_atmos%': str(dt_atmos),
        '%dt_inner%': str(dt_inner),
    }

    print('Replacements:')
    for rep in result:
        print("  %s => %s"%(rep,result[rep]))
    
    return result

if __name__ == '__main__':
    main()
