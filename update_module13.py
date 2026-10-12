
from sqlalchemy import inspect, text
from app.database import engine
from app import models

inspector = inspect(engine)

# Create the coupons table if it doesn't exist
models.Coupon.__table__.create(bind=engine, checkfirst=True)

# Read existing booking columns
columns = {
    column["name"]
    for column in inspect(engine).get_columns("bookings")
}

with engine.begin() as connection:
    if "coupon_id" not in columns:
        connection.execute(text(
            "ALTER TABLE bookings ADD COLUMN coupon_id INTEGER"
        ))

    if "discount_amount" not in columns:
        connection.execute(text(
            "ALTER TABLE bookings ADD COLUMN discount_amount FLOAT DEFAULT 0"
        ))

    if "final_amount" not in columns:
        connection.execute(text(
            "ALTER TABLE bookings ADD COLUMN final_amount FLOAT"
        ))

print("Module 13 database update completed!")
