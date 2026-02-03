"""
SQLAlchemy models for the View Changer App.

Tables:
- patient_columns: Master list of all available columns from the patient database
- view_columns: Configuration for which columns appear in a specific view
"""

from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///app.db", echo=False)
SessionLocal = sessionmaker(bind=engine)


class PatientColumn(Base):
    """
    Master list of all available columns from the patient database.
    These are the columns that can be added to a view.
    """
    __tablename__ = "patient_columns"
    
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, nullable=False)
    column_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "data_type": self.data_type,
            "label": self.label
        }


class ViewColumn(Base):
    """
    Configuration for which columns appear in a specific view.
    Includes display properties like order, width, and alignment.
    """
    __tablename__ = "view_columns"
    
    id = Column(Integer, primary_key=True, index=True)
    view_name = Column(String, nullable=False, default="vwTitanium_WLAdmin")
    table_name = Column(String, nullable=True)
    column_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    grid_order = Column(Integer, nullable=False, default=0)
    grid_width = Column(String, nullable=False, default="100px")
    is_right_aligned = Column(Boolean, nullable=False, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "view_name": self.view_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "data_type": self.data_type,
            "label": self.label,
            "grid_order": self.grid_order,
            "grid_width": self.grid_width,
            "is_right_aligned": self.is_right_aligned
        }



class Patient(Base):
    """
    Patient data table.
    """
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    firstName = Column(String, nullable=True)
    lastName = Column(String, nullable=True)
    dtBirth = Column(String, nullable=True) # YYYY-MM-DD
    
    # Common view fields
    Waitlist = Column(String, default="General")
    Priority = Column(String, default="Routine")
    Status = Column(String, default="Active")
    DaysWaiting = Column(Integer, default=0)
    
    def to_dict(self):
        return {
            "id": self.id,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "dtBirth": self.dtBirth,
            "Waitlist": self.Waitlist,
            "Priority": self.Priority,
            "Status": self.Status,
            "DaysWaiting": self.DaysWaiting
        }


# Create tables
Base.metadata.create_all(bind=engine)
