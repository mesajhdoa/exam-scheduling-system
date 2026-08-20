import streamlit as st
import pandas as pd


st.set_page_config(
    page_title="Course Scheduling",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Course Scheduling")

st.write(
    "Plan courses for a new semester and avoid timetable conflicts."
)


# --------------------------------------------------
# 1. Course Data
# --------------------------------------------------

st.subheader("1. Courses Offered")

default_data = pd.DataFrame(
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
        ]
    }
)

course_df = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 2. Available Days and Times
# --------------------------------------------------

st.subheader("2. Available Days and Times")

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
# 3. Generate Schedule
# --------------------------------------------------

st.subheader("3. Generate Course Schedule")

if st.button(
    "Generate Course Schedule",
    type="primary"
):

    if not days or not times:
        st.error(
            "Please select at least one day and one class time."
        )
        st.stop()

    course_df = course_df.dropna(
        subset=["Course", "Semester", "Cohort"]
    ).copy()

    course_df["Course"] = (
        course_df["Course"]
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


    # ----------------------------------------------
    # Scheduling
    # ----------------------------------------------

    schedule_rows = []

    # Each slot stores the groups already using it.
    slot_groups = {}

    for _, row in course_df.iterrows():

        course = row["Course"]
        semester = str(row["Semester"])
        cohort = str(row["Cohort"])

        group = (
            cohort,
            semester
        )

        assigned = False

        for day in days:

            for class_time in times:

                slot = (
                    day,
                    class_time
                )

                if slot not in slot_groups:
                    slot_groups[slot] = set()

                # Courses belonging to the same cohort
                # and semester cannot be at the same time.
                if group not in slot_groups[slot]:

                    schedule_rows.append(
                        {
                            "Course": course,
                            "Semester": semester,
                            "Cohort": cohort,
                            "Day": day,
                            "Time": class_time
                        }
                    )

                    slot_groups[slot].add(
                        group
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
    # 4. Results
    # --------------------------------------------------

    schedule_df = pd.DataFrame(
        schedule_rows
    )

    st.subheader("4. Course Schedule")

    st.dataframe(
        schedule_df,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------
    # 5. Validation
    # --------------------------------------------------

    unscheduled = schedule_df[
        schedule_df["Day"] == "No Slot"
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
    # 6. Weekly View
    # --------------------------------------------------

    st.subheader("5. Weekly View")

    for day in days:

        st.markdown(
            f"### {day}"
        )

        day_df = schedule_df[
            schedule_df["Day"] == day
        ]

        if day_df.empty:

            st.caption(
                "No classes"
            )

        else:

            for class_time in times:

                time_df = day_df[
                    day_df["Time"] == class_time
                ]

                if not time_df.empty:

                    st.markdown(
                        f"**{class_time}**"
                    )

                    for _, item in time_df.iterrows():

                        st.info(
                            f"**{item['Course']}**\n\n"
                            f"Semester: {item['Semester']}\n\n"
                            f"Cohort: {item['Cohort']}"
                        )


    # --------------------------------------------------
    # Download
    # --------------------------------------------------

    csv_output = schedule_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download Course Schedule",
        csv_output,
        "course_schedule.csv",
        "text/csv"
    )
