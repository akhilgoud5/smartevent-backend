
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Review, Booking, Event
from app.dependencies import get_current_user

router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ReviewCreate(BaseModel):
    event_id: int
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)


@router.post("/")
def create_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    event = db.query(Event).filter(
        Event.id == data.event_id
    ).first()

    if not event:
        raise HTTPException(404, "Event not found")

    if event.event_date > datetime.utcnow():
        raise HTTPException(
            400, "Reviews are allowed only after the event"
        )

    booking = db.query(Booking).filter(
        Booking.event_id == data.event_id,
        Booking.user_id == current_user.id,
        Booking.booking_status == "CONFIRMED"
    ).first()

    if not booking:
        raise HTTPException(
            403, "You must have a confirmed booking for this event"
        )

    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.event_id == data.event_id
    ).first()

    if existing:
        raise HTTPException(
            400, "You have already reviewed this event"
        )

    review = Review(
        user_id=current_user.id,
        event_id=data.event_id,
        rating=data.rating,
        review_text=data.review_text
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "message": "Review submitted successfully",
        "review_id": review.id,
        "event_id": review.event_id,
        "rating": review.rating,
        "review_text": review.review_text
    }


@router.get("/event/{event_id}")
def get_event_reviews(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(
        Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(404, "Event not found")

    reviews = db.query(Review).filter(
        Review.event_id == event_id
    ).order_by(Review.created_at.desc()).all()

    average = db.query(
        func.avg(Review.rating)
    ).filter(
        Review.event_id == event_id
    ).scalar()

    return {
        "event_id": event_id,
        "average_rating": round(float(average), 2) if average is not None else 0,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "id": review.id,
                "user_id": review.user_id,
                "rating": review.rating,
                "review_text": review.review_text,
                "created_at": review.created_at
            }
            for review in reviews
        ]
    }


@router.put("/{review_id}")
def update_review(
    review_id: int,
    data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    if review.user_id != current_user.id:
        raise HTTPException(403, "You can edit only your own review")

    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(400, "Provide a rating or review text")

    for field, value in changes.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)

    return {
        "message": "Review updated successfully",
        "review_id": review.id,
        "rating": review.rating,
        "review_text": review.review_text
    }


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    if review.user_id != current_user.id:
        raise HTTPException(403, "You can delete only your own review")

    db.delete(review)
    db.commit()

    return {"message": "Review deleted successfully"}
