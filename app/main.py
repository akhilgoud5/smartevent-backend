from fastapi import FastAPI
from app.database import Base, engine
from app.routers import auth, events, bookings, tickets, notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartEvent API", version="1.0.0")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

@app.get("/")
def root():
    return {"message": "SmartEvent API is running"}
