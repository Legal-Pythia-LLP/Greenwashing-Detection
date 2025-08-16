from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.config import Base  # Base must be created beforehand

class ReportFile(Base):
    """Store report file information"""
    __tablename__ = "report_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String(64), unique=True, index=True)
    file_path = Column(String(512))
    original_filename = Column(String(256))
    upload_time = Column(DateTime, default=datetime.utcnow)
    
    reports = relationship("Report", back_populates="report_file")

class Report(Base):
    """Store analysis report results"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    company_name = Column(String(256))
    overall_score = Column(Float)
    risk_type = Column(String(128))
    analysis_time = Column(DateTime, default=datetime.utcnow)
    metrics = Column(Text)  # Store metrics data in JSON format
    analysis_summary = Column(Text)
    file_id = Column(Integer, ForeignKey("report_files.id"))
    
    report_file = relationship("ReportFile", back_populates="reports")
