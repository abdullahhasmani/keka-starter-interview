import logging
import uuid
from decimal import Decimal

from app.errors import ConflictError, NotFoundError
from app.schemas import Ticket, VehicleEntryRequest, TicketResponse, FeesResponse, VehicleExitRequest

log = logging.getLogger(__name__)

Bike=["B1","B2"]
Car =["C1","C2"]
ticket = []

class ParkingService:
    def __init__(self ):
        pass
    def create_Ticket(self, req: VehicleEntryRequest):
        if req.vehicleType == "Bike":
            if len(Bike) == 0:
                return 0
            else:
                slot = Bike.pop()
                Ticket = TicketResponse(id=uuid.uuid4().hex,
                                        slot=slot,
                                        vehicle_type=req.vehicle_type,
                                        status="PARKED")
        if req.vehicleType == "Car":
            if len(Car) == 0:
                return 0
            else:
                slot = Car.pop()
                Ticket = TicketResponse(id=uuid.uuid4().hex,
                                        slot=slot,
                                        vehicle_type=req.vehicle_type,
                                        status="PARKED")

                return Ticket
    def exit_Ticket(self, req: VehicleExitRequest):

        Fees = FeesResponse(id=uuid.uuid4().hex, fees = res)
        return Fees
