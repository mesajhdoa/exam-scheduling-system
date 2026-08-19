import streamlit as st
import pandas as pd
from datetime import timedelta
import jdatetime
import random

from scheduler_core import (
    build_conflict_graph,
    greedy_coloring,
    welsh_powell,
    dsatur,
    local_search,
    simulated_annealing,
    validate_schedule,
    consecutive_exam_penalty,
    total_cost
)


# --------------------------------------------------
# Page Settings
# --------------------------------------------------

st.set_page_config(
    page_title="Exam Scheduling System",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Exam Scheduling System")

st.write(
    "Enter student-course data manually, upload a CSV file, "
    "or generate a demo dataset and create an optimized exam schedule."
)


# --------------------------------------------------
# Sidebar Settings
# --------------------------------------------------

st.sidebar.header("Optimization Settings")

algorithm = st.sidebar.selectbox(
    "Scheduling Method",
    [
        "Greedy",
        "Welsh-Powell",
        "DSATUR",
        "Local Search",
        "Simulated Annealing"
    ]
)

slot_weight = st.sidebar.slider(
    "Slot Weight",
    min_value=1,
    max_value=30,
    value=10
)


# --------------------------------------------------
# Exam Calendar
# --------------------------------------------------

st.sidebar.subheader("Exam Calendar")

start_date = st.sidebar.date_input(
    "First Exam Date"
)

exam_times = st.sidebar.multiselect(
    "Exam Times",
    ["09:00", "13:00", "16:00"],
    default=["09:00", "13:00"]
)


# --------------------------------------------------
# Student Data Input
# --------------------------------------------------

st.subheader("1. Student Data")

input_method = st.radio(
    "Choose Input Method",
    [
        "Manual Entry",
        "Upload CSV",
        "Quick Demo"
    ],
    horizontal=True
)

df = None


# --------------------------------------------------
# Manual Entry
# --------------------------------------------------

if input_method == "Manual Entry":

    st.write(
        "Enter each student-course enrollment below. "
        "You can add or delete rows."
    )

    manual_data = pd.DataFrame(
        {
            "Student_ID": ["", "", "", "", "", ""],
            "Course": ["", "", "", "", "", ""]
        }
    )

    df = st.data_editor(
        manual_data,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_data_editor"
    )


# --------------------------------------------------
# CSV Upload
# --------------------------------------------------

elif input_method == "Upload CSV":

    st.write(
        "CSV file must contain two columns: "
        "Student_ID and Course"
    )

    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=["csv"]
    )

    if uploaded_file is not None:

        df = pd.read_csv(uploaded_file)


# --------------------------------------------------
# Quick Demo Generator
# --------------------------------------------------

else:

    st.write(
        "Create a sample university dataset automatically."
    )

    demo_col1, demo_col2, demo_col3 = st.columns(3)

    number_of_students = demo_col1.number_input(
        "Number of Students",
        min_value=2,
        max_value=1000,
        value=30,
        step=1
    )

    number_of_courses = demo_col2.number_input(
        "Number of Courses",
        min_value=2,
        max_value=100,
        value=8,
        step=1
    )

    courses_per_student = demo_col3.number_input(
        "Exams per Student",
        min_value=1,
        max_value=int(number_of_courses),
        value=min(3, int(number_of_courses)),
        step=1
    )

    random_seed = st.number_input(
        "Random Seed",
        min_value=1,
        value=42,
        step=1
    )

    rng = random.Random(int(random_seed))

    course_names = [
        f"Course {i}"
        for i in range(1, int(number_of_courses) + 1)
    ]

    demo_rows = []

    for student_id in range(
        1,
        int(number_of_students) + 1
    ):

        selected_courses = rng.sample(
            course_names,
            int(courses_per_student)
        )

        for course in selected_courses:

            demo_rows.append(
                {
                    "Student_ID": student_id,
                    "Course": course
                }
            )

    df = pd.DataFrame(demo_rows)

    st.success(
        "Demo dataset generated automatically."
    )


# --------------------------------------------------
# Process Input Data
# --------------------------------------------------

if df is not None:

    required_columns = {
        "Student_ID",
        "Course"
    }

    if not required_columns.issubset(df.columns):

        st.error(
            "Data must contain Student_ID and Course columns."
        )

    else:

        # ------------------------------------------
        # Clean Data
        # ------------------------------------------

        df = df.dropna(
            subset=["Student_ID", "Course"]
        ).copy()

        df["Student_ID"] = (
            df["Student_ID"]
            .astype(str)
            .str.strip()
        )

        df["Course"] = (
            df["Course"]
            .astype(str)
            .str.strip()
        )

        df = df[
            (df["Student_ID"] != "")
            & (df["Course"] != "")
        ]

        df = df.drop_duplicates(
            subset=["Student_ID", "Course"]
        )

        if df.empty:

            st.info(
                "Enter student and course information to continue."
            )

        else:

            st.success(
                "Student data is ready."
            )

            with st.expander(
                "View Student Data",
                expanded=False
            ):

                st.dataframe(
                    df,
                    use_container_width=True
                )


            # --------------------------------------
            # Convert Data to Student Dictionary
            # --------------------------------------

            students = (
                df.groupby("Student_ID")["Course"]
                .apply(list)
                .to_dict()
            )

            graph = build_conflict_graph(students)

            course_sizes = (
                df.groupby("Course")["Student_ID"]
                .nunique()
                .to_dict()
            )


            # --------------------------------------
            # Dataset Information
            # --------------------------------------

            st.subheader("2. Dataset Information")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Students",
                len(students)
            )

            col2.metric(
                "Courses",
                len(graph)
            )

            conflicts = (
                sum(
                    len(neighbors)
                    for neighbors in graph.values()
                )
                // 2
            )

            col3.metric(
                "Conflicts",
                conflicts
            )

            col4.metric(
                "Enrollments",
                len(df)
            )


            # --------------------------------------
            # Generate Schedule
            # --------------------------------------

            st.subheader("3. Generate Schedule")

            if st.button(
                "Generate Exam Schedule",
                type="primary"
            ):

                if not exam_times:

                    st.error(
                        "Please select at least one exam time."
                    )

                    st.stop()


                # ----------------------------------
                # Select Algorithm
                # ----------------------------------

                if algorithm == "Greedy":

                    schedule = greedy_coloring(
                        graph
                    )

                elif algorithm == "Welsh-Powell":

                    schedule = welsh_powell(
                        graph
                    )

                elif algorithm == "DSATUR":

                    schedule = dsatur(
                        graph
                    )

                elif algorithm == "Local Search":

                    initial = dsatur(
                        graph
                    )

                    schedule = local_search(
                        initial,
                        graph,
                        students,
                        slot_weight
                    )

                else:

                    initial = dsatur(
                        graph
                    )

                    schedule = simulated_annealing(
                        initial,
                        graph,
                        students,
                        slot_weight
                    )


                # ----------------------------------
                # Optimization Results
                # ----------------------------------

                valid = validate_schedule(
                    graph,
                    schedule
                )

                penalty = consecutive_exam_penalty(
                    students,
                    schedule
                )

                cost = total_cost(
                    schedule,
                    students,
                    slot_weight
                )

                slots = max(
                    schedule.values()
                )

                st.subheader(
                    "4. Optimization Results"
                )

                r1, r2, r3, r4 = st.columns(4)

                r1.metric(
                    "Time Slots",
                    slots
                )

                r2.metric(
                    "Penalty",
                    penalty
                )

                r3.metric(
                    "Total Cost",
                    cost
                )

                r4.metric(
                    "Valid Schedule",
                    "Yes" if valid else "No"
                )


                # ----------------------------------
                # Slot -> Date and Time
                # ----------------------------------

                def slot_to_datetime(slot):

                    slot_index = slot - 1

                    exams_per_day = len(
                        exam_times
                    )

                    day_offset = (
                        slot_index
                        // exams_per_day
                    )

                    time_index = (
                        slot_index
                        % exams_per_day
                    )

                    exam_date = (
                        start_date
                        + timedelta(
                            days=day_offset
                        )
                    )

                    exam_time = (
                        exam_times[
                            time_index
                        ]
                    )

                    return (
                        exam_date,
                        exam_time
                    )


                # ----------------------------------
                # Create Schedule Table
                # ----------------------------------

                schedule_rows = []

                for course, slot in schedule.items():

                    exam_date, exam_time = (
                        slot_to_datetime(
                            slot
                        )
                    )

                    jalali_date = (
                        jdatetime.date.fromgregorian(
                            date=exam_date
                        )
                    )

                    schedule_rows.append(
                        {
                            "Course": course,
                            "Students": course_sizes.get(
                                course,
                                0
                            ),
                            "Slot": slot,
                            "Gregorian Date":
                                exam_date.strftime(
                                    "%Y-%m-%d"
                                ),
                            "Jalali Date":
                                jalali_date.strftime(
                                    "%Y-%m-%d"
                                ),
                            "Time": exam_time
                        }
                    )

                schedule_df = pd.DataFrame(
                    schedule_rows
                )

                schedule_df = (
                    schedule_df.sort_values(
                        [
                            "Slot",
                            "Course"
                        ]
                    )
                )


                # ----------------------------------
                # Schedule Table
                # ----------------------------------

                st.subheader(
                    "5. Exam Schedule"
                )

                st.dataframe(
                    schedule_df,
                    use_container_width=True,
                    hide_index=True
                )


                # ----------------------------------
                # Visual Calendar
                # ----------------------------------

                st.subheader(
                    "6. Calendar View"
                )

                unique_dates = (
                    schedule_df[
                        "Gregorian Date"
                    ]
                    .drop_duplicates()
                    .tolist()
                )

                for current_date in unique_dates:

                    day_schedule = (
                        schedule_df[
                            schedule_df[
                                "Gregorian Date"
                            ]
                            == current_date
                        ]
                    )

                    jalali_day = (
                        day_schedule[
                            "Jalali Date"
                        ]
                        .iloc[0]
                    )

                    st.markdown(
                        f"### 📅 {jalali_day}"
                    )

                    st.caption(
                        f"Gregorian: {current_date}"
                    )

                    time_columns = st.columns(
                        len(exam_times)
                    )

                    for column, exam_time in zip(
                        time_columns,
                        exam_times
                    ):

                        with column:

                            st.markdown(
                                f"**🕒 {exam_time}**"
                            )

                            exams_at_time = (
                                day_schedule[
                                    day_schedule[
                                        "Time"
                                    ]
                                    == exam_time
                                ]
                            )

                            if exams_at_time.empty:

                                st.caption(
                                    "No exam"
                                )

                            else:

                                for _, exam in (
                                    exams_at_time.iterrows()
                                ):

                                    st.info(
                                        f"**{exam['Course']}**\n\n"
                                        f"Students: "
                                        f"{exam['Students']}\n\n"
                                        f"Slot: "
                                        f"{exam['Slot']}"
                                    )

                    st.divider()


                # ----------------------------------
                # Download
                # ----------------------------------

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
                    "Download Schedule CSV",
                    csv_output,
                    "exam_schedule.csv",
                    "text/csv"
                )
