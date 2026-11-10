#!/bin/bash
# 과제 2 실행: 인덱스(flat/hnsw) x prefetch(off/normal/seq) x 메모리(unlimited/256m) x 반복
# os-w3 디렉터리에서 실행: ./workspace/run_exp2.sh
# 사전 준비: docker run --rm -v "$PWD":/work os-w3 python3 /work/workspace/build_index.py
set -e

INDEXES="flat hnsw"
PREFETCH="off normal seq"
MEMS="unlimited 256m"
REPS=5
START=${START:-1}   # 시작 회차. 예: START=4 ./workspace/run_exp2.sh -> 4, 5회차만 실행 (결과는 exp2.csv 에 이어 붙음)
# 과제 1 과 같은 조건: 단일 스레드 + CPU 1개 고정
THREADS=1
CPUS=2

mkdir -p results
echo "start: $(date '+%F %T') governor=$(cat /sys/devices/system/cpu/cpu$CPUS/cpufreq/scaling_governor) read_ahead_kb=$(cat /sys/block/nvme1n1/queue/read_ahead_kb) page-cluster=$(cat /proc/sys/vm/page-cluster) load=$(cut -d' ' -f1-3 /proc/loadavg)"

# 회차를 바깥 루프로 (특정 시간대의 호스트 간섭이 한 조건에 몰리지 않게)
for rep in $(seq $START $REPS); do
  for idx in $INDEXES; do
    for pf in $PREFETCH; do
      for mem in $MEMS; do
        # cold start: 페이지 캐시 비우기 (exp2.py 의 fadvise 와 이중 보장). DROP_CACHES=0 이면 생략
        if [ "${DROP_CACHES:-1}" = 1 ]; then
          sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
        fi

        if [ "$mem" = "unlimited" ]; then
          limit=""
        else
          limit="--memory=$mem --memory-swap=4g"
        fi

        echo "=== index=$idx prefetch=$pf mem=$mem rep=$rep ==="
        docker run --rm -v "$PWD":/work -w /work/workspace -e OMP_NUM_THREADS=$THREADS --cpuset-cpus=$CPUS $limit os-w3 \
          /usr/bin/time -v -o /work/results/exp2_time_${idx}_${pf}_${mem}_${rep}.txt \
          python3 /work/workspace/exp2.py /work/data/$idx.index "$pf" "$mem" "$rep"
      done
    done
  done
done
echo "end: $(date '+%F %T')"
