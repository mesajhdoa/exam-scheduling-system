# Academic Scheduling System

An academic scheduling and optimization system for **exam timetabling** and **course scheduling**, developed with Python and Streamlit.

The project combines graph-coloring heuristics, metaheuristic optimization, and an exact **Google OR-Tools CP-SAT** model. It also supports selected constraints and penalty components from the **ITC2007 Examination Timetabling** benchmark format.

## Live Demo

- **Exam Scheduling:**  
  https://exam-scheduling-system-jrckrhb9prfjntqpoyqrzx.streamlit.app/

- **Course Scheduling:**  
  https://exam-scheduling-system-jrckrhb9prfjntqpoyqrzx.streamlit.app/Course_Scheduling

## Repository

https://github.com/mesajhdoa/exam-scheduling-system

---

## Project Overview

Academic timetabling is a combinatorial optimization problem in which exams or courses must be assigned to available time periods while satisfying hard constraints and reducing undesirable scheduling situations.

This project contains two related scheduling modules:

1. **Exam Scheduling**
   - Creates conflict-free examination timetables.
   - Supports multiple heuristic and optimization algorithms.
   - Supports ITC2007 benchmark input.
   - Includes period and room constraints.
   - Includes an exact CP-SAT optimization model.

2. **Course Scheduling**
   - Creates weekly course timetables before student enrollment.
   - Detects conflicts between courses belonging to the same cohort, semester, related group, or explicit non-overlap requirements.
   - Supports configurable teaching days and class times.

---

## Exam Scheduling Problem

The basic exam scheduling problem is modeled as a **graph-coloring problem**.

- Each exam is represented by a vertex.
- An edge connects two exams if at least one student is enrolled in both.
- A graph color represents an examination time slot.
- Adjacent vertices cannot receive the same color.

Formally, for every conflict edge:

```text
(u, v) ∈ E  =>  slot(u) != slot(v)
