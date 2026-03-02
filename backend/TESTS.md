## Prompt smoke tests (via `backend/compass_cli`)

- **Timestamp**: 2026-03-02T10:42:35-08:00
- **Working directory**: `backend/`
- **Python**: `Python 3.13.5`
- **CLI**: `python3 -m compass_cli.cli --once "<prompt>"`
- **Note**: Initial run failed due to restricted network access; reran with unrestricted network to reach Supabase/OpenAI.

#### Prompt 1

Command:

- `python3 -m compass_cli.cli --once "Who's the best professor for ECS 36C?"`

Output (stdout+stderr):

```text
For ECS 36C, the main professor with available data is Nicholas Weaver. Here’s a summary based on recent student reviews and metrics:

- Average rating for ECS 36C: 3.8 out of 5
- Average difficulty for ECS 36C: 4.4 out of 5 (quite challenging)
- Would take again: 43%
- Number of reviews for this course: 5 (evidence is somewhat sparse, so keep that in mind)

Sample student comments:
- “Weaver is great, take him to learn Kotlin. Cool lectures. Tests are insane—tons of trick questions that flip ideas learned in class on their head. Hard but good!”
- “Gives confusing lectures, doesn't explain concepts well/at all. Homework frequent/needlessly difficult. Rude/unhelpful during office hours. Tests very difficult, contain concepts not taught in class.”
- “Interesting lecturer, records his lectures, homework a bit difficult but he gives you extra days for full credit, tests are difficult though but he did curve the class.”

Summary:
Nicholas Weaver is knowledgeable and engaging, but his class is considered difficult, with challenging homework and exams. Some students appreciate his teaching style, while others find his explanations confusing and his tests overly tricky. The evidence is limited (only 5 reviews), so experiences may vary.

If you want more details or have a specific preference (e.g., easier grading, more engaging lectures), let me know!
```

#### Prompt 2

Command:

- `python3 -m compass_cli.cli --once "I need to take a computer science elective, who should I take it with?"`

Output (stdout+stderr):

```text
Could you specify which computer science elective you’re interested in? UC Davis offers many electives in computer science (like ECS 150, ECS 152A, ECS 165A, etc.), and the best professor can vary by course. If you let me know the course code or topic, I can give you evidence-based recommendations for the best professors for that specific elective!
```

#### Prompt 3

Command:

- `python3 -m compass_cli.cli --once "I want an easy A for my GE requirement"`

Output (stdout+stderr):

```text
I can help you find an easy A for your GE requirement! To give you the best recommendations, could you please specify:

- Which GE area are you looking to fulfill? (e.g., Arts & Humanities, Social Sciences, Science & Engineering, etc.)
- Do you have any preferences for the type of course (lecture, seminar, online, etc.) or subject area?
- Are you looking for recommendations for a specific quarter?

Let me know, and I’ll find the best options for you!
```

#### Prompt 4

Command:

- `python3 -m compass_cli.cli --once "Who are the top-rated biology professors?"`

Output (stdout+stderr):

```text
It looks like there are no professors specifically listed under "Biology" or "Molecular/Cellular Biology" in the ratings database. Sometimes, biology-related courses at UC Davis are taught under more specific departments like "Molecular and Cellular Biology" (MCB), "Evolution and Ecology" (EVE), or "Neurobiology, Physiology, and Behavior" (NPB).

If you have a specific biology course or a more specific department in mind (like MCB, EVE, or NPB), let me know! I can then find the top-rated professors for that area or course.
```

#### Prompt 5

Command:

- `python3 -m compass_cli.cli --once "I learn best from professors who use lots of real-world examples"`

Output (stdout+stderr):

```text
Thanks for sharing your learning preference! If you let me know which course or subject you're interested in, I can recommend UC Davis professors who are known for using real-world examples in their teaching. I’ll look for professors with reviews mentioning practical applications, engaging examples, or real-life scenarios.

Which course or department are you looking at?
```

#### Prompt 6

Command:

- `python3 -m compass_cli.cli --once "Which math professor has the lightest workload?"`

Output (stdout+stderr):

```text
To give you the best answer, could you clarify if you’re interested in math professors for a specific course (like MAT 21A, MAT 22B, etc.), or are you looking for general information about math professors with the lightest workload across all courses? Workload can vary a lot depending on the course and professor.

If you have a specific course in mind, let me know! Otherwise, I can look up general ratings for math professors with the lowest reported workload.
```

#### Prompt 7

Command:

- `python3 -m compass_cli.cli --once "Tell me about Professor Alexander Aue"`

Output (stdout+stderr):

```text
Professor Alexander Aue has an overall rating of 3.5 out of 5, with a difficulty rating of 3.5. About 54% of students say they would take his class again, indicating a mixed but slightly positive overall impression.

Key points from student reviews:

- Teaching Style: Students note that he explains concepts in depth, sometimes more than necessary, but tries to make things easier with helpful homework and practice exams.
- Exams: Midterms are often considered easy (sometimes with extra credit), but finals can be graded harshly. Formula sheets and practice exams are provided.
- Communication: He is responsive to emails and helpful outside of class.
- Clarity: Some students find his lectures clear and thorough, while others mention he can be boring or hard to understand at times.
- Course Material: Some overlap with previous statistics courses, but the material can feel more challenging due to his teaching style.

Sample student comments:
- "He responds to emails really quickly and is very helpful. His HW assignments are helpful during tests. GOOD TEACHER."
- "He explains his things well, but kinda boring. His test are easy, if you have a ti 89 but you only can use a basic calculator."
- "Simply terrible, could not understand him at all, practice midterms and finals were deceiving and did not prepare you at all for the actual midterm."

Summary: Professor Aue is regarded as a solid, if sometimes challenging, statistics instructor. Students who keep up with notes and attend class tend to do better. Experiences vary, so it may depend on your learning style.

You can read more reviews on his RateMyProfessors profile.
```

#### Prompt 8

Command:

- `python3 -m compass_cli.cli --once "I want a challenging upper-division course, who should I look for?"`

Output (stdout+stderr):

```text
To recommend a challenging upper-division course and the best professors for it, could you specify a subject or department you’re interested in (e.g., Computer Science, Mathematics, Economics)? This will help me find the most relevant and rigorous courses and instructors for you.

If you’re open to any subject, let me know your general interests or career goals, and I can suggest some notoriously challenging upper-division courses and the professors who teach them!
```

#### Prompt 9

Command:

- `python3 -m compass_cli.cli --once "Are there any really engaging lecturers in the psychology department?"`

Output (stdout+stderr):

```text
I couldn't directly search for "engaging" lecturers in the Psychology department, and there isn't a direct list of the most engaging professors available. However, if you have a specific psychology course in mind, I can look up the top-rated professors for that course, which often highlights those who are engaging and effective lecturers. Let me know if there's a particular class or professor you're interested in!
```

#### Prompt 10

Command:

- `python3 -m compass_cli.cli --once "Who teaches MAT 21A and how are they rated?"`

Output (stdout+stderr):

```text
There is not enough data available on professors who teach MAT 21A, so I can't provide ratings or reviews at this time. If you have a specific professor in mind, I can try to look up their profile for you. Let me know if you'd like to try that or if you have any other questions!
```

#### Prompt 11

Command:

- `python3 -m compass_cli.cli --once "I need a professor who's good at explaining complex topics clearly"`

Output (stdout+stderr):

```text
I’d be happy to help! Could you tell me which course or subject you’re interested in? That way, I can recommend professors who are known for explaining complex topics clearly in that specific area.
```
