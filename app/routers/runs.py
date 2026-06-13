from fastapi import APIRouter, HTTPException

from app.application.use_cases.errors import ApplicationError
from app.application.use_cases.run_node import RunNodeUseCase
from app.schemas import EstimateRunRequest, EstimateRunResponse, RunNodeRequest, RunNodeResponse

router = APIRouter(prefix="/api/runs", tags=["runs"])


def application_error(exc: ApplicationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/estimate", response_model=EstimateRunResponse)
async def estimate_run(payload: EstimateRunRequest):
    try:
        return await RunNodeUseCase().estimate(payload)
    except ApplicationError as exc:
        raise application_error(exc) from exc


@router.post("/node", response_model=RunNodeResponse)
async def run_node(payload: RunNodeRequest):
    try:
        return await RunNodeUseCase().run(payload)
    except ApplicationError as exc:
        raise application_error(exc) from exc

