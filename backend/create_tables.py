from app.database.database import Base, engine

# Import every model
from app.models.user import User
from app.models.hcp import HCP
from app.models.interaction import Interaction
print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")