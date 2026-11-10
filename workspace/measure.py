# 종속변인 측정 (과제 1, 2 공통)
# 사용법: 작업 앞뒤에서 snapshot() 을 찍고, diff(start, end) 로 그 작업 동안의 변화량을 얻는다.
#   s0 = snapshot(); ...작업...; s1 = snapshot()
#   rows.append({"mem": "256m", "rep": 1, "phase": "search", **diff(s0, s1)})
#   save_csv("/work/results/exp1.csv", rows)
import csv
import os
import resource
import time


def read_cgroup():
    # 컨테이너 자신의 cgroup 통계 (컨테이너 안에서는 /sys/fs/cgroup 이 자기 cgroup)
    stat = {}
    with open("/sys/fs/cgroup/memory.stat") as f:        # pgfault, pgmajfault, workingset_refault_anon ...
        for line in f:
            key, value = line.split()
            stat[key] = int(value)
    # memory.pressure (PSI): "some avg10=.. avg60=.. avg300=.. total=<us>"
    #   some = 메모리 때문에 태스크가 1개 이상 멈춘 누적 시간(us), full = 모두 멈춘 시간
    with open("/sys/fs/cgroup/memory.pressure") as f:
        for line in f:
            kind = line.split()[0]
            stat["pressure_" + kind] = int(line.split("total=")[1])
    with open("/sys/fs/cgroup/memory.peak") as f:        # 물리 메모리 최대 사용량
        stat["memory_peak"] = int(f.read())
    with open("/sys/fs/cgroup/memory.swap.peak") as f:   # swap 최대 사용량
        stat["swap_peak"] = int(f.read())
    return stat


def read_schedstat():
    # /proc/<pid>/task/<tid>/schedstat: "<CPU 실행 ns> <run queue 대기 ns> <타임슬라이스 수>"
    # 스레드가 1개면 한 줄이지만, 확인 차원에서 모든 task 를 합산
    run_ns, wait_ns = 0, 0
    for tid in os.listdir("/proc/self/task"):
        with open(f"/proc/self/task/{tid}/schedstat") as f:
            run, wait, _ = f.read().split()
            run_ns += int(run)
            wait_ns += int(wait)
    return run_ns, wait_ns


def snapshot():
    r = resource.getrusage(resource.RUSAGE_SELF)
    run_ns, wait_ns = read_schedstat()
    return {
        "time": time.perf_counter(),
        "utime": r.ru_utime,      # user CPU 시간
        "stime": r.ru_stime,      # kernel CPU 시간 (fault 처리 등)
        "nivcsw": r.ru_nivcsw,    # 비자발적 문맥교환 (다른 작업에 CPU 빼앗김)
        "run_ns": run_ns,
        "wait_ns": wait_ns,
        "majflt": r.ru_majflt,    # major fault: 디스크(swap) I/O 가 필요했던 fault
        "minflt": r.ru_minflt,    # minor fault: 메모리에 있어서 매핑만 한 fault
        "cg": read_cgroup(),
    }


def diff(start, end):
    # 두 스냅샷의 차이 = 그 작업 동안 일어난 양 (peak 는 누적 최대값이라 차이가 아님)
    return {
        "seconds": round(end["time"] - start["time"], 4),
        "user_s": round(end["utime"] - start["utime"], 4),
        "sys_s": round(end["stime"] - start["stime"], 4),
        "sched_run_s": round((end["run_ns"] - start["run_ns"]) / 1e9, 4),
        "sched_wait_s": round((end["wait_ns"] - start["wait_ns"]) / 1e9, 4),
        "nivcsw": end["nivcsw"] - start["nivcsw"],
        "majflt": end["majflt"] - start["majflt"],
        "minflt": end["minflt"] - start["minflt"],
        "cg_pgmajfault": end["cg"]["pgmajfault"] - start["cg"]["pgmajfault"],
        "cg_pgfault": end["cg"]["pgfault"] - start["cg"]["pgfault"],
        "cg_refault_anon": end["cg"]["workingset_refault_anon"] - start["cg"]["workingset_refault_anon"],
        "pressure_some_us": end["cg"]["pressure_some"] - start["cg"]["pressure_some"],
        "pressure_full_us": end["cg"]["pressure_full"] - start["cg"]["pressure_full"],
        "memory_peak": end["cg"]["memory_peak"],
        "swap_peak": end["cg"]["swap_peak"],
    }


def save_csv(path, rows):
    # 측정이 끝난 뒤 한 번만 쓴다. 파일이 없으면 헤더부터
    new_file = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if new_file:
            writer.writeheader()
        writer.writerows(rows)
