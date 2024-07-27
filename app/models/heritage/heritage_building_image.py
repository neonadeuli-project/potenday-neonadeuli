from sqlalchemy import (
    Column, 
    Integer, 
    ForeignKey, 
    String, 
    DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class HeritageBuildingImage(Base):
    __tablename__ = 'heritage_building_images'
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("heritage_buildings.id"))
    image_url = Column(String(255))
    description = Column(String(255))
    alt_text = Column(String(100))
    order = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    buildings = relationship("HeritageBuilding", back_populates="images")