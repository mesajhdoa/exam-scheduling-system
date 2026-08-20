import streamlit as st
import pandas as pd


# --------------------------------------------------
# Page Settings
# --------------------------------------------------

st.set_page_config(
    page_title="Course Scheduling",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Course Scheduling")

st.write(
    "Plan courses for a new semester and reduce "
    "course-selection timetable conflicts."
)


# --------------------------------------------------
# 1. Courses Offered
# --------------------------------------------------

st.subheader("1. Courses Offered")

default_courses = pd.DataFrame(
    {
        "Course": [
            "Physics 1",
            "Mathematics 1",
            "Programming",
            "Physics 2",
            "Mathematics 2",
            "Data Structures"
        ],
        "Semester": [
            1,
            1,
            1,
            2,
            2,
            3
        ],
        "Cohort": [
            "1405",
            "1405",
            "1405",
            "1404",
            "1404",
            "1403"
        ],
        "Related Group": [
            "Physics",
            "Mathematics",
            "Programming",
            "Physics",
            "Mathematics",
            "Programming"
        ]
    }
)

course_df = st.data_editor(
    default_courses,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="course_editor"
)


# --------------------------------------------------
# 2. Courses That Must Not Overlap
# --------------------------------------------------

st.subheader("2. Courses That Must Not Overlap")

st.write(
    "Enter pairs of courses that should never be "
    "scheduled at the same day and time."
)

default_conflicts = pd.DataFrame(
    {
        "Course A": [
            "Physics 1",
            "Mathematics 1",
            "Programming"
        ],
        "Course B": [
            "Physics 2",
            "Mathematics 2",
            "Data Structures"
        ]
    }
)

conflict_df = st.data_editor(
    default_conflicts,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="conflict_editor"
)


# --------------------------------------------------
# 3. Available Days and Times
# --------------------------------------------------

st.subheader("3. Available Days and Times")

days = st.multiselect(
    "Teaching Days",
    [
        "Saturday",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday"
    ],
    default=[
        "Saturday",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday"
    ]
)

times = st.multiselect(
    "Class Times",
    [
        "08:00",
        "10:00",
        "13:00",
        "15:00"
    ],
    default=[
        "08:00",
        "10:00",
        "13:00"
    ]
)


# --------------------------------------------------
# 4. Generate Schedule
# --------------------------------------------------

st.subheader("4. Generate Course Schedule")

if st.button(
    "Generate Course Schedule",
    type="primary"
):

    if not days or not times:

        st.error(
            "Please select at least one teaching day "
            "and one class time."
        )

        st.stop()


    # --------------------------------------------------
    # Clean Course Data
    # --------------------------------------------------

    course_df = course_df.dropna(
        subset=[
            "Course",
            "Semester",
            "Cohort"
        ]
    ).copy()

    course_df["Course"] = (
        course_df["Course"]
        .astype(str)
        .str.strip()
    )

    course_df["Semester"] = (
        course_df["Semester"]
        .astype(str)
        .str.strip()
    )

    course_df["Cohort"] = (
        course_df["Cohort"]
        .astype(str)
        .str.strip()
    )

    course_df = course_df[
        course_df["Course"] != ""
    ]

    if course_df.empty:

        st.error(
            "Please enter at least one course."
        )

        st.stop()


    # --------------------------------------------------
    # Clean Explicit Conflict Pairs
    # --------------------------------------------------

    conflict_pairs = set()

    if not conflict_df.empty:

        conflict_df = conflict_df.dropna(
            subset=[
                "Course A",
                "Course B"
            ]
        ).copy()

        for _, row in conflict_df.iterrows():

            course_a = str(
                row["Course A"]
            ).strip()

            course_b = str(
                row["Course B"]
            ).strip()

            if (
                course_a
                and course_b
                and course_a != course_b
            ):

                conflict_pairs.add(
                    frozenset(
                        [
                            course_a,
                            course_b
                        ]
                    )
                )


    # --------------------------------------------------
    # Create Available Slots
    # --------------------------------------------------

    all_slots = []

    for day_index, day in enumerate(days):

        for time_index, class_time in enumerate(times):

            all_slots.append(
                {
                    "day": day,
                    "time": class_time,
                    "day_index": day_index,
                    "time_index": time_index
                }
            )


    # --------------------------------------------------
    # Scheduling Data
    # --------------------------------------------------

    # --------------------------------------------------
    # Scheduling Data
    # --------------------------------------------------

    slot_courses = {
        (slot["day"], slot["time"]): []
        for slot in all_slots
    }

    slot_load = {
        (slot["day"], slot["time"]): 0
        for slot in all_slots
    }

    day_load = {
        day: 0
        for day in days
    }

    schedule_rows = []


    # --------------------------------------------------
    # Conflict Function
    # --------------------------------------------------

    def courses_conflict(
        course_a,
        semester_a,
        cohort_a,
        related_group_a,
        course_b,
        semester_b,
        cohort_b,
        related_group_b
    ):

        if (
            cohort_a == cohort_b
            and semester_a == semester_b
        ):
            return True

        if (
            related_group_a
            and related_group_b
            and related_group_a == related_group_b
        ):
            return True

        pair = frozenset(
            [
                course_a,
                course_b
            ]
        )

        if pair in conflict_pairs:
            return True

        return False


    # --------------------------------------------------
    # Assign Courses
    # --------------------------------------------------

    for _, row in course_df.iterrows():

        course = row["Course"]
        semester = row["Semester"]
        cohort = row["Cohort"]

        related_group = str(
            row["Related Group"]
        ).strip()

        ordered_slots = sorted(
            all_slots,
            key=lambda slot: (
                day_load[
                    slot["day"]
                ],
                slot_load[
                    (
                        slot["day"],
                        slot["time"]
                    )
                ],
                slot["day_index"],
                slot["time_index"]
            )
        )

        assigned = False

        for slot in ordered_slots:

            day = slot["day"]
            class_time = slot["time"]

            slot_key = (
                day,
                class_time
            )

            can_use_slot = True

            for existing in slot_courses[
                slot_key
            ]:

                if courses_conflict(
                    course,
                    semester,
                    cohort,
                    related_group,
                    existing["Course"],
                    existing["Semester"],
                    existing["Cohort"],
                    existing["Related Group"]
                ):
                    can_use_slot = False
                    break

            if can_use_slot:

                schedule_rows.append(
                    {
                        "Course": course,
                        "Semester": semester,
                        "Cohort": cohort,
                        "Day": day,
                        "Time": class_time
                    }
                )

                slot_courses[
                    slot_key
                ].append(
                    {
                        "Course": course,
                        "Semester": semester,
                        "Cohort": cohort,
                        "Related Group": related_group
                    }
                )

                slot_load[
                    slot_key
                ] += 1

                day_load[
                    day
                ] += 1

                assigned = True
                break

        if not assigned:

            schedule_rows.append(
                {
                    "Course": course,
                    "Semester": semester,
                    "Cohort": cohort,
                    "Day": "No Slot",
                    "Time": "-"
                }
            )
    
    # --------------------------------------------------
    # 5. Results
    # --------------------------------------------------

    schedule_df = pd.DataFrame(
        schedule_rows
    )

    st.subheader(
        "5. Course Schedule"
    )

    st.dataframe(
        schedule_df,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    unscheduled = schedule_df[
        schedule_df["Day"]
        == "No Slot"
    ]

    if unscheduled.empty:

        st.success(
            "All courses were scheduled successfully "
            "without detected conflicts."
        )

    else:

        st.warning(
            f"{len(unscheduled)} course(s) "
            "could not be scheduled."
        )


    # --------------------------------------------------
    # 6. Weekly View
    # --------------------------------------------------

    st.subheader(
        "6. Weekly View"
    )

    for day in days:

        st.markdown(
            f"### {day}"
        )

        day_df = schedule_df[
            schedule_df["Day"]
            == day
        ]

        if day_df.empty:

            st.caption(
                "No classes"
            )

        else:

            for class_time in times:

                time_df = day_df[
                    day_df["Time"]
                    == class_time
                ]

                if not time_df.empty:

                    st.markdown(
                        f"**🕒 {class_time}**"
                    )

                    for _, item in (
                        time_df.iterrows()
                    ):

                        st.info(
                            f"**{item['Course']}**\n\n"
                            f"Semester: "
                            f"{item['Semester']}\n\n"
                            f"Cohort: "
                            f"{item['Cohort']}"
                        )


    # --------------------------------------------------
    # Download
    # --------------------------------------------------

    csv_output = (
        schedule_df
        .to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )

    st.download_button(
        "Download Course Schedule",
        csv_output,
        "course_schedule.csv",
        "text/csv"
    )
