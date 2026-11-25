"""HTTP layer: parse request -> call service -> shape response. Keep it thin."""
from fastapi import APIRouter, Depends, status

from app.schemas import TicketResponse, FeesResponse ,VehicleEntryRequest, VehicleExitRequest
from app.services.parking_service import ParkingService

router = APIRouter(prefix="/api")

# single shared instances (in-memory storage must outlive each request)

_service = ParkingService()


def get_service() -> ParkingService:
    return _service


@router.post("/entry", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(req: VehicleEntryRequest, service: ParkingService = Depends(get_service)):
    return service.create_Ticket(req).to_response()

@router.post("/exit", response_model=FeesResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(req: VehicleExitRequest, service: ParkingService = Depends(get_service)):
    return service.exit_Ticket(req).to_response()
