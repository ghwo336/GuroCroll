import requests
import calendar

BASE_URL = "https://guro.kumc.or.kr"
BASE_LIST_URL = f"{BASE_URL}/api/doctorApi.do"
BASE_SCHEDULE_URL = f"{BASE_URL}/api/getDoctorSchedule.do"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/kr/doctor-department/doctor.do",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}


def get_all_doctors():
    params = {
        "startIndex": 1,
        "pageRow": 400,
        "langType": "kr",
        "instNo": 2,
        "deptClsf": "A"
    }

    res = requests.get(BASE_LIST_URL, params=params, headers=COMMON_HEADERS)
    res.raise_for_status()
    return res.json()["doctorList"]


def get_schedule(emp_id, emr_dept_cd, year_month):
    year = int(year_month[:4])
    month = int(year_month[4:6])
    last_day = calendar.monthrange(year, month)[1]

    params = {
        "hpCd": "GR",
        "empId": emp_id,
        "inqrStrtYmd": f"{year_month}01",
        "inqrFnshYmd": f"{year_month}{last_day:02d}",
        "mcdpCd": emr_dept_cd
    }

    res = requests.get(BASE_SCHEDULE_URL, params=params, headers=COMMON_HEADERS)
    res.raise_for_status()
    return res.json()


def get_schedule_range(emp_id, emr_dept_cd, start_ymd, end_ymd):
    """날짜 범위로 스케줄 조회 (YYYYMMDD ~ YYYYMMDD)"""
    params = {
        "hpCd": "GR",
        "empId": emp_id,
        "inqrStrtYmd": start_ymd,
        "inqrFnshYmd": end_ymd,
        "mcdpCd": emr_dept_cd
    }

    res = requests.get(BASE_SCHEDULE_URL, params=params, headers=COMMON_HEADERS)
    res.raise_for_status()
    return res.json()


def get_department_schedules(dept_name, year_month):
    doctors = get_all_doctors()

    dept_doctors = [
        d for d in doctors
        if d["doctorDept"]["deptNm"] == dept_name
    ]

    if not dept_doctors:
        print("해당 과를 찾을 수 없음")
        return

    print(f"\n===== {dept_name} ({len(dept_doctors)}명) =====")

    for d in dept_doctors:
        name = d["drName"]
        emp_id = d["empId"]
        emr_dept_cd = d["doctorDept"]["emrDeptCd"]

        schedule = get_schedule(emp_id, emr_dept_cd, year_month)

        print(f"\n▶ {name}")

        if not schedule:
            print("  진료 없음")
            continue

        for s in schedule:
            date = s["mdcrYmd"]
            am = s.get("amSttsDvsnCd") == "1"
            pm = s.get("pmSttsDvsnCd") == "1"

            status = []
            if am:
                status.append("오전")
            if pm:
                status.append("오후")

            if status:
                print(f"  {date} → {', '.join(status)}")

