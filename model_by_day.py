from sys import argv, exit
from datetime import date, timedelta
from time import sleep


def calculate_model(tdate: date):
    sleep(2)
    ...
    print(f"Done calculations for {tdate}")
    return 0


def run_in_sequence(from_date, to_date, func):
    tdate = from_date
    while tdate < to_date:
        func(tdate)
        tdate += timedelta(days=1)


HELP_STRING = """Small util to run calculation on a date period

Usage: 
    model_by_day.py run YYYY-MM-DD
    model_by_day.py period --start YYYY-MM-DD
    model_by_day.py period --start YYYY-MM-DD --end YYYY-MM-DD
"""

if __name__ == "__main__":
    try:
        if len(argv) < 2 or argv[1] == "--help":
            print(HELP_STRING)
            exit(0)
        if argv[1] == "run":
            tdate = date.fromisoformat(argv[2])
            calculate_model(tdate)
            exit(0)
        if argv[1] == "period":
            key, value = None, None
            kwarg = dict()
            for i in range(2, len(argv)):
                if argv[i].startswith("--"):
                    key = argv[i]
                else:
                    value = argv[i]
                if key is not None and value is not None:
                    kwarg[key] = value
                    key, value = None, None

            if "--start" not in kwarg:
                raise ValueError("run command needs --start value")
            start_date = date.fromisoformat(kwarg["--start"])

            if "--end" not in kwarg:
                end_date = max(date.today(), date.fromisoformat(kwarg["--start"]))
            else:
                end_date = date.fromisoformat(kwarg["--end"])
            run_in_sequence(start_date, end_date, calculate_model)
            exit(0)
    except Exception as e:
        print("Raised an error while running cli:")
        print(e)

    exit(1)

