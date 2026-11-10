# os-w3: 벡터DB(Faiss) 가용 메모리에 따른 성능 분석

## Dependencies

### Host
| 항목 | 버전 | 비고 |
|---|---|---|
| OS | Ubuntu 22.04.5 LTS | |
| Kernel | 6.8.0-138-generic | page fault / readahead 동작은 호스트 커널이 결정 |
| Docker | 29.9.2 | |
| cgroup | v2 | `--memory` 제한에 page cache 포함 |
| Swap | 활성화 필요 | 메모리 제한 시 OOM 대신 swap-in(major fault) 유도 |

### Container (`Dockerfile`)
| 항목 | 버전 |
|---|---|
| Base image | ubuntu:22.04 |
| Python | 3.10.12 |
| faiss-cpu | 1.15.1 |
| numpy | 2.2.6 |
| matplotlib | 3.10.9 |
| GNU time | apt (`/usr/bin/time -v`로 major/minor fault 측정) |

## Build

```bash
docker build -t os-w3 .
```

## Run

```bash
# 메모리 제한 없음
docker run --rm -it -v "$PWD":/work os-w3

# 메모리 제한 (swap 허용: --memory-swap > --memory)
docker run --rm -it -v "$PWD":/work --memory=1g --memory-swap=4g os-w3
```

## Host-side settings (컨테이너 내부에서 변경 불가)

```bash
# cold start: page cache 비우기
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches

# 파일 readahead (기본 128KB)
cat /sys/block/nvme1n1/queue/read_ahead_kb
echo 0 | sudo tee /sys/block/nvme1n1/queue/read_ahead_kb

# swap readahead (2^n 페이지, 기본 3)
cat /proc/sys/vm/page-cluster
echo 0 | sudo tee /proc/sys/vm/page-cluster
```

실험 후 원래 값으로 복구할 것.

## Experiments

```bash
# 과제 1: 메모리 상한(64m~1024m, unlimited) x 5회. 약 100분
./workspace/run_exp1.sh 2>&1 | tee results/run_exp1.log     # drop_caches 에 sudo. 없으면 DROP_CACHES=0
python3 workspace/plot_exp1.py                               # results/fig1~4.png

# 과제 2: 인덱스(flat/hnsw) x prefetch(off/normal/seq) x 메모리(unlimited/256m) x 3회. 약 30분
docker run --rm -v "$PWD":/work os-w3 python3 /work/workspace/build_index.py   # 인덱스 파일 생성 (한 번)
./workspace/run_exp2.sh 2>&1 | tee results/run_exp2.log     # drop_caches 에 sudo. 없으면 DROP_CACHES=0
python3 workspace/plot_exp2.py                               # results/fig5~6.png
```

## Layout
```
workspace/
  measure.py      종속변인 측정 (snapshot / diff / save_csv). exp1, exp2 공통
  exp1.py         과제 1: gen -> add -> search, 메모리 상한별 fault/시간
  run_exp1.sh     과제 1 실행 (docker run 반복)
  plot_exp1.py    과제 1 그래프
  build_index.py  과제 2: flat.index, hnsw.index 생성
  exp2.py         과제 2: mmap 로드 + madvise(prefetch) + search
  run_exp2.sh     과제 2 실행
  plot_exp2.py    과제 2 그래프
data/      인덱스 파일 (git 제외)
results/   측정 결과 csv, time -v 출력, 그래프 (git 제외)
```
