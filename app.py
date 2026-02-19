from flask import Flask, render_template, jsonify, request
from croll import get_all_doctors, get_schedule_range
import calendar
import time
import threading

app = Flask(__name__)

# 전체 캐시
_doctors = []
_dept_list = []
# { "과이름": [ { name, title, empId, schedule: [...] }, ... ] }
_schedule_cache = {}


def calc_range_from_now():
    """현재 기준 앞뒤 3개월 범위"""
    now = time.localtime()
    year, month = now.tm_year, now.tm_mon

    sy, sm = year, month - 3
    while sm < 1:
        sm += 12
        sy -= 1

    ey, em = year, month + 3
    while em > 12:
        em -= 12
        ey += 1

    last_day = calendar.monthrange(ey, em)[1]
    start = f"{sy}{sm:02d}01"
    end = f"{ey}{em:02d}{last_day:02d}"
    return start, end


def preload_all():
    """서버 시작 시 모든 과의 스케줄을 미리 로드"""
    global _doctors, _dept_list, _schedule_cache

    print("의사 목록 로딩 중...")
    _doctors = get_all_doctors()
    print(f"총 {len(_doctors)}명 로드 완료")

    # 과 목록 구성
    dept_set = {}
    dept_doctors_map = {}  # deptNm -> [doctor, ...]
    for d in _doctors:
        dept = d["doctorDept"]
        nm = dept["deptNm"]
        code = dept["deptCd"]
        if code not in dept_set:
            dept_set[code] = {
                "deptCd": code,
                "deptNm": nm,
                "emrDeptCd": dept["emrDeptCd"],
                "count": 0
            }
        dept_set[code]["count"] += 1
        dept_doctors_map.setdefault(nm, []).append(d)

    _dept_list = sorted(dept_set.values(), key=lambda x: x["deptNm"])
    print(f"{len(_dept_list)}개 진료과 확인")

    # 전체 스케줄 프리로드
    start_ymd, end_ymd = calc_range_from_now()
    print(f"스케줄 범위: {start_ymd} ~ {end_ymd}")

    total = sum(len(docs) for docs in dept_doctors_map.values())
    loaded = 0

    for dept_nm, docs in dept_doctors_map.items():
        results = []
        for d in docs:
            emp_id = d["empId"]
            emr_dept_cd = d["doctorDept"]["emrDeptCd"]
            name = d["drName"]
            title = d.get("hptlJobTitle", "")

            try:
                schedule = get_schedule_range(emp_id, emr_dept_cd, start_ymd, end_ymd)
            except Exception:
                schedule = []

            results.append({
                "name": name,
                "title": title,
                "empId": emp_id,
                "schedule": schedule
            })

            loaded += 1
            if loaded % 10 == 0:
                print(f"  [{loaded}/{total}] 로딩 중...")

            time.sleep(0.2)

        _schedule_cache[dept_nm] = {
            "doctors": results,
            "rangeStart": start_ymd,
            "rangeEnd": end_ymd
        }

    print(f"전체 스케줄 로드 완료! ({loaded}명)")


def daily_refresh():
    """매일 새벽 5시에 데이터 갱신 (백그라운드 스레드)"""
    while True:
        now = time.localtime()
        # 다음 새벽 5시까지 남은 초 계산
        seconds_until_5am = ((5 - now.tm_hour - 1) % 24) * 3600 + (60 - now.tm_min) * 60
        if seconds_until_5am == 0:
            seconds_until_5am = 86400
        print(f"다음 갱신까지 {seconds_until_5am // 3600}시간 {(seconds_until_5am % 3600) // 60}분")
        time.sleep(seconds_until_5am)

        print("=== 일일 데이터 갱신 시작 ===")
        try:
            preload_all()
            print("=== 일일 데이터 갱신 완료 ===")
        except Exception as e:
            print(f"=== 갱신 실패: {e} ===")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/departments")
def departments():
    return jsonify(_dept_list)


@app.route("/api/schedules")
def schedules():
    dept_nm = request.args.get("dept", "")
    if not dept_nm:
        return jsonify({"error": "dept 파라미터 필요"}), 400

    cached = _schedule_cache.get(dept_nm)
    if cached:
        return jsonify(cached)

    return jsonify({"doctors": [], "rangeStart": "", "rangeEnd": ""})


# 로딩 상태 플래그
_loading = True


def background_init():
    """백그라운드에서 프리로드 후 일일 갱신 루프"""
    global _loading
    preload_all()
    _loading = False
    daily_refresh()


@app.route("/api/status")
def status():
    return jsonify({"loading": _loading, "depts": len(_dept_list)})

def start_background():
    """백그라운드 스레드 시작 (워커 프로세스에서 호출)"""
    t = threading.Thread(target=background_init, daemon=True)
    t.start()


if __name__ == "__main__":
    import os
    start_background()
    port = int(os.environ.get("PORT", 5001))
    print(f"\n서버 시작: http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
