#! /usr/bin/env python3

import sys
import os
import tempfile
import subprocess

def main():

    where={
        'noscrub':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/',
        'HAFS':   '/lfs/h2/oar/esrl/noscrub/samuel.trahan/hafsv1_phase3/',
        'scrub':  '/lfs/h2/oar/ptmp/samuel.trahan/',
        'exebase':'supafast',
        'template_dir':'/lfs/h2/oar/esrl/noscrub/samuel.trahan/junghoon-reference/',
        'autohafs_dir': os.path.join(os.path.dirname(os.path.realpath(__file__)),'junghoon-reference'),
    }


    layout_tests(**where)

########################################################################

def layout_tests(**kwargs):
    inner_add = range(4)
    inner_min = 14
    node_count = 45
    these = {
        'lay-divppn-': most_square_layout_that_integer_divides_ppn,
        'lay-revppn-': reversed_most_square_layout_that_integer_divides_ppn,
        'lay-square-': most_square_layout,
    }
    for iadd in inner_add:
        inner_nodes = iadd+inner_min
        outer_nodes = node_count-inner_nodes
        for more_prefix, best_layout in these.items():
            replace=make_hash(more_prefix=more_prefix+'outer-k2n4-',
                              best_layout=best_layout,
                              inner_nodes=inner_nodes,outer_nodes=outer_nodes,
                              outer_k_split=2,outer_n_split=4,
                              **kwargs)
            generate_and_submit(replace)
    
def layout_tests_15(**kwargs):
    these = {
        'lay-divppn-': most_square_layout_that_integer_divides_ppn,
        'lay-revppn-': reversed_most_square_layout_that_integer_divides_ppn,
        # 'lay-square-': most_square_layout,
    }
    for more_prefix, best_layout in these.items():
        replace=make_hash(more_prefix=more_prefix,best_layout=best_layout,**kwargs)
        generate_and_submit(replace)
    
def debug_test(**kwargs):
    # Run with the defaults, but put it in the debug queue
    replace=make_hash(queue='debug',walltime='00:30:00',**kwargs)
    generate_and_submit(replace)

def basic_test(**kwargs):
    # Run with the defaults
    replace=make_hash(**kwargs)
    generate_and_submit(replace)

def sixteen_node_config(**kwargs):
    # best config so far: fv3 with 16 nodes for inner and 29 for outer
    for i in range(3): # submit 3 of them
        replace=make_hash(inner_nodes=16,outer_nodes=29,**kwargs)
        generate_and_submit(replace)
    
def outer4(**kwargs):
    # 16 node config with alternative n_split in outer domain.
    replace=make_hash(inner_nodes=16,outer_nodes=29,outer_k_split=2,outer_n_split=4,more_prefix='outer-k2n4-',**kwargs)
    generate_and_submit(replace)

def dt72(**kwargs):
    # 16 node config with 72s timestep
    replace=make_hash(inner_nodes=16,
                      outer_nodes=29,
                      outer_k_split=2,
                      outer_n_split=4,
                      inner_k_split=4,
                      inner_n_split=9,
                      dt_atmos=72,
                      more_prefix='dt72-',
                      **kwargs)
    generate_and_submit(replace)

def alternative_fv3_compute_node_count(n,**kwargs):
    # Try n fv3 compute nodes with nine different inner vs. outer node
    # counts.  Does not change the I/O or ocean nodes, so the total
    # job size is n+4 nodes.
    middle=int(16*n/45.)
    for i in [ middle-4, middle+4 ]:
        replace=make_hash(inner_nodes=i,outer_nodes=n-i,**kwargs)
        generate_and_submit(replace)

def hycom1(**kwargs):
    # cram hycom&mediator onto one node - ~500 second slower init time
    replace=make_hash(inner_nodes=16,outer_nodes=29,hycom_nodes=1,OMP_STACKSIZE='128M',queue='debug',walltime='00:30:00',**kwargs)
    generate_and_submit(replace)

def io1(**kwargs):
    # cram fv3 io onto one node - sometimes crashes
    replace=make_hash(inner_nodes=16,outer_nodes=29,io_nodes=1,OMP_STACKSIZE='128M',queue='debug',walltime='00:30:00',**kwargs)
    generate_and_submit(replace)


########################################################################

# Quasi-shell commands
    
def generate_and_submit(replace):
    # Generate the run area, chdir there, and submit the job.
    fill_auto_files(replace)
    print('will run in dir',replace['%dir%'])
    rsync(replace)
    oldcwd=os.getcwd()
    print('chdir',replace["%dir%"])
    os.chdir(replace["%dir%"])
    qsub(replace)
    print('chdir',oldcwd)
    os.chdir(oldcwd)

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
            'model_configure', 'nems.configure', 'clean.sh' ]
    parse_files(indir,outdir,replace,files)
    for afile in files:
        fullfile=os.path.join(outdir,afile)
        if not os.path.exists(fullfile):
            sys.stderr.write(fullfile+": does not exist")
        if not os.path.getsize(fullfile)>0:
            sys.stderr.write(fullfile+": is empty")

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

def best_blocksize(layout_x,layout_y,nx):
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
        exebase='32bit', # to find hafs_forecast.fd/tests/fv3_(exebase).exe
        inner_nodes=15,
        outer_nodes=30,
        io_nodes=2,
        write_groups=2,
        fv3_ppn=42,
        fv3_tpp=3,
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
    module_commands = 'module use '+module_src_dir+' ; ' + (' ; '.join([ "module load "+x for x in modules ])) + ' ; module list'
    exe=os.path.join(HAFS_test_dir,'fv3_'+exebase+'.exe')
    
    # FV3 derived:
    fv3_nodes=(inner_nodes+outer_nodes+io_nodes)
    fv3_cpus=fv3_ppn*fv3_tpp
    inner_pes=inner_nodes*fv3_ppn
    outer_pes=outer_nodes*fv3_ppn
    fv3_pes=fv3_nodes*fv3_ppn
    write_tasks_per_group=io_nodes*fv3_ppn//write_groups
    assert(write_tasks_per_group*write_groups==io_nodes*fv3_ppn)
    if inner_layout is None:
        ( inner_layout_x, inner_layout_y ) = best_layout(inner_nodes,fv3_ppn,inner_grid)
    else:
        ( inner_layout_x, inner_layout_y ) = inner_layout
        assert(inner_layout_x*inner_layout_y == inner_pes)
    if outer_layout is None:
        ( outer_layout_x, outer_layout_y ) = best_layout(outer_nodes,fv3_ppn,outer_grid)
    else:
        ( outer_layout_x, outer_layout_y ) = outer_layout
        assert(outer_layout_x*outer_layout_y == outer_pes)
    inner_blocksize=best_blocksize(inner_layout_x,inner_layout_y,inner_grid)
    outer_blocksize=best_blocksize(outer_layout_x,outer_layout_y,outer_grid)

    # Hycom derived:
    hycom_ppn=hycom_pes//hycom_nodes
    assert(hycom_ppn*hycom_nodes==hycom_pes)
    hycom_tpp=nodesize//hycom_ppn
    hycom_cpus=hycom_ppn*hycom_tpp
    
    # nems.configure:
    fv3_range=( 0, fv3_pes-1 )
    hycom_range=( fv3_pes, fv3_pes+hycom_pes-1 )

    if not prefix:
        prefix="%s-in%dou%dio%dp%dt%d-hy%dt%d-"%(
            exebase,
            inner_nodes, outer_nodes, io_nodes,
            fv3_ppn, fv3_tpp,
            hycom_pes, hycom_tpp )
    if more_prefix:
        prefix += more_prefix
        
    result={
        '%template_dir%': str(template_dir),
        '%scrub%': str(scrub),
        '%noscrub%': str(noscrub),
        '%prefix%': str(prefix),
        '%suffix%': str(suffix),
        '%ATM_petlist_bounds%': "%04d %04d"%fv3_range,
        '%OCN_petlist_bounds%': "%04d %04d"%hycom_range,
        '%MED_petlist_bounds%': "%04d %04d"%hycom_range,
        '%atm_pes%': '%d'%( fv3_pes, ),
        '%atm_tpp%': '%d'%( fv3_tpp, ),
        '%ocn_pes%': '%d'%( hycom_pes, ),
        '%ocn_tpp%': '%d'%( hycom_tpp, ),
        '%write_tasks_per_group%': "%d"%write_tasks_per_group,
        '%write_groups%': "%d"%write_groups,
        '%outer_blocksize%': "%d"%outer_blocksize,
        '%inner_blocksize%': "%d"%inner_blocksize,
        '%outer_layout%': "%d,%d"%( outer_layout_x, outer_layout_y ),
        '%inner_layout%': "%d,%d"%( inner_layout_x, inner_layout_y ),
        '%grid_pes%': "%d,%d"%( outer_pes, inner_pes ),
        '%select_atm%': "%d:mpiprocs=%d:ompthreads=%d:ncpus=%d"%( fv3_nodes,fv3_ppn,fv3_tpp,fv3_cpus ),
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
