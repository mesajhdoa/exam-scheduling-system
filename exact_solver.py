from ortools.sat.python import cp_model


def exact_cp_sat(
    graph,
    students,
    slot_weight=10,
    time_limit=30,
    period_hard_constraints=None
):
    """
    Solve the exam scheduling problem using Google OR-Tools CP-SAT.

    Supports:
    - student conflict constraints
    - ITC2007 EXCLUSION constraints
    """

    if not graph:
        return {}, {
            "status": "EMPTY",
            "optimal": True,
            "cost": 0,
            "slots": 0,
            "penalty": 0,
            "runtime": 0,
            "best_bound": 0
        }

    model = cp_model.CpModel()

    courses = list(graph.keys())

    number_of_courses = len(courses)

    # --------------------------------------------------
    # Slot Variables
    # --------------------------------------------------

    slot = {
        course: model.NewIntVar(
            1,
            number_of_courses,
            f"slot_{course}"
        )
        for course in courses
    }


    # --------------------------------------------------
    # Student Conflict Constraints
    # --------------------------------------------------

    added_edges = set()

    for course_a in courses:

        for course_b in graph[course_a]:

            edge = tuple(
                sorted(
                    [
                        course_a,
                        course_b
                    ]
                )
            )

            if edge in added_edges:
                continue

            added_edges.add(edge)

            model.Add(
                slot[course_a]
                !=
                slot[course_b]
            )


    # --------------------------------------------------
    # ITC2007 EXCLUSION Constraints
    # --------------------------------------------------

    if period_hard_constraints is not None:

        for constraint in period_hard_constraints:

            if (
                constraint["constraint"]
                == "EXCLUSION"
            ):

                exam_a = (
                    f"Exam {constraint['exam_a']}"
                )

                exam_b = (
                    f"Exam {constraint['exam_b']}"
                )

                if (
                    exam_a in slot
                    and exam_b in slot
                ):

                    model.Add(
                        slot[exam_a]
                        !=
                        slot[exam_b]
                    )


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


    # --------------------------------------------------
    # Remove Shifted Equivalent Solutions
    # --------------------------------------------------

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

    for student_id, course_list in students.items():

        for i in range(len(course_list)):

            for j in range(
                i + 1,
                len(course_list)
            ):

                course_a = course_list[i]
                course_b = course_list[j]

                if (
                    course_a not in slot
                    or course_b not in slot
                ):
                    continue

                difference = model.NewIntVar(
                    0,
                    number_of_courses,
                    (
                        f"diff_"
                        f"{student_id}_"
                        f"{i}_"
                        f"{j}"
                    )
                )

                model.AddAbsEquality(
                    difference,
                    slot[course_a]
                    - slot[course_b]
                )

                consecutive = model.NewBoolVar(
                    (
                        f"consecutive_"
                        f"{student_id}_"
                        f"{i}_"
                        f"{j}"
                    )
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


    # --------------------------------------------------
    # Objective
    # --------------------------------------------------

    total_penalty = sum(
        penalty_variables
    )

    model.Minimize(
        slot_weight * max_slot
        + total_penalty
    )


    # --------------------------------------------------
    # Solver
    # --------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        float(time_limit)
    )

    solver.parameters.num_search_workers = 1

    solver.parameters.random_seed = 42

    status = solver.Solve(model)


    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    status_name = solver.StatusName(status)

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
            "runtime": solver.WallTime(),
            "best_bound": (
                solver.BestObjectiveBound()
            )
        }


    # --------------------------------------------------
    # Extract Solution
    # --------------------------------------------------

    schedule = {
        course: solver.Value(
            slot[course]
        )
        for course in courses
    }

    used_slots = max(
        schedule.values()
    )

    penalty_value = sum(
        solver.Value(variable)
        for variable in penalty_variables
    )

    cost_value = (
        slot_weight * used_slots
        + penalty_value
    )


    return schedule, {
        "status": status_name,
        "optimal": (
            status == cp_model.OPTIMAL
        ),
        "cost": cost_value,
        "slots": used_slots,
        "penalty": penalty_value,
        "runtime": solver.WallTime(),
        "best_bound": (
            solver.BestObjectiveBound()
        )
    }
