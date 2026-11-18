import json
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from src.enums.level_and_comp_status import CompletionStatus
from src.helper.helper_functions import load_prompt
from src.logger.logger import SakuraLogger
from src.models.interview_request import InterviewResponses
from src.models.progress_summary import VoiceExchange, VoiceInterview
from src.models.sakura_models import SakuraScenarios
from src.postgres.postgres_manager import PostgresManager

load_dotenv()
interview_logger = SakuraLogger("interview_service")
evaluation_prompt = load_prompt("evaluation_prompt.md")
MAX_TURNS = int(os.getenv("INTERVIEW_MAX_TURNS", "8"))


class InterviewService:
    """Runs an AI-led Japanese workplace conversation grounded in a scenario."""

    def __init__(self):
        # The active question and conversation history currently live in process
        # memory. Move these fields to the database before running multiple workers.
        self._active_sessions: dict[str, dict] = {}

    def _client(self) -> OpenAI:
        """Create an OpenAI-compatible client configured for the Groq API."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for AI interviews")
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("GROQ_URL", "https://api.groq.com/openai/v1"),
        )

    def _ask_ai(self, instructions: str, history: list[dict]) -> dict:
        """Ask the configured model for a JSON response using conversation history."""
        response = self._client().chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.7,
            max_tokens=2048,
            messages=[{"role": "system", "content": instructions}, *history],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _load_scenario(self, scenario_id: str) -> dict:
        """Load scenario goals and learner level from PostgreSQL for AI context."""
        db = PostgresManager.get_instance()
        with db.session_scope() as session:
            scenario = (
                session.query(SakuraScenarios)
                .filter(SakuraScenarios.scenario_id == scenario_id)
                .first()
            )
            if not scenario:
                raise ValueError(f"Scenario not found: {scenario_id}")
            return {
                "name": scenario.name or "Workplace conversation",
                "description": scenario.description or "",
                "level": scenario.level.value if scenario.level else "N4",
                "job_domain": scenario.job_domain or "workplace",
                "vocabulary": scenario.vocabulary_list or [],
                "grammar": scenario.grammar_focus or [],
                "cultural_notes": scenario.cultural_notes or [],
            }

    def _scenario_prompt(self, scenario: dict) -> str:
        """Build role-play instructions that guide the AI without scripting turns."""
        return (
            "You are the manager or supervisor in a Japanese workplace role-play. "
            "The candidate is always the worker. Speak only as the manager; never speak "
            "for the worker, write the worker's lines, or perform the worker's practice goal. "
            "The scenario's learning goal describes what the candidate should practice, "
            "not what you should say.\n"
            "Begin with a natural manager utterance that invites the worker to respond and "
            "creates an opportunity to practice the scenario goal. For example, ask what "
            "the worker needs or how you can help; do not make the worker's request on "
            "their behalf.\n"
            "After each worker answer, respond appropriately as the manager, then ask one "
            "short, relevant follow-up question in Japanese. You may acknowledge, approve, "
            "or clarify a request, but do not switch roles. Adapt to the learner's answer, "
            "use Japanese appropriate for their level, and do not invent facts outside "
            "the scenario.\n"
            f"Scenario: {scenario['name']}\nContext: {scenario['description']}\n"
            f"Work domain: {scenario['job_domain']}\nJapanese level: {scenario['level']}\n"
            f"Useful vocabulary: {json.dumps(scenario['vocabulary'], ensure_ascii=False)}\n"
            f"Grammar goals: {json.dumps(scenario['grammar'], ensure_ascii=False)}\n"
            f"Cultural goals: {json.dumps(scenario['cultural_notes'], ensure_ascii=False)}\n"
            f"Complete after roughly {MAX_TURNS} learner answers, or sooner if the task has clearly concluded."
        )

    @staticmethod
    def _parse_turn(result: dict) -> dict:
        """Validate and normalize the AI's feedback, next question, and completion flag."""
        question = result.get("next_question")
        feedback = result.get("feedback", "")
        complete = bool(result.get("is_complete", False))
        if not complete and (not isinstance(question, str) or not question.strip()):
            raise ValueError("AI did not return a next question")
        return {
            "next_question": question.strip() if isinstance(question, str) else None,
            "feedback": str(feedback)[:500],
            "is_complete": complete,
        }

    def start_interview(self, scenario_id: str, candidate_id: str) -> InterviewResponses:
        """Create the interview record and ask the AI to generate its opening question."""
        scenario = self._load_scenario(scenario_id)
        instructions = self._scenario_prompt(scenario)
        opening = self._ask_ai(
            instructions
            + '\nFor this opening turn, output only a natural question spoken by the manager '
            + 'to the worker. Invite the worker to begin; do not make the worker request '
            + 'or answer for them. Return JSON with one string field named "question".',
            [],
        )
        question = opening.get("question")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError("AI did not return an opening question")

        interview_id = str(uuid.uuid4())
        now = datetime.now()
        db = PostgresManager.get_instance()
        with db.session_scope() as session:
            session.add(
                VoiceInterview(
                    interview_id=interview_id,
                    user_id=candidate_id,
                    scenario_id=scenario_id,
                    started_at=now,
                    status=CompletionStatus.PROGRESSING.value,
                    created_at=now,
                )
            )

        self._active_sessions[interview_id] = {
            "instructions": instructions,
            "history": [{"role": "assistant", "content": question.strip()}],
            "current_question": question.strip(),
            "turn_number": 1,
        }
        return InterviewResponses(
            interview_id=interview_id, question_text=question.strip(), turn_number=1
        )

    def submit_answer(
        self, interview_id: str, transcript: str, audio_path: str, turn_number: int
    ) -> InterviewResponses:
        """Persist a transcript, get AI coaching and a contextual follow-up, then advance."""
        state = self._active_sessions.get(interview_id)
        if not state:
            raise ValueError(f"No active session for interview id: {interview_id}")
        if turn_number != state["turn_number"]:
            raise ValueError(f"Expected turn {state['turn_number']}, received {turn_number}")
        if not transcript.strip():
            raise ValueError("No speech was recognized. Please record your answer again.")

        history = state["history"] + [{"role": "user", "content": transcript}]
        result = self._ask_ai(
            state["instructions"]
            + '\nRespond to the learner naturally in Japanese. Return JSON with fields: '
            + '"feedback" (brief supportive feedback in simple English), '
            + '"next_question" (one Japanese question; null only when complete), '
            + '"is_complete" (boolean). If complete, give a short natural closing in feedback.',
            history,
        )
        turn = self._parse_turn(result)

        db = PostgresManager.get_instance()
        with db.session_scope() as session:
            session.add(
                VoiceExchange(
                    exchange_id=str(uuid.uuid4()),
                    interview_id=interview_id,
                    turn_number=turn_number,
                    manager_question_text=state["current_question"],
                    candidate_audio_path=audio_path,
                    candidate_transcript=transcript,
                    manager_feedback=turn["feedback"],
                    created_at=datetime.now(),
                )
            )

        if turn["is_complete"] or turn_number >= MAX_TURNS:
            self._mark_complete(interview_id, CompletionStatus.COMPLETE.value)
            return InterviewResponses(
                next_question=None,
                feedback=turn["feedback"],
                turn_number=turn_number,
                is_complete=True,
            )

        next_question = turn["next_question"]
        state["history"] = history + [{"role": "assistant", "content": next_question}]
        state["current_question"] = next_question
        state["turn_number"] = turn_number + 1
        return InterviewResponses(
            next_question=next_question,
            feedback=turn["feedback"],
            turn_number=turn_number + 1,
            is_complete=False,
        )

    def get_current_question(self, interview_id: str) -> InterviewResponses:
        """Return the active question from this process's in-memory session state."""
        state = self._active_sessions.get(interview_id)
        if not state:
            raise ValueError(f"No active session for interview id {interview_id}")
        return InterviewResponses(
            question_text=state["current_question"], turn_number=state["turn_number"]
        )

    def end_interview(self, interview_id: str) -> None:
        """Mark an active interview abandoned when the learner exits early."""
        self._mark_complete(interview_id, CompletionStatus.ABANDONED.value)

    def _mark_complete(self, interview_id: str, status: CompletionStatus) -> None:
        """Persist the final interview status and discard its in-memory state."""
        db = PostgresManager.get_instance()
        with db.session_scope() as session:
            interview = (
                session.query(VoiceInterview)
                .filter(VoiceInterview.interview_id == interview_id)
                .first()
            )
            if interview:
                interview.status = status
                interview.ended_at = datetime.now()
        self._active_sessions.pop(interview_id, None)

    def evaluate_candidate(
        self, transcript_text: str, manager_question: str, scenario_context: str
    ) -> dict:
        """Score a saved answer for report generation and return structured scores."""
        prompt = evaluation_prompt.format(
            scenario_context=scenario_context,
            manager_question=manager_question,
            transcript=transcript_text,
        )
        try:
            content = self._client().chat.completions.create(
                model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
                max_tokens=512,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            ).choices[0].message.content or "{}"
            scores = json.loads(content)
            for key in ("grammar_score", "politeness_score", "fluency_score", "cultural_score", "overall_score"):
                scores.setdefault(key, 0.0)
            scores.setdefault("manager_feedback", "")
            return scores
        except Exception as exc:
            interview_logger.error_log(f"Evaluation failed: {exc}")
            return {
                "grammar_score": 0.0,
                "politeness_score": 0.0,
                "fluency_score": 0.0,
                "cultural_score": 0.0,
                "overall_score": 0.0,
                "manager_feedback": "Evaluation unavailable.",
            }
