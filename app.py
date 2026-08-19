import streamlit as st
import pandas as pd
from datetime import timedelta
import jdatetime

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


st.set_page_config(
    page_title="Exam Scheduling System",
    page_icon="📅",
    layout="wide"
)

st.title("Exam Scheduling System")

st.write(
    "Upload student-course enrollment data and generate "
    "a conflict-free optimized exam schedule."
)

# --------------------------------------------------
# Settings
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
# CSV Input
# --------------------------------------------------

st.subheader("1. Upload Student Data")

st.write(
    "CSV file must contain two columns: Student_ID and Course"
)

uploaded_file = st.file_uploader(
    "Choose CSV file",
    type=["csv"]
)

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    required_columns = {"Student_ID", "Course"}

    if not required_columns.issubset(df.columns):

        st.error(
            "CSV must contain Student_ID and Course columns."
        )

    else:

        st.success("Student data loaded successfully.")

        st.dataframe(
            df,
            use_container_width=True
        )

        # ------------------------------------------
        # Convert CSV to student dictionary
        # ------------------------------------------

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
        # ------------------------------------------
        # Dataset Information
        # ------------------------------------------

        st.subheader("2. Dataset Information")

        col1, col2, col3 = st.columns(3)

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

        # ------------------------------------------
        # Generate Schedule
        # ------------------------------------------

        st.subheader("3. Generate Schedule")

        if st.button("Generate Exam Schedule"):

            if not exam_times:

                st.error(
                    "Please select at least one exam time."
                )

                st.stop()

            # --------------------------------------
            # Select Algorithm
            # --------------------------------------

            if algorithm == "Greedy":

                schedule = greedy_coloring(graph)

            elif algorithm == "Welsh-Powell":

                schedule = welsh_powell(graph)

            elif algorithm == "DSATUR":

                schedule = dsatur(graph)

            elif algorithm == "Local Search":

                initial = dsatur(graph)

                schedule = local_search(
                    initial,
                    graph,
                    students,
                    slot_weight
                )

            else:

                initial = dsatur(graph)

                schedule = simulated_annealing(
                    initial,
                    graph,
                    students,
                    slot_weight
                )

            # --------------------------------------
            # Optimization Results
            # --------------------------------------

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

            slots = max(schedule.values())

            st.subheader("4. Optimization Results")

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

            # --------------------------------------
            # Convert Slot to Date and Time
            # --------------------------------------

            def slot_to_datetime(slot):

                slot_index = slot - 1

                exams_per_day = len(exam_times)

                day_offset = (
                    slot_index // exams_per_day
                )

                time_index = (
                    slot_index % exams_per_day
                )

                exam_date = (
                    start_date
                    + timedelta(days=day_offset)
                )

                exam_time = exam_times[time_index]

                return exam_date, exam_time

            # --------------------------------------
            # Schedule Table
            # --------------------------------------

            schedule_rows = []

            for course, slot in schedule.items():

            for course, slot in schedule.items():

                exam_date, exam_time = (
                    slot_to_datetime(slot)
                )

                jalali_date = jdatetime.date.fromgregorian(
                    date=exam_date
                )

                schedule_rows.append(
                    {
                        "Course": course,
                        "Students": course_sizes.get(course, 0),
                        "Slot": slot,
                        "Gregorian Date": exam_date.strftime(
                            "%Y-%m-%d"
                        ),
                        "Jalali Date": jalali_date.strftime(
                            "%Y-%m-%d"
                        ),
                        "Time": exam_time
                    }
                )

            schedule_df = pd.DataFrame(
                schedule_rows
            )

            schedule_df = schedule_df.sort_values(
                ["Slot", "Course"]
            )

            st.subheader("5. Exam Schedule")

            st.dataframe(
                schedule_df,
                use_container_width=True
            )

            # --------------------------------------
            # Download
            # --------------------------------------

            csv_output = schedule_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download Schedule CSV",
                csv_output,
                "exam_schedule.csv",
                "text/csv"
            )
