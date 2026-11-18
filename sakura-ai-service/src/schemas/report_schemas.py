from pydantic import BaseModel


class GenerateReportResponse(BaseModel):
    status: str
    interview_id: str
    report_path: str
