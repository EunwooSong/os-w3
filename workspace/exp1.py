# 과제 1: 메모리 제한에 따른 page fault / 실행 시간 측정
# 사용법: python3 exp1.py <mem_label> <rep>
import sys

import faiss
import numpy as np

from measure import snapshot, diff, save_csv

d = 128          # 벡터 차원
nb = 1_000_000   # DB 벡터 수 (1M x 128 x 4B = 512MB = 488MiB)
nq = 10_000      # 쿼리 수
k = 10           # top-k
bs = 1_000       # 한 번에 검색할 쿼리 수

mem_label, rep = sys.argv[1], sys.argv[2]   # 조건 이름(64m, ..., unlimited), 반복 번호. CSV 에 그대로 기록
rows = []

# 1) 데이터 생성
s0 = snapshot()
rng = np.random.default_rng(1234)                # seed 고정: 모든 조건에서 같은 데이터
xb = rng.random((nb, d), dtype=np.float32)       # dtype 지정: float64 임시 배열(1GB) 방지
xq = rng.random((nq, d), dtype=np.float32)
s1 = snapshot()
rows.append({"mem": mem_label, "rep": rep, "phase": "gen", **diff(s0, s1)})

# 2) 인덱스 생성 + add (add 는 xb 를 복사하므로 원본은 지운다)
index = faiss.IndexFlatL2(d)
index.add(xb)
del xb
s2 = snapshot()
rows.append({"mem": mem_label, "rep": rep, "phase": "add", **diff(s1, s2)})

# 3) 검색 (bs 개씩 나눠서 -> 매 호출마다 DB 전체를 두 번 훑음: 제곱합 계산, 거리 계산)
for i in range(0, nq, bs):
    D, I = index.search(xq[i:i + bs], k)
s3 = snapshot()
rows.append({"mem": mem_label, "rep": rep, "phase": "search", **diff(s2, s3)})

for r in rows:
    print(r)
save_csv("/work/results/exp1.csv", rows)
