
from app.database import Base, engine
from app import models

models.Review.__table__.create(
    bind=engine,
    checkfirst=True
)

print("Module 14 reviews table is ready!")
