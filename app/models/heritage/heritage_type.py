from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Float, 
    Enum
)
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum

from app.models.enums import ElementType


# class ElementType(enum.Enum):
#     PALACE="궁궐"
#     TEMPLE="사찰"
#     TOMB="고분"
#     HISTORIC_SITE="유적지"
#     FORTRESS="성곽"
#     OTHER="기타"

class HeritageType(Base):
    __tablename__ = 'heritage_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    element_type = Column(Enum(ElementType))
    default_radius = Column(Float)

    heritages = relationship("Heritage", back_populates="heritage_types")
    buildings = relationship("HeritageBuilding", back_populates="building_types")