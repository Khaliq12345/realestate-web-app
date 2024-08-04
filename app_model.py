from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import String, Text
from sqlalchemy import JSON

class Base(DeclarativeBase):
    pass

class Tbl_Property(Base):
    __tablename__ = "property_2"
    
    p_id = mapped_column(Text, primary_key=True)
    address = mapped_column(Text, nullable=True)
    first_name = mapped_column(Text, nullable=True)
    last_name = mapped_column(Text, nullable=True)
    property_type = mapped_column(Text, nullable=True)
    pre_foreclosure = mapped_column(Text, nullable=True)
    vacant = mapped_column(Text, nullable=True)
    owner_occupied = mapped_column(Text, nullable=True)
    other_info = mapped_column(JSON)
    
    def __repr__(self) -> str:
        return f"Property(id={self.p_id}, firstname={self.first_name}, lastname={self.last_name})"
    