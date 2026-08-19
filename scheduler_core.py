import random
import math


# --------------------------------------------------
# Build Conflict Graph
# --------------------------------------------------

def build_conflict_graph(students):
    courses = set()

    for course_list in students.values():
        courses.update(course_list)

    graph = {course: set() for course in courses}

    for course_list in students.values():
        for i in range(len(course_list)):
            for j in range(i + 1, len(course_list)):
                course_a = course_list[i]
                course_b = course_list[j]

                graph[course_a].add(course_b)
                graph[course_b].add(course_a)

    return graph


# --------------------------------------------------
# Validate Schedule
# --------------------------------------------------

def validate_schedule(graph, colors):
    for course in graph:
        for conflict in graph[course]:
            if colors[course] == colors[conflict]:
                return False

    return True


# --------------------------------------------------
# Greedy Coloring
# --------------------------------------------------

def greedy_coloring(graph):
    colors = {}

    for course in graph:
        used_colors = {
            colors[n]
            for n in graph[course]
            if n in colors
        }

        color = 1

        while color in used_colors:
            color += 1

        colors[course] = color

    return colors


# --------------------------------------------------
# Welsh-Powell
# --------------------------------------------------

def welsh_powell(graph):
    ordered_courses = sorted(
        graph,
        key=lambda course: len(graph[course]),
        reverse=True
    )

    colors = {}

    for course in ordered_courses:
        used_colors = {
            colors[n]
            for n in graph[course]
            if n in colors
        }

        color = 1

        while color in used_colors:
            color += 1

        colors[course] = color

    return colors


# --------------------------------------------------
# DSATUR
# --------------------------------------------------

def dsatur(graph):
    colors = {}

    while len(colors) < len(graph):
        uncolored = [
            course
            for course in graph
            if course not in colors
        ]

        def saturation_degree(course):
            neighbor_colors = {
                colors[n]
                for n in graph[course]
                if n in colors
            }

            return len(neighbor_colors)

        course = max(
            uncolored,
            key=lambda c: (
                saturation_degree(c),
                len(graph[c])
            )
        )

        used_colors = {
            colors[n]
            for n in graph[course]
            if n in colors
        }

        color = 1

        while color in used_colors:
            color += 1

        colors[course] = color

    return colors


# --------------------------------------------------
# Penalty and Objective Function
# --------------------------------------------------

def consecutive_exam_penalty(students, colors):
    penalty = 0

    for course_list in students.values():
        slots = sorted(colors[course] for course in course_list)

        for i in range(len(slots) - 1):
            if slots[i + 1] - slots[i] == 1:
                penalty += 1

    return penalty


def total_cost(colors, students, slot_weight=10):
    slots = max(colors.values())
    penalty = consecutive_exam_penalty(students, colors)

    return slots * slot_weight + penalty


# --------------------------------------------------
# Local Search
# --------------------------------------------------

def local_search(colors, graph, students, slot_weight=10):
    best_colors = colors.copy()
    best_cost = total_cost(best_colors, students, slot_weight)

    courses = list(graph.keys())

    for course in courses:
        current_slot = best_colors[course]

        for new_slot in range(1, max(best_colors.values()) + 1):
            if new_slot == current_slot:
                continue

            candidate = best_colors.copy()
            candidate[course] = new_slot

            if validate_schedule(graph, candidate):
                candidate_cost = total_cost(
                    candidate,
                    students,
                    slot_weight
                )

                if candidate_cost < best_cost:
                    best_colors = candidate
                    best_cost = candidate_cost

    for i in range(len(courses)):
        for j in range(i + 1, len(courses)):
            course_a = courses[i]
            course_b = courses[j]

            candidate = best_colors.copy()

            candidate[course_a], candidate[course_b] = (
                candidate[course_b],
                candidate[course_a]
            )

            if validate_schedule(graph, candidate):
                candidate_cost = total_cost(
                    candidate,
                    students,
                    slot_weight
                )

                if candidate_cost < best_cost:
                    best_colors = candidate
                    best_cost = candidate_cost

    return best_colors


# --------------------------------------------------
# Simulated Annealing
# --------------------------------------------------

def simulated_annealing(
    colors,
    graph,
    students,
    slot_weight=10,
    iterations=10000,
    seed=42
):
    rng = random.Random(seed)

    current = colors.copy()
    current_cost = total_cost(current, students, slot_weight)

    best = current.copy()
    best_cost = current_cost

    temperature = 100.0
    courses = list(graph.keys())

    for _ in range(iterations):
        candidate = current.copy()

        move_type = rng.choice(["move", "swap"])

        if move_type == "move":
            course = rng.choice(courses)

            new_slot = rng.randint(
                1,
                max(current.values())
            )

            candidate[course] = new_slot

        else:
            course_a, course_b = rng.sample(courses, 2)

            candidate[course_a], candidate[course_b] = (
                candidate[course_b],
                candidate[course_a]
            )

        if not validate_schedule(graph, candidate):
            continue

        candidate_cost = total_cost(
            candidate,
            students,
            slot_weight
        )

        difference = candidate_cost - current_cost

        if difference < 0:
            current = candidate
            current_cost = candidate_cost

        else:
            probability = math.exp(
                -difference / temperature
            )

            if rng.random() < probability:
                current = candidate
                current_cost = candidate_cost

        if current_cost < best_cost:
            best = current.copy()
            best_cost = current_cost

        temperature *= 0.999

    return best
