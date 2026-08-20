from ortools.sat.python import cp_model


def exact_cp_sat(
    graph,
    students,
    slot_weight=10,
    time_limit=30
):
    """
    Exact exam scheduling with Google OR-Tools CP-SAT.

    Objective:
        slot_weight * max_slot
        + consecutive_exam_penalty

    Returns:
        schedule, info
    """

    courses = list(graph.keys())

    if not courses:
        return {}, {
            "status": "EMPTY",
            "optimal": True,
            "cost": 0,
            "slots": 0,
            "penalty": 0,
            "runtime": 0.0
        }

    number_of_courses = len(courses)

    model = cp_model.CpModel()

    # --------------------------------------------------
    # Slot Variables
    # --------------------------------------------------

    slot = {}

    for index, course in enumerate(courses):

        slot[course] = model.NewIntVar(
            1,
            number_of_courses,
            f"slot_{index}"
        )

    # --------------------------------------------------
    # Conflict Constraints
    # --------------------------------------------------

    added_edges = set()

    for course_a in courses:

        for course_b in graph[course_a]:

            edge = frozenset(
                [course_a, course_b]
            )

            if edge in added_edges:
                continue

            model.Add(
                slot[course_a]
                != slot[course_b]
            )

            added_edges.add(edge)

    # --------------------------------------------------
    # Maximum Slot
    # --------------------------------------------------

    max_slot = model.NewIntVar(
        1,
        number_of_courses,
        "max_slot"
    )

    model.AddMaxEquality(
        max_slot,
        list(slot.values())
    )

    # Force the schedule to start from Slot 1.
    # This removes unnecessary shifted solutions.

    min_slot = model.NewIntVar(
        1,
        number_of_courses,
        "min_slot"
    )

    model.AddMinEquality(
        min_slot,
        list(slot.values())
    )

    model.Add(
        min_slot == 1
    )

    # --------------------------------------------------
    # Consecutive Exam Penalty
    # --------------------------------------------------

    penalty_variables = []

    penalty_index = 0

    for student_courses in students.values():

        # Remove duplicate courses while
        # preserving their original order.

        unique_courses = list(
            dict.fromkeys(student_courses)
        )

        unique_courses = [
            course
            for course in unique_courses
            if course in slot
        ]

        for i in range(
            len(unique_courses)
        ):

            for j in range(
                i + 1,
                len(unique_courses)
            ):

                course_a = unique_courses[i]
                course_b = unique_courses[j]

                difference = model.NewIntVar(
                    0,
                    number_of_courses - 1,
                    f"difference_{penalty_index}"
                )

                model.AddAbsEquality(
                    difference,
                    slot[course_a]
                    - slot[course_b]
                )

                consecutive = model.NewBoolVar(
                    f"consecutive_{penalty_index}"
                )

                model.Add(
                    difference == 1
                ).OnlyEnforceIf(
                    consecutive
                )

                model.Add(
                    difference != 1
                ).OnlyEnforceIf(
                    consecutive.Not()
                )

                penalty_variables.append(
                    consecutive
                )

                penalty_index += 1

    # --------------------------------------------------
    # Objective Function
    # --------------------------------------------------

    if penalty_variables:

        total_penalty = sum(
            penalty_variables
        )

        model.Minimize(
            slot_weight * max_slot
            + total_penalty
        )

    else:

        model.Minimize(
            slot_weight * max_slot
        )

    # --------------------------------------------------
    # Solver
    # --------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        float(time_limit)
    )

    # One worker gives more reproducible results.

    solver.parameters.num_search_workers = 1

    solver.parameters.random_seed = 42

    status = solver.Solve(
        model
    )

    status_name = solver.StatusName(
        status
    )

    # --------------------------------------------------
    # Solution
    # --------------------------------------------------

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        return None, {
            "status": status_name,
            "optimal": False,
            "cost": None,
            "slots": None,
            "penalty": None,
            "runtime": solver.WallTime()
        }

    schedule = {
        course: solver.Value(
            slot[course]
        )
        for course in courses
    }

    slots_used = max(
        schedule.values()
    )

    penalty_value = sum(
        solver.Value(variable)
        for variable in penalty_variables
    )

    cost_value = (
        slot_weight * slots_used
        + penalty_value
    )

    info = {
        "status": status_name,
        "optimal": (
            status == cp_model.OPTIMAL
        ),
        "cost": cost_value,
        "slots": slots_used,
        "penalty": penalty_value,
        "runtime": solver.WallTime(),
        "best_bound": solver.BestObjectiveBound()
    }

    return schedule, info
