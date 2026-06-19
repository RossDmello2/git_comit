import hashlib
import json
import os
import random
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path


TODAY = date(2026, 6, 19)
START_DATE = TODAY - timedelta(days=364)
INTERNSHIP_START = date(2026, 1, 1)
TARGET_MIN = 863
TARGET_MAX = 866
TARGET_TOTAL = 865
PRE_TARGET_MIN = 130
PRE_TARGET_MAX = 170
MAX_ACTIVE_STREAK = 14
ACTIVE_DAY_MAX = 220
SEED = "transparent-internship-pattern-v1"
AUTHOR_NAME = "RossDmello2"
AUTHOR_EMAIL = "184658540+RossDmello2@users.noreply.github.com"

WORK_FILES = [
    Path("internship-log/daily-notes.md"),
    Path("internship-log/debug-notes.md"),
    Path("internship-log/learning-journal.md"),
    Path("internship-log/review-notes.md"),
    Path("experiment/graph-observations.md"),
    Path("experiment/synthetic-data.txt"),
]

MESSAGES = [
    "Synthetic graph experiment note",
    "Transparent internship-pattern sample",
    "Record synthetic contribution observation",
    "Update educational graph data",
    "Add transparent activity sample",
    "Document synthetic schedule point",
]


def rng_for(label):
    digest = hashlib.sha256(f"{SEED}:{label}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def run(command, env=None):
    subprocess.run(command, shell=False, check=True, env=env)


def days_between(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def season(day):
    return "internship" if day >= INTERNSHIP_START else "pre_internship"


def zero_windows():
    windows = [
        (date(2025, 7, 8), date(2025, 7, 24), "summer break"),
        (date(2025, 8, 16), date(2025, 8, 30), "college gap"),
        (date(2025, 10, 20), date(2025, 10, 26), "semester pause"),
        (date(2025, 12, 18), date(2025, 12, 31), "exam and holiday break"),
        (date(2026, 1, 12), date(2026, 1, 18), "internship onboarding gap"),
        (date(2026, 3, 6), date(2026, 3, 10), "family event"),
        (date(2026, 5, 14), date(2026, 5, 19), "exam administration gap"),
    ]
    return windows


def in_zero_window(day):
    for start, end, _reason in zero_windows():
        if start <= day <= end:
            return True
    return False


def is_dead_week(day):
    week_index = (day - START_DATE).days // 7
    rng = rng_for(f"dead-week:{week_index}")
    cadence = rng.choice([3, 4, 5])
    return week_index > 0 and week_index % cadence == 0 and rng.random() < 0.40


def active_probability(day):
    if in_zero_window(day):
        return 0.0

    weekday = day.weekday()
    dead = is_dead_week(day)
    if season(day) == "pre_internship":
        probabilities = [0.18, 0.16, 0.18, 0.16, 0.10, 0.04, 0.02]
    else:
        probabilities = [0.88, 0.86, 0.86, 0.82, 0.46, 0.22, 0.14]

    probability = probabilities[weekday]
    if dead:
        probability *= 0.35

    # Some Friday-off / weekend-catch-up behavior.
    if weekday == 5:
        friday = day - timedelta(days=1)
        friday_rng = rng_for(f"friday-off:{friday.isoformat()}")
        if friday_rng.random() < 0.32:
            probability += 0.26

    return min(0.95, probability)


def initial_active_days():
    active = set()
    for day in days_between(START_DATE, TODAY):
        rng = rng_for(f"active:{day.isoformat()}")
        if rng.random() < active_probability(day):
            active.add(day)
    return active


def enforce_streak_limits(active):
    ordered = list(days_between(START_DATE, TODAY))
    streak = 0
    for day in ordered:
        if day in active:
            streak += 1
            if streak > MAX_ACTIVE_STREAK:
                active.remove(day)
                streak = 0
        else:
            streak = 0
    return active


def max_active_streak(active):
    max_streak = 0
    streak = 0
    for day in days_between(START_DATE, TODAY):
        if day in active:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def can_activate(day, counts):
    if in_zero_window(day):
        return False
    active = set(counts)
    active.add(day)
    return max_active_streak(active) <= MAX_ACTIVE_STREAK


def intensity_for_day(day):
    rng = rng_for(f"count:{day.isoformat()}")
    if season(day) == "pre_internship":
        return rng.choices([1, 2, 3], weights=[65, 30, 5], k=1)[0]

    if day.weekday() >= 5:
        return rng.choices([1, 2, 3, 4, 5], weights=[40, 28, 18, 10, 4], k=1)[0]

    bucket = rng.choices(
        ["light", "normal", "busy", "crunch"],
        weights=[25, 35, 30, 10],
        k=1,
    )[0]
    if bucket == "light":
        return rng.randint(1, 2)
    if bucket == "normal":
        return rng.randint(3, 4)
    if bucket == "busy":
        return rng.randint(5, 7)
    return rng.randint(8, 12)


def build_counts():
    active = enforce_streak_limits(initial_active_days())
    counts = {day: intensity_for_day(day) for day in active}

    def total():
        return sum(counts.values())

    internship_days = [
        day for day in days_between(INTERNSHIP_START, TODAY) if not in_zero_window(day)
    ]
    pre_days = [
        day
        for day in days_between(START_DATE, INTERNSHIP_START - timedelta(days=1))
        if not in_zero_window(day)
    ]

    def pre_total():
        return sum(count for day, count in counts.items() if day < INTERNSHIP_START)

    # Keep pre-January sparse but visible: enough scattered activity to avoid
    # looking like the account was empty before internship.
    for day in sorted(pre_days, key=lambda item: (counts.get(item, 0), item)):
        if pre_total() >= PRE_TARGET_MIN:
            break
        if counts.get(day, 0) == 0 and not can_activate(day, counts):
            continue
        counts[day] = min(3, counts.get(day, 0) + 1)

    while total() < TARGET_MIN:
        if pre_total() < PRE_TARGET_MAX:
            pool = pre_days + internship_days
        else:
            pool = internship_days
        candidates = sorted(
            [
                day
                for day in pool
                if counts.get(day, 0) < 12
                and (counts.get(day, 0) > 0 or can_activate(day, counts))
            ],
            key=lambda item: (
                season(item) != "internship",
                counts.get(item, 0),
                item.weekday() >= 5,
                item,
            ),
        )
        day = candidates[0]
        counts[day] = counts.get(day, 0) + 1

    while total() > TARGET_MAX:
        candidates = sorted(
            [day for day, count in counts.items() if count > 1],
            key=lambda item: (season(item) == "pre_internship", counts[item]),
            reverse=True,
        )
        day = candidates[0]
        counts[day] -= 1
        if counts[day] == 0:
            del counts[day]

    # Keep pre-internship within the agreed 15-25% band.
    current_pre_total = pre_total()
    for day in sorted(pre_days, key=lambda item: counts.get(item, 0), reverse=True):
        if current_pre_total <= PRE_TARGET_MAX:
            break
        if counts.get(day, 0) > 0:
            counts[day] -= 1
            current_pre_total -= 1
            if counts[day] == 0:
                del counts[day]
            for target in internship_days:
                if counts.get(target, 0) < 12 and (
                    counts.get(target, 0) > 0 or can_activate(target, counts)
                ):
                    counts[target] = counts.get(target, 0) + 1
                    break

    if max_active_streak(set(counts)) > MAX_ACTIVE_STREAK:
        raise RuntimeError("generated active streak exceeds cap")

    while len(counts) > ACTIVE_DAY_MAX:
        removable = sorted(
            counts,
            key=lambda item: (
                counts[item],
                item.weekday() < 5,
                season(item) == "internship",
                item,
            ),
        )
        removed = False
        for day in removable:
            amount = counts[day]
            same_period = pre_days if day < INTERNSHIP_START else internship_days
            cap = 3 if day < INTERNSHIP_START else 12
            targets = [
                target
                for target in same_period
                if target != day and counts.get(target, 0) > 0 and counts[target] < cap
            ]
            if not targets:
                continue
            del counts[day]
            for _ in range(amount):
                targets = [target for target in targets if counts[target] < cap]
                if not targets:
                    counts[day] = counts.get(day, 0) + 1
                    continue
                target = sorted(targets, key=lambda item: (counts[item], item))[0]
                counts[target] += 1
            removed = True
            break
        if not removed:
            break

    return counts


def commit_time(day, index, count):
    rng = rng_for(f"time:{day.isoformat()}:{index}")
    progress = index / max(count, 1)
    if progress < 0.58:
        hour = rng.randint(9, 12)
    elif progress < 0.90:
        hour = rng.randint(13, 17)
    else:
        hour = rng.randint(18, 21)
    return datetime(
        day.year,
        day.month,
        day.day,
        hour,
        rng.randint(0, 59),
        rng.randint(0, 59),
    )


def write_change(day, index, count, commit_dt):
    rng = rng_for(f"file:{day.isoformat()}:{index}")
    path = rng.choice(WORK_FILES)
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")
    if path.suffix == ".md" and not path.exists():
        path.write_text(f"# {path.stem.replace('-', ' ').title()}\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n{timestamp} | synthetic transparent graph sample | "
            f"{season(day)} | commit {index + 1}/{count}\n"
        )
    return path


def validate(counts):
    total = sum(counts.values())
    active_days = len(counts)
    pre_total = sum(count for day, count in counts.items() if day < INTERNSHIP_START)
    internship_total = total - pre_total
    weekend_days = sum(1 for day in counts if day.weekday() >= 5)
    max_streak = max_active_streak(set(counts))
    levels = Counter()
    for count in counts.values():
        if count <= 2:
            levels["1-2"] += 1
        elif count <= 4:
            levels["3-4"] += 1
        elif count <= 7:
            levels["5-7"] += 1
        else:
            levels["8-12"] += 1

    summary = {
        "start_date": START_DATE.isoformat(),
        "end_date": TODAY.isoformat(),
        "total_commits": total,
        "active_days": active_days,
        "zero_days": 365 - active_days,
        "pre_january_commits": pre_total,
        "internship_commits": internship_total,
        "internship_share": round(internship_total / total, 3),
        "weekend_active_days": weekend_days,
        "max_streak": max_streak,
        "levels": dict(levels),
    }
    Path("experiment").mkdir(exist_ok=True)
    Path("experiment/distribution-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    if not TARGET_MIN <= total <= TARGET_MAX:
        raise RuntimeError(f"total {total} outside target")
    if not 0.75 <= internship_total / total <= 0.85:
        raise RuntimeError("internship share outside target")
    if max_streak > MAX_ACTIVE_STREAK:
        raise RuntimeError("max streak too high")


def create_commit(commit_dt, message):
    date_str = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str
    env["GIT_AUTHOR_NAME"] = AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = AUTHOR_EMAIL
    run(["git", "add", "."], env=env)
    run(["git", "commit", "-m", message], env=env)


def main():
    counts = build_counts()
    validate(counts)

    for day in sorted(counts):
        count = counts[day]
        for index in range(count):
            commit_dt = commit_time(day, index, count)
            write_change(day, index, count, commit_dt)
            rng = rng_for(f"message:{day.isoformat()}:{index}")
            create_commit(commit_dt, rng.choice(MESSAGES))


if __name__ == "__main__":
    main()
