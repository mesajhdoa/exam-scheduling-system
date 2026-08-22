from ortools.sat.python import cp_model


def exact_cp_sat(
    graph,
    students,
    slot_weight=10,
    time_limit=30,
    period_hard_constraints=None,
    rooms=None,
    course_sizes=None,
    room_hard_constraints=None
    periods=None
    
):
    """
    Solve the exam scheduling problem using Google OR-Tools CP-SAT.

    Supports:
    - student conflict constraints
    - ITC2007 EXCLUSION
    - ITC2007 EXAM_COINCIDENCE
    - ITC2007 AFTER
    - room assignment
    - room capacity
    - ROOM_EXCLUSIVE
    """

    if not graph:
        return {}, {
            "status": "EMPTY",
            "optimal": True,
            "cost": 0,
            "slots": 0,
            "penalty": 0,
            "runtime": 0,
            "best_bound": 0,
            "room_assignment": {}
        }

    model = cp_model.CpModel()

    courses = list(graph.keys())
    number_of_courses = len(courses)
    number_of_periods = (
        len(periods)
        if periods is not None and len(periods) > 0
        else number_of_courses
    )

    

    # --------------------------------------------------
    # Slot Variables
    # --------------------------------------------------

    slot = {
        course: model.NewIntVar(
            1,
            number_of_periods,
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
                != slot[course_b]
            )

    # --------------------------------------------------
    # ITC2007 Period Hard Constraints
    # --------------------------------------------------

    if period_hard_constraints is not None:

        for constraint in period_hard_constraints:

            exam_a = (
                f"Exam {constraint['exam_a']}"
            )

            exam_b = (
                f"Exam {constraint['exam_b']}"
            )

            if (
                exam_a not in slot
                or exam_b not in slot
            ):
                continue

            constraint_type = constraint[
                "constraint"
            ]

            if constraint_type == "EXCLUSION":

                model.Add(
                    slot[exam_a]
                    != slot[exam_b]
                )

            elif constraint_type == "EXAM_COINCIDENCE":

                model.Add(
                    slot[exam_a]
                    == slot[exam_b]
                )

            elif constraint_type == "AFTER":

                model.Add(
                    slot[exam_a]
                    > slot[exam_b]
                )

    # --------------------------------------------------
    # Room Assignment
    # --------------------------------------------------

    room_use = None
    occupancy = None

    room_data_available = (
        rooms is not None
        and course_sizes is not None
        and len(rooms) > 0
    )

    if room_data_available:

        number_of_rooms = len(rooms)

        # Each exam must use exactly one room.

        room_use = {}

        for course in courses:

            room_variables = []

            for room_id in range(
                number_of_rooms
            ):

                variable = model.NewBoolVar(
                    f"room_{course}_{room_id}"
                )

                room_use[
                    course,
                    room_id
                ] = variable

                room_variables.append(
                    variable
                )

            model.AddExactlyOne(
                room_variables
            )

        # --------------------------------------------------
        # Slot Indicator Variables
        # --------------------------------------------------

        slot_is = {}

        for course in courses:

            for period in range(
                1,
                number_of_courses + 1
            ):

                variable = model.NewBoolVar(
                    f"is_slot_{course}_{period}"
                )

                slot_is[
                    course,
                    period
                ] = variable

                model.Add(
                    slot[course] == period
                ).OnlyEnforceIf(
                    variable
                )

                model.Add(
                    slot[course] != period
                ).OnlyEnforceIf(
                    variable.Not()
                )

        # --------------------------------------------------
        # Room + Slot Occupancy Variables
        # --------------------------------------------------

        occupancy = {}

        for course in courses:

            for room_id in range(
                number_of_rooms
            ):

                for period in range(
                    1,
                    number_of_courses + 1
                ):

                    variable = model.NewBoolVar(
                        (
                            f"occupancy_"
                            f"{course}_"
                            f"{room_id}_"
                            f"{period}"
                        )
                    )

                    occupancy[
                        course,
                        room_id,
                        period
                    ] = variable

                    slot_variable = slot_is[
                        course,
                        period
                    ]

                    room_variable = room_use[
                        course,
                        room_id
                    ]

                    # occupancy =
                    # slot_is AND room_use

                    model.Add(
                        variable
                        <= slot_variable
                    )

                    model.Add(
                        variable
                        <= room_variable
                    )

                    model.Add(
                        variable
                        >= (
                            slot_variable
                            + room_variable
                            - 1
                        )
                    )

        # --------------------------------------------------
        # Room Capacity
        # --------------------------------------------------

        for room_id, room_info in enumerate(
            rooms
        ):

            capacity = int(
                room_info["capacity"]
            )

            for period in range(
                1,
                number_of_courses + 1
            ):

                model.Add(
                    sum(
                        int(
                            course_sizes.get(
                                course,
                                0
                            )
                        )
                        * occupancy[
                            course,
                            room_id,
                            period
                        ]
                        for course in courses
                    )
                    <= capacity
                )

        # --------------------------------------------------
        # ROOM_EXCLUSIVE
        # --------------------------------------------------

        if room_hard_constraints is not None:

            exclusive_courses = set()

            for constraint in (
                room_hard_constraints
            ):

                if (
                    constraint["constraint"]
                    == "ROOM_EXCLUSIVE"
                ):

                    exam_name = (
                        f"Exam {constraint['exam_id']}"
                    )

                    if exam_name in slot:
                        exclusive_courses.add(
                            exam_name
                        )

            for exclusive_course in (
                exclusive_courses
            ):

                for room_id in range(
                    number_of_rooms
                ):

                    for period in range(
                        1,
                        number_of_courses + 1
                    ):

                        exclusive_occupancy = (
                            occupancy[
                                exclusive_course,
                                room_id,
                                period
                            ]
                        )

                        model.Add(
                            sum(
                                occupancy[
                                    course,
                                    room_id,
                                    period
                                ]
                                for course in courses
                            )
                            <= 1
                        ).OnlyEnforceIf(
                            exclusive_occupancy
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

    for student_id, course_list in (
        students.items()
    ):

        for i in range(
            len(course_list)
        ):

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

    status_name = solver.StatusName(
        status
    )

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
            ),
            "room_assignment": None
        }

    # --------------------------------------------------
    # Extract Schedule
    # --------------------------------------------------

    schedule = {
        course: solver.Value(
            slot[course]
        )
        for course in courses
    }

    # --------------------------------------------------
    # Extract Room Assignment
    # --------------------------------------------------

    room_assignment = {}

    if room_use is not None:

        number_of_rooms = len(rooms)

        for course in courses:

            for room_id in range(
                number_of_rooms
            ):

                if solver.Value(
                    room_use[
                        course,
                        room_id
                    ]
                ):

                    room_assignment[
                        course
                    ] = room_id

                    break

    # --------------------------------------------------
    # Final Metrics
    # --------------------------------------------------

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
        ),
        "room_assignment": (
            room_assignment
        )
    }
