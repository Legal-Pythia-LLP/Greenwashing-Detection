from typing import Dict, Any, List
import time
import json
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.report import Report
from app.config import Base
from fastapi import Depends

# 数据库依赖
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# 风险趋势数据
risk_trends = [
    {"date": "2025-01-01", "risks": 5, "new_risks": 2},
    {"date": "2025-01-08", "risks": 7, "new_risks": 3},
    {"date": "2025-01-15", "risks": 6, "new_risks": 1},
    {"date": "2025-01-22", "risks": 9, "new_risks": 4},
    {"date": "2025-01-29", "risks": 12, "new_risks": 5},
    {"date": "2025-02-05", "risks": 15, "new_risks": 6},
]

# 获取所有公司报告列表
def get_all_companies(db: Session = Depends(get_db_session)) -> List[Dict[str, Any]]:
    """获取所有公司及其最新分析报告"""
    # 查询每个公司的最新报告
    subquery = db.query(
        Report.company_name,
        Report.session_id,
        Report.overall_score,
        Report.risk_type,
        Report.analysis_time,
        Report.file_id
    ).order_by(
        Report.company_name,
        Report.analysis_time.desc()
    ).subquery()

    result = db.query(subquery).distinct(
        subquery.c.company_name
    ).all()

    companies = []
    for row in result:
        companies.append({
            "id": row.session_id,
            "name": row.company_name,
            "score": int(row.overall_score),
            "type": row.risk_type,
            "date": _format_date(row.analysis_time.timestamp()) if row.analysis_time else "2025-01-01",
            "session_count": db.query(Report).filter(
                Report.company_name == row.company_name
            ).count()
        })
    
    # 按风险评分排序
    return sorted(companies, key=lambda x: x["score"], reverse=True)

def _get_main_risk_type(report: Dict[str, Any]) -> str:
    """从报告中提取主要风险类型"""
    breakdown = report.get("breakdown", [])
    if not breakdown:
        return "未知类型"
    
    # 找到评分最高的类型
    max_score = 0
    main_type = "未知类型"
    for item in breakdown:
        score = item.get("value", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
        if score > max_score:
            max_score = score
            main_type = item.get("type", "未知类型")
    
    return main_type

def _format_date(timestamp: float) -> str:
    """格式化时间戳为日期字符串"""
    try:
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d")
    except:
        return "2025-01-01"

def update_dashboard_stats():
    """更新仪表盘统计数据"""
    global dashboard_stats
    
    # 计算高风险公司数量 (评分 >= 70)
    high_risk_count = 0
    pending_count = len(analysis_results_by_session)
    
    for session_data in analysis_results_by_session.values():
        score = session_data.get("overall_score", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
        if score >= 70:
            high_risk_count += 1
    
    dashboard_stats.update({
        "high_risk_companies": high_risk_count,
        "pending_reports": pending_count,
        "high_priority_reports": max(9, high_risk_count // 3),
        "last_updated": time.time()
    })

def store_analysis_result(session_id: str, company_name: str, data: Dict[str, Any]):
    """存储分析结果并更新索引"""
    # 添加时间戳
    data["created_at"] = time.time()
    data["company_name"] = company_name
    
    # 存储分析结果
    analysis_results_by_session[session_id] = data
    
    # 更新公司索引
    if company_name not in company_reports_index:
        company_reports_index[company_name] = []
    if session_id not in company_reports_index[company_name]:
        company_reports_index[company_name].append(session_id)
    
    # 更新仪表盘统计
    update_dashboard_stats()
