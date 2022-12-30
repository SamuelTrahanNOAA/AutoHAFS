#!/bin/sh
#PBS -joe
#PBS -o job.log
#PBS -N supafast-n14o32p32t4-io2w8p16-hy120t2-dt72-st128-lay-square-bs16
#PBS -A HWRF-DEV
#PBS -q dev
#PBS -l select=46:mpiprocs=32:ompthreads=4:ncpus=128+1:mpiprocs=16:ompthreads=8:ncpus=128+2:mpiprocs=60:ompthreads=2:ncpus=120
#PBS -l place=excl
#PBS -l walltime=02:20:00

set -xue

cd $PBS_O_WORKDIR

testdir=/lfs/h2/oar/esrl/noscrub/samuel.trahan/hafsv1_phase3/sorc/hafs_forecast.fd/tests
resultdir=/lfs/h2/oar/esrl/noscrub/samuel.trahan/fv3results
exebase=32bit
testname=supafast-n14o32p32t4-io2w8p16-hy120t2-dt72-st128-lay-square-bs16
exe=$testdir/fv3_$exebase.exe

date

# Load modules.
set +xue
# This assumes the fv3_32bit executable was compiled with -DSUPAFAST=ON
module use $testdir
module load modules.fv3_$exebase
module load cray-pals
module list

set -xue

# Setup the environment
export OMP_STACKSIZE=128M
export OMP_PLACES=cores

# Delete old output.
set +e
chmod 755 ./clean.sh
./clean.sh
set -e

# Run the program.
start=$( date +%s )
mpiexec --cpu-bind core \
        -n 1472 -depth 4 /usr/bin/env OMP_NUM_THREADS=4 "$exe" \
      : -n 16 -depth 8 /usr/bin/env OMP_NUM_THREADS=4 "$exe" \
      : -n 120 -depth 2 /usr/bin/env OMP_NUM_THREADS=2 "$exe" \
        > hafs_forecast.out 2> hafs_forecast.err
end=$( date +%s )

set +eu
set -x

# Total runtime of mpiexec
runtime=$(( end-start ))

# Time before mediator.log is created
initend=$( stat --format=%X mediator.log )
init_time=$(( initend-start ))

# Time between creation of atm.nest02.f126.nc and end of mpiexec
# which is approximately the time after the last timestep ends
cleanbegin=$( stat --format=%X atm.nest02.f126.nc )
cleanup_time=$(( end-cleanbegin ))

count() {
	 awk '{
             phase_time_count+=$10;
             phase_count++;
	     if(phase_count%2 == 0) {
	        phases=phase_count;
		phase_time=phase_time_count;
	     }
           }
         END{
             kdt=phases/2;
             dt=72;
             valid_time=dt*kdt;  # seconds
             simulation_length=126*3600;  # seconds
	     expected_phase_runtime=phase_time*simulation_length/valid_time;
             print(int(expected_phase_runtime+0.5))
           }'
}

# Time spent in phase 1 & 2
tphase=$( grep phase hafs_forecast.??? | count )

# Average time spent in phase 1 & 2 in each 3hr period
nphase=$(( tphase / 42 ))

# Wallclock reported by NEMS
nemswall=$( grep 'total amount of wall' hafs_forecast.out |awk '{print int($8)}' )

mkdir -p $resultdir
stats="$testname 60 47 126 42 3 supafast cores $TOTAL_TASKS $start $initend $cleanbegin $end $runtime $init_time $cleanup_time $tphase $nphase $nemswall $PWD"
echo $stats
echo $stats >> $resultdir/summary

mkdir -p $resultdir/$testname
ls -ltr --full-time > $resultdir/$testname/timings
cp -fp hafs_forecast.out hafs_forecast.err manual_hafs_forecast.sh $resultdir/$testname/.
chmod -R a-w $resultdir/$testname

exit 0
