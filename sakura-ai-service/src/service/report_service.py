import uuid
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from src.models.progress_summary import ProgressSummary
from src.logger.logger import SakuraLogger
from src.service.interview_service import InterviewService as ResponseEvaluator
from src.models.progress_summary import VoiceInterview, VoiceExchange, UsersScore
from src.models.sakura_models import SakuraScenarios, SakuraUsers
from src.postgres.postgres_manager import PostgresManager
from pathlib import Path
from src.exception.exception import raise_exception
from src.report.pdf_report import build_pdf_report
from src.constants.constants import FAILED

reporter_logger = SakuraLogger()
evaluator = ResponseEvaluator()

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportService:
    """Evaluates interview turns, stores scores, and builds downloadable PDFs."""

    # ------------------------------------------------------------------ #
    #  Main entry point                                                    #
    # ------------------------------------------------------------------ #

    def generate(self, interview_id: str) -> str:
        """
        Load an interview and its answers, score each transcript with the LLM,
        average the scores, save scores to PostgreSQL, and build a PDF report.

        Returns the generated PDF's local path. Raises ``ValueError`` if the
        interview or its saved answers do not exist.
        """
        db = PostgresManager.get_instance()
        with db.session_scope() as session:
            interview = (
                session.query(VoiceInterview)
                .filter(VoiceInterview.interview_id == interview_id)
                .first()
            )
            reporter_logger.info_log(f"Interview : {interview}")
            if not interview:
                raise ValueError(f"Interview not found for interview id:{interview_id}")

            exchanges = (
                session.query(VoiceExchange)
                .filter(VoiceExchange.interview_id == interview_id)
                .order_by(VoiceExchange.turn_number)
                .all()
            )

            reporter_logger.info_log(f"Exchanges : {exchanges}")

            if not exchanges:
                raise ValueError(f"No exchanges found for interview: {interview_id}")

            # Fetch scenario and candidate names for the PDF
            scenario = (
                session.query(SakuraScenarios)
                .filter(SakuraScenarios.scenario_id == interview.scenario_id)
                .first()
            )

            reporter_logger.info_log(f"scenario : {scenario}")

            candidate = (
                session.query(SakuraUsers)
                .filter(SakuraUsers.user_id == interview.user_id)
                .first()
            )

            scenario_name = scenario.name if scenario else "Unknown Scenario"
            scenario_context = scenario.description if scenario else ""
            candidate_name = candidate.name if candidate else "Unknown Candidate"

            # ---------------------------------------------------------- #
            #  Evaluate each turn                                         #
            # ---------------------------------------------------------- #
            evaluated_turns = []
            score_totals = {
                "grammar_score": 0.0,
                "politeness_score": 0.0,
                "fluency_score": 0.0,
                "cultural_score": 0.0,
                "overall_score": 0.0,
            }

            for exchange in exchanges:
                transcript = exchange.candidate_transcript or ""
                question = exchange.manager_question_text or ""

                scores = evaluator.evaluate_candidate(
                    transcript_text=transcript,
                    manager_question=question,
                    scenario_context=scenario_context,
                )

                reporter_logger.info_log(f"scores : {scores}")

                # Write per-turn scores back to VoiceExchange
                exchange.grammar_score = scores.get("grammar_score", 0.0)
                exchange.flow_score = scores.get("fluency_score", 0.0)
                exchange.manager_feedback = scores.get("manager_feedback", "")

                for key in score_totals:
                    score_totals[key] += scores.get(key, 0.0)

                evaluated_turns.append(
                    {
                        "turn_number": exchange.turn_number,
                        "question": question,
                        "transcript": transcript,
                        "scores": scores,
                    }
                )

                reporter_logger.info_log(f"evaluated_turns : {evaluated_turns}")

            # ---------------------------------------------------------- #
            #  Average scores                                              #
            # ---------------------------------------------------------- #
            n = len(exchanges)
            avg = {k: round(v / n, 2) for k, v in score_totals.items()}

            # ---------------------------------------------------------- #
            #  Save to UsersScore                                         #
            # ---------------------------------------------------------- #
            users_score = UsersScore(
                score_id=str(uuid.uuid4()),
                user_id=interview.user_id,
                scenario_id=interview.scenario_id,
                grammar_score=int(avg["grammar_score"]),
                politeness_score=int(avg["politeness_score"]),
                clarity_score=int(avg["fluency_score"]),
                cultural_correctness_score=int(avg["cultural_score"]),
                overall_score=int(avg["overall_score"]),
                created_at=datetime.utcnow(),
            )
            session.add(users_score)

            # Update interview overall score
            interview.overall_score = avg["overall_score"]
            interview.grammar_score = avg["grammar_score"]
            interview.flow_score = avg["fluency_score"]

            reporter_logger.info_log(
                f"Scores saved for interview={interview_id} overall={avg['overall_score']}"
            )

            # ---------------------------------------------------------- #
            #  Generate PDF                                               #
            # ---------------------------------------------------------- #
            pdf_path = self._build_pdf(
                interview_id=interview_id,
                candidate_name=candidate_name,
                scenario_name=scenario_name,
                started_at=interview.started_at,
                avg_scores=avg,
                evaluated_turns=evaluated_turns,
            )

            # Save PDF path
            interview.report_pdf_path = pdf_path
            reporter_logger.info_log(f"Report generated: {pdf_path}")

        return pdf_path

    # ------------------------------------------------------------------ #
    #  PDF builder                                                         #
    # ------------------------------------------------------------------ #

    def _build_pdf(
        self,
        interview_id: str,
        candidate_name: str,
        scenario_name: str,
        started_at: datetime,
        avg_scores: dict,
        evaluated_turns: list,
    ) -> str:
        """Format evaluated interview data and write the report PDF to disk."""
        pdf_path = str(REPORTS_DIR / f"report_{interview_id[:8]}.pdf")

        info = {
            "Candidate": candidate_name,
            "Scenario": scenario_name,
            "Interview ID": interview_id[:8] + "...",
            "Date": started_at.strftime("%Y-%m-%d") if started_at else "—",
        }

        summary_table = [
            ("Grammar", f"{avg_scores['grammar_score']} / 10"),
            ("Politeness (Keigo)", f"{avg_scores['politeness_score']} / 10"),
            ("Fluency", f"{avg_scores['fluency_score']} / 10"),
            ("Cultural Fit", f"{avg_scores['cultural_score']} / 10"),
            ("Overall", f"{avg_scores['overall_score']} / 10"),
        ]

        sections = []
        for turn in evaluated_turns:
            s = turn["scores"]
            section = {
                "heading": f"Turn {turn['turn_number']}",
                "paragraphs": [
                f"<b>Question:</b> {turn['question']}",
                    f"<b>Candidate:</b> {turn['transcript'] or '(no transcript)'}",
                ],
                "table": [
                    [
                        "Grammar",
                        f"{s.get('grammar_score', 0)}/10",
                        "Politeness",
                        f"{s.get('politeness_score', 0)}/10",
                        "Fluency",
                        f"{s.get('fluency_score', 0)}/10",
                        "Cultural",
                        f"{s.get('cultural_score', 0)}/10",
                    ]
                ],
                "col_widths": [3, 2, 3, 2, 2.5, 2, 2.5, 2],
            }
            feedback = s.get("manager_feedback", "")
            if feedback:
                section["note"] = f"Feedback: {feedback}"
            sections.append(section)

        return build_pdf_report(
            output_path=pdf_path,
            title="🌸 SakuraPath — Interview Report",
            info=info,
            summary_table=summary_table,
            sections=sections,
            footer=f"Generated by SakuraPath on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        )


def download_report(interview_id: str):
    """
    Stream the previously generated report PDF as an HTTP file response.

    Looks up the saved report path by interview ID and returns 404 if the
    interview or its PDF is missing.
    """
    db = PostgresManager.get_instance()
    try:
        with db.session_scope() as session:
            interview = (
                session.query(VoiceInterview)
                .filter(VoiceInterview.interview_id == interview_id)
                .first()
            )

            if not interview:
                raise_exception(
                    status_code=404, detail=f"Interview {interview_id} not found"
                )

            pdf_path = interview.report_pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise_exception(status_code=404, detail="Report not found")

            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=f"sakura_report_{interview_id}.pdf",
            )

    except HTTPException:
        raise
    except Exception as e:
        reporter_logger.error_log(f"Download failed: {e}")
        raise_exception(status_code=500, detail=FAILED)
