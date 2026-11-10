#!/bin/bash
# 과제 1 실행: 메모리 제한 조건 x 반복 횟수
# os-w3 디렉터리에서 실행: ./workspace/run_exp1.sh
set -e

# 64m 부터 32m 간격으로 1024m 까지 + 제한 없음 (인덱스 512MB 전후를 촘촘히)
MEMS="$(seq -f "%gm" 64 32 1024) unlimited"
REPS=5     # 5회 반복: 평균과 최소~최대 범위로 보고
# 단일 스레드 + CPU 1개 고정: 멀티스레드는 fault 대기 중 OpenMP spin/경합이 섞여 해석이 어려움
THREADS=1
CPUS=2     # CPU 0은 인터럽트 처리가 몰리므로 피함

mkdir -p results

# 회차를 바깥 루프로: 1회차에 전 조건 -> 2회차 ... (특정 시간대의 호스트 간섭이 한 조건에 몰리지 않게)
for rep in $(seq 1 $REPS); do
  for mem in $MEMS; do
    # cold start: page cache 비우기 (호스트에서만 가능)
    # DROP_CACHES=0 으로 실행하면 생략 (sudo 없을 때)
    if [ "${DROP_CACHES:-1}" = 1 ]; then
      sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    fi

    if [ "$mem" = "unlimited" ]; then
      limit=""
    else
      limit="--memory=$mem --memory-swap=4g"
    fi

    echo "=== mem=$mem rep=$rep ==="
    docker run --rm -v "$PWD":/work -e OMP_NUM_THREADS=$THREADS --cpuset-cpus=$CPUS $limit os-w3 \
      /usr/bin/time -v -o /work/results/exp1_time_${mem}_${rep}.txt \
      python3 /work/workspace/exp1.py "$mem" "$rep"
  done
done
