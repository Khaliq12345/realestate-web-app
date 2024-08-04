from sqlalchemy import create_engine
from app_model import Base
import config

engine = create_engine(config.db_url)
Base.metadata.create_all(bind=engine)