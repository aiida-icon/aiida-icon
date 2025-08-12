#!/bin/bash
exec > _scheduler-stdout.txt
exec 2> _scheduler-stderr.txt
export OMP_NUM_THREADS=2


'mpirun' '-np' '10' '/bin/bash'
