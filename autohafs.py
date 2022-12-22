#! /usr/bin/env python3

import sys
import os
import tempfile
import subprocess

def make_hash(
        # These must match the input nml files, inputs, and bcs:
        inner_grid=601,outer_grid=1201,
              
        # execution configuration:
        queue='dev',
        walltime='03:30:00',
        OMP_STACKSIZE='2048M',
        OMP_PLACES='cores',
        
        # fies and directories:
        noscrub=None, # '/lfs/h2/oar/esrl/noscrub/samuel.trahan/',
        scrub=None, # '/lfs/h2/oar/ptmp/samuel.trahan/',
        HAFS=None, # '/lfs/h2/oar/ptmp/samuel.trahan/hafsv1_phase3/',
        exebase=None, # 32bit, the BUILD_NR (third argument to hafs_forecast.fd/tests/compile.sh)
        template_dir, # '/lfs/h2/oar/ptmp/samuel.trahan/junghoon-reference/',
        
        # FV3 configuration:
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
    
        #hycom configuration:
        hycom_nodes=2,
        hycom_pes=120,

        # naming:
        prefix=None,
        suffix=None ):

    if suffix is None:
        suffix=''

    if dt_inner is None:
        dt_inner = dt_atmos/2.0

    # Make sure mandatory arguments are specified:
    assert(noscrub)
    assert(scrub)
    assert(os.path.isdir(noscrub))
    assert(os.path.isdir(scrub))
    assert(exebase)
        
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
    }

    print('Replacements:')
    for rep in result:
        print("  %s => %s"%(rep,result[rep]))
    
    return result
    
def best_layout(nodes,ppn,nx):
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

########################################################################

def replacetxt(intext,replace):
    outtext=intext
    for rep in replace:
        outtext=outtext.replace(rep,replace[rep])
    return outtext

def parse_files(indir,outdir,replace,files):
    for afile in files:
        infile=os.path.join(indir,afile+".auto")
        outfile=os.path.join(outdir,afile)
        with open(infile,'rt') as fd:
            indata=fd.read()
        outdata=replacetxt(indata,replace)
        with open(outfile,'wt') as fd:
            fd.write(outdata)

def fill_auto_files(replace):
    outdir=tempfile.mkdtemp(prefix=replace['%prefix%'], dir=replace['%scrub%'])
    indir=replace['%template_dir%']
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

########################################################################
    
def rsync(replace):
    rsync_command=[ "rsync", "-arv", "--ignore-existing",
                    os.path.join(replace["%template_dir%"],"."),
                    os.path.join(replace['%dir%'],'.') ]
    print('execute',rsync_command)
    sys.stdout.flush()
    subprocess.run(rsync_command,check=True)

def chdir(replace):
    print('chdir',replace['%dir%'])
    os.chdir(replace['%dir%'])

def qsub(replace):
    qsub_command=[ "qsub", "hafs_forecast.sh" ]
    print('execute',qsub_command)
    sys.stdout.flush()
    subprocess.run(qsub_command,check=True)
    
def generate_and_submit(replace):
    fill_auto_files(replace)
    print('will run in dir',replace['%dir%'])
    rsync(replace)
    chdir(replace)
    qsub(replace)

########################################################################
    
def debug_test():
    replace=make_hash(exebase='ftz-nocons-hycom',queue='debug',walltime='00:30:00',hycom_nodes=3)
    generate_and_submit(replace)
    
def basic_test():
    replace=make_hash(exebase='ftz-nocons-hycom',queue='dev',walltime='03:00:00')
    generate_and_submit(replace)
    
def sixteen():
    for i in range(3):
        replace=make_hash(exebase='ftz-nocons-hycom',inner_nodes=16,outer_nodes=29,scrub='/lfs/h2/oar/stmp/samuel.trahan/')
        generate_and_submit(replace)

def more_nodes(n):
    middle=int(16*n/45.)
    for i in [ middle-4, middle-3 ]:
        replace=make_hash(exebase='ftz-nocons-hycom',inner_nodes=i,outer_nodes=n-i)
        generate_and_submit(replace)

def hycom1():
    replace=make_hash(exebase='ftz-nocons-hycom',inner_nodes=16,outer_nodes=29,scrub='/lfs/h2/oar/ptmp/samuel.trahan/',hycom_nodes=1,OMP_STACKSIZE='128M',queue='debug',walltime='00:30:00')
    generate_and_submit(replace)

def io1():
    replace=make_hash(exebase='ftz-nocons-hycom',inner_nodes=16,outer_nodes=29,scrub='/lfs/h2/oar/ptmp/samuel.trahan/',io_nodes=1,OMP_STACKSIZE='128M',queue='debug',walltime='00:30:00')
    generate_and_submit(replace)

basic_test()
