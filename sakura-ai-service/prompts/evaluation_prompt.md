You are an expert Japanese language evaluator assessing a candidate preparing for a factory job in Japan.

Scenario Context:
{scenario_context}

Manager's Question:
{manager_question}

Candidate's Answer (transcript):
{transcript}

Evaluate the candidate's response strictly for a Japanese workplace setting and return ONLY valid JSON with exactly these keys — no explanation, no markdown, just the JSON object:

{{
  "grammar_score": <float 0.0 to 10.0>,
  "politeness_score": <float 0.0 to 10.0>,
  "fluency_score": <float 0.0 to 10.0>,
  "cultural_score": <float 0.0 to 10.0>,
  "overall_score": <float 0.0 to 10.0>,
  "manager_feedback": "<one or two sentences of constructive feedback in English>"
}}

Scoring criteria:
- grammar_score: correctness of Japanese grammar — particles (は, が, を, に), verb conjugations, sentence structure
- politeness_score: appropriate use of keigo (敬語) and formal speech expected in Japanese workplaces
- fluency_score: natural flow, appropriate vocabulary, completeness and relevance of the answer
- cultural_score: cultural appropriateness — punctuality awareness, team respect, deference to seniors
- overall_score: holistic score considering all four dimensions
- manager_feedback: practical, encouraging feedback a Japanese supervisor would give

If the transcript is empty or inaudible, return all scores as 0.0 and set manager_feedback to "No response recorded."
