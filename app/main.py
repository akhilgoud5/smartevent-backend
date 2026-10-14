
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.database import Base, engine
from app.routers import auth, events, bookings, tickets, notifications
from app.routers import payments
from app.routers import coupons
from app.routers import reviews
from app.websocket_manager import manager
from app.routers import wishlist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartEvent API", version="1.0.0")


app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
app.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"]
)
app.include_router(payments.router)
app.include_router(coupons.router)
app.include_router(reviews.router)
app.include_router(wishlist.router, prefix="/wishlist", tags=["Wishlist"])

@app.get("/")
def root():
    return {"message": "SmartEvent API is running"}


@app.websocket("/ws/events/{event_id}")
async def event_availability(websocket: WebSocket, event_id: int):
    await manager.connect(event_id, websocket)

    try:
        # Send the current ticket count immediately.
        from app.database import SessionLocal
        from app.models import Event

        db = SessionLocal()

        try:
            event = db.query(Event).filter(Event.id == event_id).first()

            if not event:
                await websocket.send_json({
                    "type": "error",
                    "message": "Event not found"
                })
                await websocket.close(code=1008)
                return

            await websocket.send_json({
                "type": "ticket_availability",
                "event_id": event_id,
                "available_tickets": event.available_tickets
            })
        finally:
            db.close()

        # Keep the connection open until the client disconnects.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(event_id, websocket)
