# 과제 2: 인덱스 종류(Flat / HNSW) x 리눅스 prefetch(readahead) 에 따른 page fault 측정
# 사용법: python3 exp2.py <index_path> <prefetch> <mem_label> <rep>
#   prefetch: off | normal | seq  (아래 ADVICE 참고)
import ctypes
import mmap
import os
import sys

import faiss
import numpy as np

from measure import snapshot, diff, save_csv

d = 128
nq = 2_000       # 쿼리 수 (exp1 의 1/5: 256m 조건에서 디스크 I/O 를 줄이기 위해)
k = 10
bs = 1_000       # 한 번에 검색할 쿼리 수

index_path, prefetch, mem_label, rep = sys.argv[1:5]
index_name = os.path.basename(index_path).split(".")[0]   # flat / hnsw

# 파일 mmap 영역에 대한 커널 readahead(prefetch) 설정. madvise(2) 로 지정
ADVICE = {
    "off": mmap.MADV_RANDOM,       # readahead 끔: fault 난 페이지 1개만 읽음 (faiss 의 기본값)
    "normal": mmap.MADV_NORMAL,    # 기본 readahead: fault 주변 read_ahead_kb(128KB = 32페이지) 를 읽음
    "seq": mmap.MADV_SEQUENTIAL,   # 순차 접근 가정: 앞쪽을 더 공격적으로 읽고 지나간 페이지는 버림
}
libc = ctypes.CDLL("libc.so.6", use_errno=True)


def drop_page_cache(path):
    # 이 파일의 페이지 캐시를 비워 cold start 로 만든다 (sudo 불필요)
    fd = os.open(path, os.O_RDONLY)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    os.close(fd)


def madvise_file(path, advice):
    # faiss 가 mmap 한 영역을 /proc/self/maps 에서 찾아 madvise 를 덮어쓴다
    # (faiss 는 mmap 직후 MADV_RANDOM 을 걸어 readahead 를 꺼 둔다: faiss/impl/mapped_io.cpp)
    for line in open("/proc/self/maps"):
        if line.rstrip().endswith(path):
            start, end = (int(x, 16) for x in line.split()[0].split("-"))
            assert libc.madvise(ctypes.c_void_p(start), ctypes.c_size_t(end - start), advice) == 0
            return
    raise RuntimeError("mmap region not found: " + path)


xq = np.random.default_rng(999).random((nq, d), dtype=np.float32)   # 쿼리 (DB 와 다른 seed)
rows = []
label = {"index": index_name, "prefetch": prefetch, "mem": mem_label, "rep": rep}

# 1) 로드: 파일을 mmap 으로 연다 (복사 없음, 페이지는 접근할 때 fault 로 들어옴)
drop_page_cache(index_path)
s0 = snapshot()
index = faiss.read_index(index_path, faiss.IO_FLAG_MMAP_IFC)
madvise_file(index_path, ADVICE[prefetch])
s1 = snapshot()
rows.append({**label, "phase": "load", **diff(s0, s1)})

# 2) 검색 (bs 개씩 나눠서)
for i in range(0, nq, bs):
    D, I = index.search(xq[i:i + bs], k)
s2 = snapshot()
rows.append({**label, "phase": "search", **diff(s1, s2)})

for r in rows:
    print(r)
save_csv("/work/results/exp2.csv", rows)
