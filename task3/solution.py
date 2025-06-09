from enum import IntEnum


class Action(IntEnum):
    ENTER = 1
    EXIT = -1


def appearance(intervals: dict[str, list[int]]) -> int:
    lesson_start, lesson_end = intervals['lesson']

    events = []
    for i in range(0, len(intervals['pupil']), 2):
        events.append((intervals['pupil'][i], Action.ENTER, 'pupil'))
        events.append((intervals['pupil'][i+1], Action.EXIT, 'pupil'))
    for i in range(0, len(intervals['tutor']), 2):
        events.append((intervals['tutor'][i], Action.ENTER, 'tutor'))
        events.append((intervals['tutor'][i+1], Action.EXIT, 'tutor'))

    events.sort()

    pupil_active = 0
    tutor_active = 0
    total_time = 0
    prev_time = None

    for time, action, role in events:
        if pupil_active and tutor_active and prev_time is not None:
            start = max(prev_time, lesson_start)
            end = min(time, lesson_end)
            if start < end:
                total_time += end - start

        if role == 'pupil':
            pupil_active += action
        else:
            tutor_active += action

        prev_time = time

    return total_time
