# 과제 1 그래프: exp1.csv -> 같은 폴더에 fig1~fig4 png
# 사용법: python3 workspace/plot_exp1.py [results/exp1.csv]   (os-w3 디렉터리에서)
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")  # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "results/exp1.csv"
out = os.path.dirname(path)
rows = list(csv.DictReader(open(path)))


def mb(label):
    # 정렬용: "256m" -> 256, "1g" -> 1024, "unlimited" -> 무한대
    if label == "unlimited":
        return float("inf")
    return int(label[:-1]) * (1024 if label.endswith("g") else 1)


mems = sorted({r["mem"] for r in rows}, key=mb)
ticks = ["none" if m == "unlimited" else str(int(mb(m))) for m in mems]
x = range(len(mems))


def mean(phase, col):
    # 조건별 반복 평균
    res = []
    for m in mems:
        v = [float(r[col]) for r in rows if r["mem"] == m and r["phase"] == phase]
        res.append(sum(v) / len(v))
    return res


INDEX_MIB = 1_000_000 * 128 * 4 / 2**20   # 인덱스 크기 = 512,000,000 B = 488.3 MiB (Docker 의 512m 은 512 MiB)

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # blue, orange, aqua, yellow


def style(ax, ylabel):
    # 데이터 점은 32MiB 마다 그대로 두고, 눈금 글자는 64, 128, 256, ..., 1024, none 만 가로로 적어 읽기 쉽게
    pos = [i for i, t in enumerate(ticks) if t == "none" or int(t) % 128 == 0 or i == 0]
    ax.set_xticks(pos, ["\nnone" if ticks[i] == "none" else ticks[i] for i in pos])   # none 은 1024 와 겹치지 않게 한 줄 아래
    ax.set_xlabel("memory limit (MB)")
    ax.set_ylabel(ylabel)
    # 인덱스 크기 위치에 점선. 조건이 64m 부터 32MiB 등간격이므로 눈금 위치 = (MiB - 64) / 32
    ax.axvline((INDEX_MIB - mb(mems[0])) / 32, color="gray", ls=":", lw=1)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def span(phase, col):
    # 오차 막대 [아래, 위] = 평균 - 최소값, 최대값 - 평균 (회차별 범위). 모든 그림에서 같은 표기
    # 5회뿐이라 표준편차보다 범위가 정직하고, 로그 축에서도 0 밑으로 내려가지 않음
    lo, hi = [], []
    for m, mu in zip(mems, mean(phase, col)):
        v = [float(r[col]) for r in rows if r["mem"] == m and r["phase"] == phase]
        lo.append(mu - min(v))
        hi.append(max(v) - mu)
    return [lo, hi]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name), dpi=150)
    print("saved", os.path.join(out, name))


# 그림 1: search 작업 major / minor fault 수
fig, ax = plt.subplots(figsize=(10, 4))
ax.errorbar(x, mean("search", "majflt"), yerr=span("search", "majflt"), fmt="o-", color=C[0], capsize=2, label="major fault")   # 막대 = 최소~최대
ax.errorbar(x, mean("search", "minflt"), yerr=span("search", "minflt"), fmt="s-", color=C[1], capsize=2, label="minor fault")
ax.set_yscale("symlog")  # 0 도 표시되는 로그 축
style(ax, "page faults (search)")
ax.legend(frameon=False)
save(fig, "fig1_search_faults.png")

# 그림 2: search 작업 wall time 분해 (누적 막대)
wall, user, sys_, wait = (mean("search", c) for c in ["seconds", "user_s", "sys_s", "sched_wait_s"])
other = [w - u - s - q for w, u, s, q in zip(wall, user, sys_, wait)]  # 나머지 = I/O 등 대기
fig, ax = plt.subplots(figsize=(10, 4))
bottom = [0] * len(mems)
for vals, name, c in [(user, "user", C[0]), (sys_, "sys", C[1]),
                      (wait, "run queue wait", C[2]), (other, "other wait (I/O)", C[3])]:
    ax.bar(x, vals, bottom=bottom, color=c, label=name, width=0.8)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.errorbar(x, wall, yerr=span("search", "seconds"), fmt="none", ecolor="black", capsize=2)  # 막대 = 최소~최대
style(ax, "search time (s)")
ax.legend(frameon=False)
save(fig, "fig2_search_time.png")

# 그림 3: add 작업 시간과 major fault (스케일이 달라 패널 분리)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
a1.bar(x, mean("add", "seconds"), color=C[0], width=0.8)
style(a1, "add time (s)")
a2.bar(x, mean("add", "majflt"), color=C[1], width=0.8)
style(a2, "add major faults")
save(fig, "fig3_add.png")

# 그림 4: cgroup 최대 메모리 / swap 사용량 (search 종료 시점 누적값)
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(x, [v / 2**20 for v in mean("search", "memory_peak")], "o-", color=C[0], label="memory.peak")
ax.plot(x, [v / 2**20 for v in mean("search", "swap_peak")], "s-", color=C[1], label="swap.peak")
ax.axhline(512, color="gray", ls=":", lw=1)  # 인덱스 크기
style(ax, "MB")
ax.legend(frameon=False)
save(fig, "fig4_peak.png")
