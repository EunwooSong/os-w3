# 과제 2 준비: 인덱스를 한 번 만들어 파일로 저장 (HNSW 구축은 느리므로 멀티스레드, 메모리 제한 없이)
# 사용법: python3 build_index.py   -> /work/data/flat.index, /work/data/hnsw.index
import time
import faiss
import numpy as np

d, nb = 128, 1_000_000
rng = np.random.default_rng(1234)                # exp1 과 같은 데이터
xb = rng.random((nb, d), dtype=np.float32)

flat = faiss.IndexFlatL2(d)
flat.add(xb)
faiss.write_index(flat, "/work/data/flat.index")
print("flat.index written")

t = time.time()
hnsw = faiss.IndexHNSWFlat(d, 32)                # M=32: 노드당 이웃 수 (level 0 는 2M=64)
hnsw.add(xb)
faiss.write_index(hnsw, "/work/data/hnsw.index")
print(f"hnsw.index written ({time.time() - t:.0f}s, threads={faiss.omp_get_max_threads()})")
