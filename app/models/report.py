from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.config import Base  # 需要先创建Base

class ReportFile(Base):
    """存储报告文件信息"""
    __tablename__ = "report_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String(64), unique=True, index=True)
    file_path = Column(String(512))
    original_filename = Column(String(256))
    upload_time = Column(DateTime, default=datetime.utcnow)
    
    reports = relationship("Report", back_populates="report_file")

class Report(Base):
    """存储分析报告结果"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    company_name = Column(String(256))
    overall_score = Column(Float)
    risk_type = Column(String(128))
    analysis_time = Column(DateTime, default=datetime.utcnow)
    metrics = Column(Text)  # 存储JSON格式的指标数据
    analysis_summary = Column(Text)
    file_id = Column(Integer, ForeignKey("report_files.id"))
    
    report_file = relationship("ReportFile", back_populates="reports")
