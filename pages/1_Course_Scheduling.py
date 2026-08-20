import streamlit as st
import pandas as pd


st.set_page_config(
    page_title="Course Scheduling",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Course Scheduling")

st.write(
    "Plan courses for the new semester and reduce scheduling conflicts."
)


# --------------------------------------------------
# Course Input
# --------------------------------------------------

st.subheader("1. Courses Offered")

default_courses = pd.DataFrame(
    {
        "Course": [
            "Physics 1",
            "Physics 2",
            "Mathematics 1",
            "Mathematics 2",
            "Programming",
            "Data Structures"
        ],
        "Semester": [
            1,
            2,
            1,
            2,
            1,
            3
        ],
        "Cohort": [
            "1405",
            "1404",
            "1405",
            "1404",
            "1405",
            "1403"
        ]
    }
)

course_df = st.data_editor(
    default_courses,
    num_rows="dynamic",
    use_container_width=True
)


# --------------------------------------------------
# Weekly Settings
# --------------------------------------------------

st.subheader("2. Weekly Schedule Settings")

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
# Generate
# --------------------------------------------------

st.subheader("3. Generate Course Schedule")

if st.button(
    "Generate Course Schedule",
    type="primary"
):

    if course_df.empty:

        st.error(
            "Please enter at least one course."
        )

        st.stop()

    if not days or not times:

        st.error(
            "Please select at least one day and one class time."
        )

        st.stop()

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

    schedule_rows = []

    used_slots = {}

    for _, row in course_df.iterrows():

        course = row["Course"]
        semester = row["Semester"]
        cohort = row["Cohort"]

        conflict_group = (
            str(cohort),
            str(semester)
        )

        assigned = False

        for day in days:

            for class_time in times:

                slot = (
                    day,
                    class_time
                )

                if slot not in used_slots:

                    used_slots[slot] = []

                existing_groups = [
                    item["group"]
                    for item in used_slots[slot]
                ]

                if conflict_group not in existing_groups:

                    schedule_rows.append(
                        {
                            "Course": course,
                            "Semester": semester,
                            "Cohort": cohort,
                            "Day": day,
                            "Time": class_time
                        }
                    )

                    used_slots[slot].append(
                        {
                            "course": course,
                            "group": conflict_group
                        }
                    )

                    assigned = True

                    break

            if assigned:
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
    # Results
    # --------------------------------------------------

    schedule_df = pd.DataFrame(
        schedule_rows
    )

    st.subheader(
        "4. Course Schedule"
    )

    st.dataframe(
        schedule_df,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------
    # Conflict Check
    # --------------------------------------------------

    unscheduled = schedule_df[
        schedule_df["Day"]
        == "No Slot"
    ]

    if unscheduled.empty:

        st.success(
            "All courses were scheduled successfully."
        )

    else:

        st.warning(
            f"{len(unscheduled)} course(s) could not be scheduled."
        )


    # --------------------------------------------------
    # Weekly View
    # --------------------------------------------------

    st.subheader(
        "5. Weekly View"
    )

    for day in days:

        st.markdown(
            f"### {day}"
        )

        day_data = schedule_df[
            schedule_df["Day"]
            == day
        ]

        for class_time in times:

            exams = day_data[
                day_data["Time"]
                == class_time
            ]

            if not exams.empty:

                st.markdown(
                    f"**{class_time}**"
                )

                for _, course_row in exams.iterrows():

                    st.info(
                        f"**{course_row['Course']}**\n\n"
                        f"Semester: {course_row['Semester']}\n\n"
                        f"Cohort: {course_row['Cohort']}"
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
    )ر
