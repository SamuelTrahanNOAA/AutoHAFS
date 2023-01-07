#! /usr/bin/env python3

import sys
import os
import tempfile
import subprocess
import math

# Main entry point to the program:
def main():

    # STEP 1: You will need to edit these paths:
    where={
        # summary statistics go in a subdirectory of this:
        'noscrub':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/',

        # Location of your HAFS repo clone:
        'HAFS':   '/lfs/h2/oar/esrl/noscrub/samuel.trahan/hafsv1_phase3/',

        # Name of the executable = {HAFS}/hafs_forecast.fd/tests/fv3_{exebase}.exe
        'exebase':'32bit',

        # The forecast to run. This has INPUT, static files, and all that other nice stuff:
        'template_dir':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/junghoon-reference/',

        # The junghoon-reference subdirectory of the AutoHAFS clone. This is used to
        # generate the input*nml, model_configure and nems.configure:
        'autohafs_dir': os.path.join(os.path.dirname(os.path.realpath(__file__)),'junghoon-reference'),

        # Scrub space. The test cases' run directories will be subdirectories of this:
        'scrub':  '/lfs/h2/oar/ptmp/samuel.trahan/',
    }

    # STEP 2: do this to generate string replacements based on a test case configuration:
    #
    #     replacements = make_hash(... a test case configuration ...)
    #
    # STEP 3: Generate and (if desired) automatically submit test cases
    # 
    #     Option 1: just generate the test cast directory, but do not submit hafs_forecast.sh:
    #
    #         generate(replacements)
    #
    #     Option 2: generate the test case directory AND submit the hafs_forecast.sh:
    #
    #         generate_and_submit(replacements)
    #
    # Using generate_and_submit is convenient when generating many cases at once.

    # For convenience, I keep these in subroutines.

    # Run several tests with 128 nodes:
    with32t4(dt=72,**where)

    # Run various blocksizes
    #blocksize_test(72, [ 8, 16, 32, 64 ], **where)
    
########################################################################

def decomp_tests(**kwargs):
    # This is a test of two different decompositions to see if they get the same results (they didn't)
    replace=make_hash(
        # Run in the debug queue:
        queue='debug',
        # With a 30 minute wallclock limit:
        walltime='00:30:00',
        # Using 15 nodes for  the inner domain:
        inner_nodes=15,
        # And 30 nodes for the outer domain:
        outer_nodes=30,
        # 60 ppn and 2 threads per rank for the FV3 compute ranks
        comp_ppn=60,comp_tpp=2,
        # Inner domain (nest) layout=15,60
        inner_layout=[15,60],
        # Outer domain layout=120,15
        outer_layout=[120,15],
        # Disable the best layout algorithm. Not actually necessary
        # since it turns off automatically when a layout is specified
        best_layout=None,
        # Prepend a string to the test name.
        more_prefix='decomp-test-',
        # Pass any named arguments to this function into make_hash
        **kwargs)
    generate_and_submit(replace)

    # Second test is the same as the first, but with a different decomposition.
    replace=make_hash(
        # Run in the debug queue:
        queue='debug',
        # With a 30 minute wallclock limit:
        walltime='00:30:00',
        # Using 25 nodes for  the inner domain:
        inner_nodes=25,
        # And 15 nodes for the outer domain:
        outer_nodes=25,
        # 40 ranks per node and 3 threads per rank for FV3 compute
        comp_ppn=40,comp_tpp=3,
        # Inner domain layout=25,40
        inner_layout=[25,40],
        # Outer domain layout=40,25
        outer_layout=[40,25],
        # Disable the best layout algorithm. Not actually necessary
        # since it turns off automatically when a layout is specified
        best_layout=None,
        # Prepend a string to the test name.
        more_prefix='decomp-test-',
        # Pass any named arguments to this function into make_hash
        **kwargs)
    generate_and_submit(replace)

def with32t4(dt,**kwargs):
    # This function produces several tests in a loop and submits them all.

    # Number of FV3 compute nodes
    fv3_compute_nodes=46

    # List of all inner domain node counts to test.
    inner_nodes_list=[ 14 ]

    # All layout algorithms to test
    layouts = {
        #'lay-divppn-': most_square_layout_that_integer_divides_ppn,
        #'lay-revppn-': reversed_most_square_layout_that_integer_divides_ppn,
        'lay-square-': most_square_layout,
    }

    # Block size algorithms. There was a loop over this, but now there isn't:
    blocksizes = {
        'bsth-': blocksize_with_one_block_per_thread,
        '': blocksize_with_lowest_remainder,
    }

    # Extra prefix on the test name to indicate the block size algorithm:
    blocksize_prefix=''

    # Block size algorithm:
    best_blocksize=blocksizes[blocksize_prefix]

    # Submit two tests of each combination:
    for i in range(1):
        # Loop over all selected layouts.
        for layout_prefix, best_layout in layouts.items():
            # Loop over all selected inner domain node counts:
            for inner_nodes in inner_nodes_list:
                # Calculate the number of outer domain nodes:
                outer_nodes=fv3_compute_nodes-inner_nodes

                # Generate the replacement strings:
                replace=make_hash(inner_nodes=inner_nodes, # number of inner domain nodes
                                  outer_nodes=outer_nodes, # number of outer domain nodes

                                  # fv3 compute: 32 ranks per node, 4 threads per rank
                                  comp_ppn=32,
                                  comp_tpp=4,

                                  # Set the blocksizes:
                                  inner_blocksize=16,
                                  outer_blocksize=16,

                                  # Number of write tasks per group:
                                  write_tasks_per_group=8,

                                  # FV3 io is allocated 16 ranks per node and 8 threads per rank:
                                  io_ppn=16,
                                  io_tpp=8,

                                  # Only run 4 threads per rank on I/O
                                  # ranks, even if another number is
                                  # allocated:
                                  io_omp_num_threads=4,

                                  # k and n splits for outer and inner domains:
                                  outer_k_split=2,
                                  outer_n_split=4,
                                  inner_k_split=4,
                                  inner_n_split=9,

                                  # The timestep, passed in from the argument list:
                                  dt_atmos=dt,

                                  # Layout and block size calculation algorithms:
                                  best_layout=best_layout,
                                  best_blocksize=None,

                                  # OpenMP stack size:
                                  OMP_STACKSIZE="128M",
                                  
                                  # Wallclock limit. Shorter than the
                                  # 3:30 default since we know it
                                  # won't take that long.
                                  walltime="02:20:00",
                                  
                                  # Test name prefix.
                                  more_prefix='dt%d-st128-%s%s'%(dt,layout_prefix,blocksize_prefix),

                                  # Pass any other named arguments
                                  **kwargs)

                # Make the test directory for this case, and submit hafs_forecast.sh
                generate_and_submit(replace)


def blocksize_test(dt,blocksizes,**kwargs):
    # This test looked for the ideal blocksize. It turned out to be 16
    fv3_compute_nodes=46
    inner_nodes=14
    outer_nodes=fv3_compute_nodes-inner_nodes
    for i in range(1):
        for blocksize in blocksizes:
                replace=make_hash(inner_nodes=inner_nodes,
                                  outer_nodes=outer_nodes,
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
                                  outer_blocksize=blocksize,
                                  inner_blocksize=blocksize,
                                  OMP_STACKSIZE="128M",
                                  walltime="02:20:00",
                                  more_prefix='dt%d-bs%d-'%(dt,blocksize),
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
    # Copies the *.auto files to the test directory without the .auto
    # extension, and applies all replacements in the replace hash.

    # Add a few directories to the "replace" hash before using it:
    outdir=tempfile.mkdtemp(prefix=replace['%prefix%'], dir=replace['%scrub%'])
    indir=replace['%autohafs_dir%']
    replace['%name%'] = str(os.path.basename(outdir))
    replace['%dir%'] = str(outdir)

    # Sanity check. Does the executable exist?
    if not os.access(replace['%exe%'],os.X_OK):
        sys.stderr.write(replace['%exe%']+': cannot execute\n')

    # These are the files that should be replaced:
    files=[ 'hafs_forecast.sh', 'input_nest02.nml', 'input.nml',
            'model_configure', 'nems.configure', 'clean.sh', 'lookit.sh' ]

    # These to should be chmod to be executable:
    exe=[ 'clean.sh', 'lookit.sh' ]

    # Copy the files, 
    parse_files(indir,outdir,replace,files)

    # Make sure they exist, and chmod some of them to 0755:
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
    # Layout generator that tries to make the layout as square as
    # possible while also integer dividing ppn.
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
    # Transposes most_square_layout_that_integer_divides_ppn
    [ layout_y, layout_x ] = most_square_layout_that_integer_divides_ppn(nodes,ppn,nx)
    return [ layout_x, layout_y ]

def most_square_layout(nodes,ppn,nx):
    # Generates the most square layout possible.
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
    # Generates blocksize to have exactly one block per thread. This is quite slow.
    big_x=math.ceil(float(nx)/layout_x)
    big_y=math.ceil(float(nx)/layout_y)
    return math.ceil(float(big_x*big_y)/tpp)

def blocksize_with_lowest_remainder(layout_x,layout_y,nx,tpp):
    # Tries to minimize the remainder. Not 100% accurate, and also quite slow
    # A blocksize of 16 seems to be best.
    return max(nx//layout_x,nx//layout_y)
   
def make_hash(
        # These must match the input nml files, inputs, and bcs:
        inner_grid=601,outer_grid=1201,
              
        # execution configuration:
        queue='dev',
        walltime='03:30:00',
        OMP_STACKSIZE='2048M',
        OMP_PLACES='cores',

        # Files and directories must be specified by caller as absolute paths:

        noscrub=None, # parent of fv3results, which has the summary statistics
        scrub=None, # parent of the directory that contains the test case
        HAFS=None, # HAFS clone. Executables are at {HAFS}/hafs_forecast.fd/tests/fv3_{exebase}.exe
        template_dir=None, # Location of the directory with INPUT, static files, etc.
        autohafs_dir=None, # Directory with the *.auto files for input.nml, nems.configure, etc.
        
        # FV3 configuration:
        exebase='32bit', # to find {HAFS}/hafs_forecast.fd/tests/fv3_{exebase}.exe
        inner_nodes=16, # node count for inner domain
        outer_nodes=29, # node count for outer domain
        io_ppn=None, # number of ranks per node for FV3 I/O nodes
        io_tpp=None, # threads per rank for to allocate for FV3 I/O nodes
        io_omp_num_threads=None, # threads per rank to run for FV3 I/O nodes (must be <= io_tpp)
        write_tasks_per_group=None, # Number of write tasks per group (model_configure)
        write_groups=2, # number of write groups (model_configure)
        comp_ppn=42, # Ranks per node for FV3 compute
        comp_tpp=3,  # threads per node for FV3 compute
        outer_k_split = 2,  # outer domain k_split
        outer_n_split = 5,  # outer domain n_split
        inner_k_split = 4,  # inner domain k_split
        inner_n_split = 9,  # inner domain n_split
        dt_atmos = 60,      # dt_atmos for both domains
        dt_inner = None,    # dt_inner for both domains (should be dt_atmos/2)
        inner_layout = None, # 2 element array with layout for inner domain, or None to use best_layout()
        outer_layout = None, # 2 element array with layout for outer domain, or None to use best_layout()

        inner_blocksize = 16, # blocksize for inner domain
        outer_blocksize = 16, # blocksize for outer domain
    
        # Algorithm to decide the best layout if the inner or outer
        # layout are unspecified:
        best_layout=most_square_layout,

        # Used if inner or outer_blocksize are None. Decides blocksize.
        # Both algorithms are bad. You should use 16 instead.
        best_blocksize=blocksize_with_lowest_remainder,
        
        #hycom configuration:
        hycom_nodes=2,
        hycom_pes=120,

        # naming of the test case, used for directory name and summary statistics:
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

    # FV3 compute derived quantities:
    comp_nodes=(inner_nodes+outer_nodes)
    comp_cpus=comp_ppn*comp_tpp
    inner_pes=inner_nodes*comp_ppn
    outer_pes=outer_nodes*comp_ppn
    comp_pes=comp_nodes*comp_ppn

    # Decide the layout if it isn't provided:
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

    # Decide the blocksize if it isn't provided:
    if not inner_blocksize:
        inner_blocksize=best_blocksize(inner_layout_x,inner_layout_y,inner_grid,comp_tpp)
    if not outer_blocksize:
        outer_blocksize=best_blocksize(outer_layout_x,outer_layout_y,outer_grid,comp_tpp)

    # FV3 I/O derived numbers:
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

    # Test name prefix:
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
