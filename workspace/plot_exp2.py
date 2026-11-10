# 과제 2 그래프: exp2.csv -> 같은 폴더에 fig5, fig6 png
# 사용법: python3 workspace/plot_exp2.py [results/exp2.csv]   (os-w3 디렉터리에서)
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "results/exp2.csv"
out = os.path.dirname(path)
rows = [r for r in csv.DictReader(open(path)) if r["phase"] == "search"]

INDEXES = ["flat", "hnsw"]
PREFETCH = ["off", "normal", "seq"]
MEMS = ["unlimited", "256m"]
C = {"off": "#2a78d6", "normal": "#eb6834", "seq": "#1baf7a"}   # prefetch 별 색 고정


def vals(idx, pf, mem, col):
    return [float(r[col]) for r in rows if r["index"] == idx and r["prefetch"] == pf and r["mem"] == mem]


def mean(idx, pf, mem, col):
    v = vals(idx, pf, mem, col)
    return sum(v) / len(v) if v else 0


def span(idx, pf, mem, col):
    # 오차 막대 [아래, 위] = 평균 - 최소값, 최대값 - 평균 (회차별 범위). 과제 1 그림과 같은 표기
    v, mu = vals(idx, pf, mem, col), mean(idx, pf, mem, col)
    return mu - min(v), max(v) - mu


def grouped(ax, col, ylabel, log=False):
    # x 축: 메모리별로 flat, hnsw 를 나란히 (unlimited | 256m), 그룹 안에 prefetch 3막대
    groups = [(i, m) for m in MEMS for i in INDEXES]
    w = 0.25
    for j, pf in enumerate(PREFETCH):
        xs = [g + (j - 1) * w for g in range(len(groups))]
        ys = [mean(i, pf, m, col) for i, m in groups]
        es = list(zip(*[span(i, pf, m, col) for i, m in groups]))   # ([아래...], [위...])
        ax.bar(xs, ys, width=w, color=C[pf], label=f"prefetch {pf}", yerr=es, capsize=2)
    ax.set_xticks(range(len(groups)), [f"{i}\n{m}" for i, m in groups])
    ax.axvline(len(INDEXES) - 0.5, color="gray", ls=":", lw=1)   # unlimited 와 256m 구분선
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("symlog")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))   # 그래프 위 바깥: 막대와 안 겹치게


def save(fig, name, rect=None):
    fig.tight_layout(rect=rect)   # rect: 그림 위쪽에 범례 자리를 남길 때
    fig.savefig(os.path.join(out, name), dpi=150)
    print("saved", os.path.join(out, name))


# 그림 5: search 작업 major fault 수
fig, ax = plt.subplots(figsize=(9, 4))
grouped(ax, "majflt", "major page faults (search)", log=True)
save(fig, "fig5_exp2_majflt.png")

# 그림 6: search 작업 wall time 분해 (그림 2 와 같은 누적 막대)
# 조건마다 시간 범위가 0.8s ~ 230s 로 달라, 로그 축에 쌓으면 비율이 왜곡되므로 (인덱스, 메모리) 별 패널 + 각자 선형 축
# 2x2 배치: 행 = 메모리 (unlimited, 256m), 열 = 인덱스 (flat, hnsw)
PARTS = [("user", "#2a78d6"), ("sys", "#eb6834"), ("run queue wait", "#1baf7a"), ("other wait (I/O)", "#eda100")]
fig, axes = plt.subplots(2, 2, figsize=(9, 6.5))
for ax, (i, m) in zip(axes.flat, [(i, m) for m in MEMS for i in INDEXES]):
    wall = [mean(i, pf, m, "seconds") for pf in PREFETCH]
    user = [mean(i, pf, m, "user_s") for pf in PREFETCH]
    sys_ = [mean(i, pf, m, "sys_s") for pf in PREFETCH]
    wait = [mean(i, pf, m, "sched_wait_s") for pf in PREFETCH]
    other = [w - u - s - q for w, u, s, q in zip(wall, user, sys_, wait)]   # 나머지 = I/O 등 대기
    bottom = [0] * len(PREFETCH)
    for part, (name, c) in zip([user, sys_, wait, other], PARTS):
        ax.bar(PREFETCH, part, bottom=bottom, color=c, label=name, width=0.6)
        bottom = [b + v for b, v in zip(bottom, part)]
    es = list(zip(*[span(i, pf, m, "seconds") for pf in PREFETCH]))
    ax.errorbar(PREFETCH, wall, yerr=es, fmt="none", ecolor="black", capsize=2)   # 막대 = 최소~최대
    ax.set_title(f"{i} / {m}", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
for ax in axes[:, 0]:
    ax.set_ylabel("search time (s)")
for ax in axes[1]:
    ax.set_xlabel("prefetch")
fig.legend(*axes[0, 0].get_legend_handles_labels(), frameon=False, ncol=4, loc="upper center")   # 그림 맨 위에 한 번
save(fig, "fig6_exp2_time.png", rect=(0, 0, 1, 0.94))
