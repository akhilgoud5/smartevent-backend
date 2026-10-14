from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="USER", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    location = Column(String(255), nullable=False)
    event_date = Column(DateTime, nullable=False)
    ticket_price = Column(Float, nullable=False)
    banner_image = Column(String(500), nullable=True)
    total_tickets = Column(Integer, default=100)
    available_tickets = Column(Integer, default=100)
    organizer_id = Column(Integer,ForeignKey("users.id"),nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="event")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ticket_quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    booking_status = Column(String(20), default="CONFIRMED")
    created_at = Column(DateTime, default=datetime.utcnow)

    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=True)

    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    ticket = relationship("Ticket", back_populates="booking", uselist=False)



class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    ticket_code = Column(String(100), unique=True, nullable=False)
    qr_code_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    booking = relationship("Booking", back_populates="ticket")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(30), default="SYSTEM")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False,
        index=True
    )

    payment_method = Column(String, default="SIMULATED")
    payment_status = Column(String, default="PENDING")
    transaction_id = Column(String, unique=True, nullable=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    booking = relationship("Booking")

    
class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    coupon_code = Column(String, unique=True, index=True, nullable=False)
    discount_type = Column(String, nullable=False)
    discount_value = Column(Float, nullable=False)
    minimum_booking_amount = Column(Float, default=0.0)
    expiry_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    event = relationship("Event")

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    event = relationship("Event")

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint(
            "user_id", "event_id",
            name="uq_wishlist_user_event"
        ),
    )

class EventUpdate(Base):
    __tablename__ = "event_updates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
        index=True
    )
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event")
