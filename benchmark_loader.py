from pathlib import Path
import re


def _read_text(source):
    """
    Read benchmark data from either:
    - a file path
    - a Streamlit uploaded file
    """

    if hasattr(source, "read"):

        try:
            source.seek(0)
        except Exception:
            pass

        raw = source.read()

        if isinstance(raw, bytes):
            return raw.decode("utf-8")

        return str(raw)

    return Path(source).read_text(
        encoding="utf-8"
    )


def load_itc2007_exam(source):
    """
    Parse an ITC2007 Examination Timetabling file.

    Returns:
        metadata
        students
        exams
        periods
        rooms
        period_hard_constraints
        room_hard_constraints
        institutional_weightings
    """

    text = _read_text(source)

    sections = {}
    expected_counts = {}

    current_section = None

    header_pattern = re.compile(
        r"^\[([A-Za-z]+)(?::(\d+))?\]$"
    )

    # --------------------------------------------------
    # Read Sections
    # --------------------------------------------------

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("//"):
            continue

        match = header_pattern.match(line)

        if match:

            current_section = match.group(1)

            sections[current_section] = []

            if match.group(2) is not None:

                expected_counts[
                    current_section
                ] = int(
                    match.group(2)
                )

            continue

        if current_section is None:

            raise ValueError(
                "Invalid benchmark file."
            )

        sections[
            current_section
        ].append(line)


    # --------------------------------------------------
    # Check Required Sections
    # --------------------------------------------------

    required_sections = {
        "Exams",
        "Periods",
        "Rooms",
        "PeriodHardConstraints",
        "RoomHardConstraints",
        "InstitutionalWeightings"
    }

    missing = (
        required_sections
        - set(sections.keys())
    )

    if missing:

        raise ValueError(
            "Missing section(s): "
            + ", ".join(
                sorted(missing)
            )
        )


    # --------------------------------------------------
    # Validate Counts
    # --------------------------------------------------

    for section, expected in (
        expected_counts.items()
    ):

        actual = len(
            sections.get(
                section,
                []
            )
        )

        if actual != expected:

            raise ValueError(
                f"{section}: "
                f"expected {expected}, "
                f"found {actual}"
            )


    # --------------------------------------------------
    # Exams + Students
    # --------------------------------------------------

    exams = []

    students = {}

    for exam_id, line in enumerate(
        sections["Exams"]
    ):

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        duration = int(
            parts[0]
        )

        student_ids = [
            item
            for item in parts[1:]
            if item
        ]

        exam_name = (
            f"Exam {exam_id}"
        )

        exams.append(
            {
                "exam_id": exam_id,
                "exam_name": exam_name,
                "duration": duration,
                "student_count": len(
                    student_ids
                ),
                "student_ids": student_ids
            }
        )

        for student_id in student_ids:

            students.setdefault(
                student_id,
                []
            ).append(
                exam_name
            )


    # --------------------------------------------------
    # Periods
    # --------------------------------------------------

    periods = []

    for period_id, line in enumerate(
        sections["Periods"]
    ):

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        periods.append(
            {
                "period_id": period_id,
                "date": parts[0],
                "time": parts[1],
                "duration": int(
                    parts[2]
                ),
                "penalty": int(
                    parts[3]
                )
            }
        )


    # --------------------------------------------------
    # Rooms
    # --------------------------------------------------

    rooms = []

    for room_id, line in enumerate(
        sections["Rooms"]
    ):

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        rooms.append(
            {
                "room_id": room_id,
                "capacity": int(
                    parts[0]
                ),
                "penalty": int(
                    parts[1]
                )
            }
        )


    # --------------------------------------------------
    # Period Hard Constraints
    # --------------------------------------------------

    period_hard_constraints = []

    for line in sections[
        "PeriodHardConstraints"
    ]:

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        period_hard_constraints.append(
            {
                "exam_a": int(
                    parts[0]
                ),
                "constraint": parts[1],
                "exam_b": int(
                    parts[2]
                )
            }
        )


    # --------------------------------------------------
    # Room Hard Constraints
    # --------------------------------------------------

    room_hard_constraints = []

    for line in sections[
        "RoomHardConstraints"
    ]:

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        room_hard_constraints.append(
            {
                "exam_id": int(
                    parts[0]
                ),
                "constraint": parts[1]
            }
        )


    # --------------------------------------------------
    # Institutional Weightings
    # --------------------------------------------------

    institutional_weightings = {}

    for line in sections[
        "InstitutionalWeightings"
    ]:

        parts = [
            item.strip()
            for item in line.split(",")
        ]

        key = parts[0]

        if key == "FRONTLOAD":

            institutional_weightings[
                key
            ] = {
                "largest_exams": int(
                    parts[1]
                ),
                "last_periods": int(
                    parts[2]
                ),
                "penalty": int(
                    parts[3]
                )
            }

        else:

            institutional_weightings[
                key
            ] = int(
                parts[1]
            )


    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    enrollment_count = sum(
        exam["student_count"]
        for exam in exams
    )

    metadata = {
        "exam_count": len(
            exams
        ),
        "student_count": len(
            students
        ),
        "enrollment_count": (
            enrollment_count
        ),
        "period_count": len(
            periods
        ),
        "room_count": len(
            rooms
        ),
        "period_hard_constraints": len(
            period_hard_constraints
        ),
        "room_hard_constraints": len(
            room_hard_constraints
        )
    }


    return {
        "metadata": metadata,
        "students": students,
        "exams": exams,
        "periods": periods,
        "rooms": rooms,
        "period_hard_constraints":
            period_hard_constraints,
        "room_hard_constraints":
            room_hard_constraints,
        "institutional_weightings":
            institutional_weightings
    }
