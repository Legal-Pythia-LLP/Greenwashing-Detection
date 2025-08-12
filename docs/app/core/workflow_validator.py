"""
优化的工作流验证系统
用于协调和管理不同的验证工具，提供更好的错误处理、并行处理和结果聚合
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import time

from app.core.tools import (
    WikirateValidationTool, 
    NewsValidationTool, 
    ESGMetricsCalculatorTool,
    ESGDocumentAnalysisTool
)
from app.core.llm import llm
from langchain.schema import HumanMessage


class ValidationStatus(Enum):
    """验证状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """验证结果数据类"""
    tool_name: str
    status: ValidationStatus
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None


class WorkflowValidator:
    """工作流验证器 - 协调和管理多个验证工具"""
    
    def __init__(self, company_name: str, vector_store=None):
        self.company_name = company_name
        self.vector_store = vector_store
        self.results: Dict[str, ValidationResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.logger = logging.getLogger(__name__)
        
        # 初始化验证工具
        self.tools = {
            "wikirate": WikirateValidationTool(company_name),
            "news": NewsValidationTool(company_name),
            "metrics": ESGMetricsCalculatorTool(),
            "document_analysis": ESGDocumentAnalysisTool(vector_store) if vector_store else None
        }
    
    async def run_validation_workflow(self, document_analysis: str, extracted_metrics: str = None) -> Dict[str, Any]:
        """
        运行完整的验证工作流
        
        Args:
            document_analysis: 文档分析结果
            extracted_metrics: 提取的指标数据
            
        Returns:
            包含所有验证结果的字典
        """
        start_time = time.time()
        
        try:
            # 并行执行验证任务
            tasks = [
                self._validate_wikirate(extracted_metrics),
                self._validate_news(document_analysis),
                self._calculate_metrics(document_analysis),
                self._analyze_document(document_analysis)
            ]
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            workflow_result = self._process_workflow_results(results)
            workflow_result["execution_time"] = time.time() - start_time
            
            return workflow_result
            
        except Exception as e:
            self.logger.error(f"Workflow validation failed: {str(e)}")
            return {
                "error": f"Workflow validation failed: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    async def _validate_wikirate(self, extracted_metrics: str = None) -> ValidationResult:
        """Wikirate验证"""
        start_time = time.time()
        
        try:
            if not extracted_metrics:
                # 如果没有提供指标，从文档分析中提取
                extracted_metrics = await self._extract_metrics_from_analysis()
            
            result = await self._run_tool_async(
                self.tools["wikirate"]._run, 
                extracted_metrics
            )
            
            return ValidationResult(
                tool_name="wikirate",
                status=ValidationStatus.COMPLETED,
                result=result,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                tool_name="wikirate",
                status=ValidationStatus.FAILED,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _validate_news(self, document_analysis: str) -> ValidationResult:
        """新闻验证"""
        start_time = time.time()
        
        try:
            # 提取需要验证的声明
            claims = await self._extract_claims_from_analysis(document_analysis)
            
            result = await self._run_tool_async(
                self.tools["news"]._run,
                claims
            )
            
            return ValidationResult(
                tool_name="news",
                status=ValidationStatus.COMPLETED,
                result=result,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                tool_name="news",
                status=ValidationStatus.FAILED,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _calculate_metrics(self, document_analysis: str) -> ValidationResult:
        """计算指标"""
        start_time = time.time()
        
        try:
            result = await self._run_tool_async(
                self.tools["metrics"]._run,
                document_analysis
            )
            
            return ValidationResult(
                tool_name="metrics",
                status=ValidationStatus.COMPLETED,
                result=result,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                tool_name="metrics",
                status=ValidationStatus.FAILED,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _analyze_document(self, document_analysis: str) -> ValidationResult:
        """文档分析"""
        start_time = time.time()
        
        try:
            if not self.tools["document_analysis"]:
                return ValidationResult(
                    tool_name="document_analysis",
                    status=ValidationStatus.SKIPPED,
                    result=None,
                    error="Vector store not available",
                    execution_time=time.time() - start_time
                )
            
            # 生成分析查询
            analysis_query = await self._generate_analysis_query(document_analysis)
            
            result = await self._run_tool_async(
                self.tools["document_analysis"]._run,
                analysis_query
            )
            
            return ValidationResult(
                tool_name="document_analysis",
                status=ValidationStatus.COMPLETED,
                result=result,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ValidationResult(
                tool_name="document_analysis",
                status=ValidationStatus.FAILED,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _run_tool_async(self, tool_func, *args):
        """异步运行工具函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, tool_func, *args)
    
    async def _extract_metrics_from_analysis(self) -> str:
        """从文档分析中提取指标"""
        prompt = f"""
        Extract specific numerical ESG metrics and values from the following analysis:

        Analysis: {self.company_name}

        Focus on extracting:
        - Scope 1, 2, 3 emissions (in tonnes CO2e)
        - Energy consumption data
        - Water usage metrics
        - Waste generation figures
        - Any other quantifiable ESG metrics

        Include the reported values, units, and time periods.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _extract_claims_from_analysis(self, document_analysis: str) -> str:
        """从文档分析中提取声明"""
        prompt = f"""
        Extract the key ESG claims and statements from the following analysis:

        Analysis: {document_analysis}

        List the main claims that should be validated against news sources.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _generate_analysis_query(self, document_analysis: str) -> str:
        """生成文档分析查询"""
        prompt = f"""
        Based on the following document analysis, generate a focused query for greenwashing detection:

        Analysis: {document_analysis}

        Create a specific query that will help identify potential greenwashing indicators.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def _process_workflow_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """处理工作流结果"""
        processed_results = {
            "overall_status": "completed",
            "successful_validations": 0,
            "failed_validations": 0,
            "total_execution_time": 0.0,
            "results": {},
            "summary": {}
        }
        
        for result in results:
            if isinstance(result, Exception):
                processed_results["results"]["error"] = {
                    "status": "failed",
                    "error": str(result)
                }
                processed_results["failed_validations"] += 1
            else:
                processed_results["results"][result.tool_name] = {
                    "status": result.status.value,
                    "result": result.result,
                    "error": result.error,
                    "execution_time": result.execution_time
                }
                
                if result.status == ValidationStatus.COMPLETED:
                    processed_results["successful_validations"] += 1
                elif result.status == ValidationStatus.FAILED:
                    processed_results["failed_validations"] += 1
                
                processed_results["total_execution_time"] += result.execution_time
        
        # 生成摘要
        processed_results["summary"] = self._generate_summary(processed_results["results"])
        
        return processed_results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成验证摘要"""
        summary = {
            "total_tools": len(results),
            "successful_tools": 0,
            "failed_tools": 0,
            "skipped_tools": 0,
            "key_findings": [],
            "recommendations": []
        }
        
        for tool_name, result in results.items():
            if result["status"] == "completed":
                summary["successful_tools"] += 1
            elif result["status"] == "failed":
                summary["failed_tools"] += 1
            elif result["status"] == "skipped":
                summary["skipped_tools"] += 1
        
        # 生成关键发现
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            summary["key_findings"].append("Wikirate data validation completed")
        
        if "news" in results and results["news"]["status"] == "completed":
            summary["key_findings"].append("News validation completed")
        
        if "metrics" in results and results["metrics"]["status"] == "completed":
            summary["key_findings"].append("Greenwashing metrics calculated")
        
        # 生成建议
        if summary["failed_tools"] > 0:
            summary["recommendations"].append("Some validation tools failed - consider manual review")
        
        if summary["successful_tools"] >= 2:
            summary["recommendations"].append("Multiple validation sources available for comprehensive analysis")
        
        return summary


class ValidationOrchestrator:
    """验证编排器 - 高级工作流管理"""
    
    def __init__(self, company_name: str, vector_store=None):
        self.validator = WorkflowValidator(company_name, vector_store)
        self.logger = logging.getLogger(__name__)
    
    async def run_comprehensive_validation(self, document_analysis: str, extracted_metrics: str = None) -> Dict[str, Any]:
        """运行综合验证"""
        try:
            # 运行基础验证
            workflow_results = await self.validator.run_validation_workflow(
                document_analysis, extracted_metrics
            )
            
            # 添加高级分析
            enhanced_results = await self._enhance_results(workflow_results, document_analysis)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Comprehensive validation failed: {str(e)}")
            return {
                "error": f"Comprehensive validation failed: {str(e)}",
                "workflow_results": workflow_results if 'workflow_results' in locals() else None
            }
    
    async def _enhance_results(self, workflow_results: Dict[str, Any], document_analysis: str) -> Dict[str, Any]:
        """增强验证结果"""
        enhanced_results = workflow_results.copy()
        
        # 添加置信度评分
        enhanced_results["confidence_score"] = await self._calculate_confidence_score(workflow_results)
        
        # 添加风险评级
        enhanced_results["risk_rating"] = await self._calculate_risk_rating(workflow_results)
        
        # 添加建议
        enhanced_results["recommendations"] = await self._generate_recommendations(workflow_results)
        
        return enhanced_results
    
    async def _calculate_confidence_score(self, workflow_results: Dict[str, Any]) -> float:
        """计算置信度评分"""
        successful_tools = workflow_results["summary"]["successful_tools"]
        total_tools = workflow_results["summary"]["total_tools"]
        
        if total_tools == 0:
            return 0.0
        
        base_score = (successful_tools / total_tools) * 100
        
        # 根据工具类型调整评分
        results = workflow_results["results"]
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            base_score += 10  # Wikirate验证很重要
        if "news" in results and results["news"]["status"] == "completed":
            base_score += 5   # 新闻验证提供额外支持
        
        return min(base_score, 100.0)
    
    async def _calculate_risk_rating(self, workflow_results: Dict[str, Any]) -> str:
        """计算风险评级"""
        results = workflow_results["results"]
        
        # 检查关键验证结果
        risk_factors = 0
        
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            # 分析Wikirate结果中的风险指标
            wikirate_result = results["wikirate"]["result"]
            if "verification_score" in str(wikirate_result):
                # 这里可以添加更复杂的风险分析逻辑
                pass
        
        if "metrics" in results and results["metrics"]["status"] == "completed":
            # 分析指标计算结果
            metrics_result = results["metrics"]["result"]
            if "overall_greenwashing_score" in str(metrics_result):
                # 这里可以添加更复杂的风险分析逻辑
                pass
        
        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _generate_recommendations(self, workflow_results: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []
        results = workflow_results["results"]
        
        # 基于验证结果生成建议
        if "wikirate" in results:
            if results["wikirate"]["status"] == "failed":
                recommendations.append("Wikirate validation failed - consider manual data verification")
            elif results["wikirate"]["status"] == "completed":
                recommendations.append("Wikirate data validation completed successfully")
        
        if "news" in results:
            if results["news"]["status"] == "failed":
                recommendations.append("News validation failed - consider manual news review")
            elif results["news"]["status"] == "completed":
                recommendations.append("News validation completed successfully")
        
        if "metrics" in results and results["metrics"]["status"] == "completed":
            recommendations.append("Greenwashing metrics calculated - review detailed scores")
        
        # 基于整体结果生成建议
        if workflow_results["summary"]["failed_tools"] > 0:
            recommendations.append("Some validation tools failed - consider running individual validations")
        
        if workflow_results["summary"]["successful_tools"] >= 3:
            recommendations.append("Multiple validation sources available - comprehensive analysis possible")
        
        return recommendations


# 使用示例
async def run_optimized_validation_workflow(
    company_name: str, 
    document_analysis: str, 
    vector_store=None,
    extracted_metrics: str = None
) -> Dict[str, Any]:
    """
    运行优化的验证工作流
    
    Args:
        company_name: 公司名称
        document_analysis: 文档分析结果
        vector_store: 向量存储
        extracted_metrics: 提取的指标数据
        
    Returns:
        包含所有验证结果的字典
    """
    orchestrator = ValidationOrchestrator(company_name, vector_store)
    return await orchestrator.run_comprehensive_validation(document_analysis, extracted_metrics) 