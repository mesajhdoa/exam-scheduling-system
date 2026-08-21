import streamlit as st
import pandas as pd
from datetime import timedelta
import jdatetime
import random 
import time

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
from exact_solver import exact_cp_sat
from benchmark_loader import load_itc2007_exam

def validate_itc2007_period_constraints(
    schedule,
    period_hard_constraints
):
    """
    Validate supported ITC2007 period hard constraints.

    Currently supports:
    - EXCLUSION
    - EXAM_COINCIDENCE
    """

    if schedule is None:
        return False

    if not period_hard_constraints:
        return True

    for constraint in period_hard_constraints:

        exam_a = f"Exam {constraint['exam_a']}"
        exam_b = f"Exam {constraint['exam_b']}"

        if (
            exam_a not in schedule
            or exam_b not in schedule
        ):
            return False

        constraint_type = constraint["constraint"]

        if constraint_type == "EXCLUSION":

            if schedule[exam_a] == schedule[exam_b]:
                return False

        elif constraint_type == "EXAM_COINCIDENCE":

            if schedule[exam_a] != schedule[exam_b]:
                return False
        elif constraint_type == "AFTER":

            if schedule[exam_a] <= schedule[exam_b]:
                return False
    

    return True

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
        "Quick Demo",
        "ITC2007 Benchmark"
    ],
    horizontal=True
)

df = None
benchmark_data = None


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
# Quick Demo
# --------------------------------------------------

elif input_method == "Quick Demo":

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
        for i in range(
            1,
            int(number_of_courses) + 1
        )
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
# ITC2007 Benchmark
# --------------------------------------------------

else:

    st.write(
        "Upload an ITC2007 Examination Timetabling "
        "benchmark instance."
    )

    benchmark_file = st.file_uploader(
        "Choose ITC2007 .exam file",
        type=["exam"]
    )

    if benchmark_file is not None:

        try:

            benchmark_data = load_itc2007_exam(
                benchmark_file
            )

            benchmark_rows = []

            for student_id, exams in (
                benchmark_data["students"].items()
            ):

                for exam in exams:

                    benchmark_rows.append(
                        {
                            "Student_ID": student_id,
                            "Course": exam
                        }
                    )

            df = pd.DataFrame(
                benchmark_rows
            )

            metadata = benchmark_data[
                "metadata"
            ]

            st.success(
                "ITC2007 benchmark loaded successfully."
            )

            b1, b2, b3, b4 = st.columns(4)

            b1.metric(
                "Exams",
                metadata["exam_count"]
            )

            b2.metric(
                "Students",
                metadata["student_count"]
            )

            b3.metric(
                "Enrollments",
                metadata["enrollment_count"]
            )

            b4.metric(
                "Periods",
                metadata["period_count"]
            )

            st.info(
                "Benchmark mode currently evaluates the "
                "student conflict graph with the project's "
                "existing scheduling objective. Full ITC2007 "
                "room and hard-constraint optimization will "
                "be integrated separately."
            )

        except Exception as error:

            st.error(
                f"Could not read benchmark: {error}"
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

            # --------------------------------------
            # ITC2007 EXCLUSION Constraints
            # --------------------------------------

            if benchmark_data is not None:

                for constraint in benchmark_data[
                    "period_hard_constraints"
                ]:

                    if constraint["constraint"] == "EXCLUSION":

                        exam_a = f"Exam {constraint['exam_a']}"
                        exam_b = f"Exam {constraint['exam_b']}"

                        if (
                            exam_a in graph
                            and exam_b in graph
                        ):
                            graph[exam_a].add(exam_b)
                            graph[exam_b].add(exam_a)

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



            # --------------------------------------
            # Compare All Algorithms
            # --------------------------------------

            st.divider()

            st.subheader(
                "7. Algorithm Comparison"
            )

            st.write(
                "Run all five scheduling methods on the same "
                "dataset and compare solution quality and runtime."
            )

            if st.button(
                "Compare All Algorithms"
            ):

                algorithm_names = [
                    "Greedy",
                    "Welsh-Powell",
                    "DSATUR",
                    "Local Search",
                    "Simulated Annealing"
                ]

                comparison_rows = []

                for method in algorithm_names:

                    start_time = time.perf_counter()

                    if method == "Greedy":

                        result_schedule = (
                            greedy_coloring(graph)
                        )

                    elif method == "Welsh-Powell":

                        result_schedule = (
                            welsh_powell(graph)
                        )

                    elif method == "DSATUR":

                        result_schedule = (
                            dsatur(graph)
                        )

                    elif method == "Local Search":

                        initial = dsatur(graph)

                        result_schedule = (
                            local_search(
                                initial,
                                graph,
                                students,
                                slot_weight
                            )
                        )

                    else:

                        initial = dsatur(graph)

                        result_schedule = (
                            simulated_annealing(
                                initial,
                                graph,
                                students,
                                slot_weight
                            )
                        )

                    end_time = time.perf_counter()

                    runtime_ms = (
                        end_time - start_time
                    ) * 1000

                    result_valid = (
    validate_schedule(
        graph,
        result_schedule
    )
    and (
        benchmark_data is None
        or validate_itc2007_period_constraints(
            result_schedule,
            benchmark_data["period_hard_constraints"]
        )
    )
)
                    result_penalty = (
                        consecutive_exam_penalty(
                            students,
                            result_schedule
                        )
                    )

                    result_cost = (
                        total_cost(
                            result_schedule,
                            students,
                            slot_weight
                        )
                    )

                    result_slots = max(
                        result_schedule.values()
                    )

                    comparison_rows.append(
                        {
                            "Algorithm": method,
                            "Slots": result_slots,
                            "Penalty": result_penalty,
                            "Cost": result_cost,
                            "Runtime (ms)": round(
                                runtime_ms,
                                3
                            ),
                            "Valid": "Yes" if result_valid else "No"
                        }
                    )
                
                # ----------------------------------
                # Exact CP-SAT
                # ----------------------------------

                exact_schedule, exact_info = exact_cp_sat(
                    graph,
                    students,
                    slot_weight,
                    time_limit=30,
                    period_hard_constraints=(
                        benchmark_data["period_hard_constraints"]
                        if benchmark_data is not None
                        else None
                    ),
                    rooms=(
                        benchmark_data["rooms"]
                        if benchmark_data is not None
                        else None
                    ),
                    course_sizes=course_sizes,
                    room_hard_constraints=(
                        benchmark_data["room_hard_constraints"]
                        if benchmark_data is not None
                        else None
                    )
                )
                
                exact_optimal = (
                    exact_info["optimal"]
                    and exact_info["cost"] is not None
                )
                
                if exact_schedule is not None:

                    exact_valid = (
                        validate_schedule(
                            graph,
                            exact_schedule
                        )
                        and (
                            benchmark_data is None
                            or validate_itc2007_period_constraints(
                                exact_schedule,
                                benchmark_data["period_hard_constraints"]
                            )
                        )
                    )

                    comparison_rows.append(
                        {
                            "Algorithm": "Exact CP-SAT",
                            "Slots": exact_info["slots"],
                            "Penalty": exact_info["penalty"],
                            "Cost": exact_info["cost"],
                            "Runtime (ms)": round(
                                exact_info["runtime"] * 1000,
                                3
                            ),
                            "Valid": "Yes" if exact_valid else "No"
                        }
                    )
                
                
                comparison_df = pd.DataFrame(
                    comparison_rows
                )

                if exact_optimal:

                    optimal_cost = exact_info["cost"]

                    comparison_df["Gap (%)"] = comparison_df.apply(
                        lambda row: (
                            round(
                                (
                                    row["Cost"]
                                    - optimal_cost
                                )
                                / optimal_cost
                                * 100,
                                2
                            )
                            if row["Valid"] == "Yes"
                            else "N/A"
                        ),
                        axis=1
                    )
            

                else:

                    comparison_df["Gap (%)"] = "N/A"
                
                comparison_df = (
                    comparison_df.sort_values(
                        [
                            "Cost",
                            "Runtime (ms)"
                        ]
                    )
                    .reset_index(
                        drop=True
                    )
                )

                st.dataframe(
                    comparison_df,
                    use_container_width=True,
                    hide_index=True
                )

                heuristic_results = comparison_df[
                    (
                        comparison_df["Valid"] == "Yes"
                    )
                    & (
                        comparison_df["Algorithm"]
                        != "Exact CP-SAT"
                    )
                ]

                if not heuristic_results.empty:

                    best_heuristic = (
                        heuristic_results.iloc[0]
                    )

                    best_col1, best_col2, best_col3 = (
                        st.columns(3)
                    )


                    best_col1.metric(
                        "Best Heuristic",
                        best_heuristic["Algorithm"]
                    )

                    if exact_info["cost"] is not None:

                        best_col2.metric(
                            (
                                "Optimal Cost"
                                if exact_info["optimal"]
                                else "Exact Feasible Cost"
                            ),
                            int(exact_info["cost"])
                        )

                    best_col3.metric(
                        "Exact Solver Status",
                        exact_info["status"]
                    )
                
                


                st.subheader(
                    "Cost Comparison"
                )

                cost_chart = (
                    comparison_df[
                        [
                            "Algorithm",
                            "Cost"
                        ]
                    ]
                    .set_index(
                        "Algorithm"
                    )
                )

                st.bar_chart(
                    cost_chart
                )

                st.subheader(
                    "Runtime Comparison"
                )

                runtime_chart = (
                    comparison_df[
                        [
                            "Algorithm",
                            "Runtime (ms)"
                        ]
                    ]
                    .set_index(
                        "Algorithm"
                    )
                )

                st.bar_chart(
                    runtime_chart
                )
