#! /bin/sh

# This script implements the reporting at the bottom of
# hafs_forecast.sh, and is intended to run in situations where that
# reporting code failed. It'll parse the hafs_forecast.out and stat
# some files to get what it needs. The cleanup_time is obvious
# nonsense (like -5783) but everything else should be fine.

set -xue

where="$1"
dt="$2"
noscrub="$3"

parent=$( dirname "$where" )
name=$( basename "$where" )

cd "$where"

start=$( grep -E 'start=[0-9]+' job.log | tail -1 | sed 's/.*=//g' )
runtime=$( grep -E 'runtime=[0-9]+' job.log | tail -1 | sed 's/.*=//g' )
end=$( grep -E 'end=[0-9]+' job.log | tail -1 | sed 's/.*=//g' )
exe=$( grep -E 'exe=.*' job.log | tail -1 | sed 's:.*tests/fv3_\(.*\).exe.*$:\1:g' )

initend=$( stat --format=%X mediator.log )
init_time=$(( initend-start ))

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
             dt='$dt';
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

mkdir -p $noscrub/fv3results
echo "$name 60 47 126 42 3 $exe cores  $start $initend $cleanbegin $end $runtime $init_time $cleanup_time $tphase $nphase $nemswall $where" >> $noscrub/fv3results/summary

mkdir -p $noscrub/fv3results/$name
ls -ltr --full-time > $noscrub/fv3results/$name/timings
cp -fp hafs_forecast.out hafs_forecast.err hafs_forecast.sh $noscrub/fv3results/$name/.
chmod -R a-w $noscrub/fv3results/$name
