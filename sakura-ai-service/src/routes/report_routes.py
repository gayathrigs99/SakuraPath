from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.logger.logger import SakuraLogger
from src.service.report_service import ReportService, download_report
from src.exception.exception import raise_exception
from src.constants.constants import SUCCESS

report_api_logger = SakuraLogger("report-api-logger")
report_service = ReportService()
report_router = APIRouter(prefix="/report")

# ------------------------------------------------------------------ #
#  POST /report/{interview_id}/generate                               #
# ------------------------------------------------------------------ #


@report_router.post("/{interview_id}/generate")
def generate_report(interview_id: str):
    """
    Evaluate saved interview answers and generate the PDF report.

    Scores each transcript with the configured LLM, saves per-turn and overall
    scores to PostgreSQL, builds a PDF, and stores the PDF path on the interview.
    Returns the interview ID and server-side report path. At least one saved
    answer is required.
    """
    try:
        pdf_path = report_service.generate(interview_id)
        report_api_logger.info_log(f"Report ready:{pdf_path}")
        return JSONResponse(
            status_code=200,
            content={
                "status": SUCCESS,
                "interview_id": interview_id,
                "report_path": pdf_path,
            },
        )

    except ValueError as e:
        report_api_logger.error_log(f"Failed to generate report:{e}")
        raise_exception(status_code=404, detail=str(e))

    except Exception as e:
        report_api_logger.error_log(f"Unexpected error encountered:{str(e)}")
        raise_exception(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  GET /report/{interview_id}/download                                #
# ------------------------------------------------------------------ #


@report_router.get("/{interview_id}/download")
def report_download(interview_id: str):
    """Download the PDF previously generated for this interview."""
    return download_report(interview_id)
