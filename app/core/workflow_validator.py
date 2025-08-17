"""
Optimized workflow validation system
Coordinates and manages different validation tools, providing better error handling, parallel processing and result aggregation
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
    """Validation status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Validation result data class"""
    tool_name: str
    status: ValidationStatus
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None


class WorkflowValidator:
    """Workflow validator - coordinates and manages multiple validation tools"""
    
    def __init__(self, company_name: str, vector_store=None):
        self.company_name = company_name
        self.vector_store = vector_store
        self.results: Dict[str, ValidationResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.logger = logging.getLogger(__name__)
        
        # Initialize validation tools
        self.tools = {
            "wikirate": WikirateValidationTool(company_name),
            "news": NewsValidationTool(company_name),
            "metrics": ESGMetricsCalculatorTool(),
            "document_analysis": ESGDocumentAnalysisTool(vector_store) if vector_store else None
        }
    
    async def run_validation_workflow(self, document_analysis: str, extracted_metrics: str = None) -> Dict[str, Any]:
        """
        Run complete validation workflow
        
        Args:
            document_analysis: Document analysis results
            extracted_metrics: Extracted metrics data
            
        Returns:
            Dictionary containing all validation results
        """
        start_time = time.time()
        
        try:
            # Execute validation tasks in parallel
            tasks = [
                self._validate_wikirate(extracted_metrics),
                self._validate_news(document_analysis),
                self._calculate_metrics(document_analysis),
                self._analyze_document(document_analysis)
            ]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
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
        """Wikirate validation"""
        start_time = time.time()
        
        try:
            if not extracted_metrics:
                # If no metrics provided, extract from document analysis
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
        """News validation"""
        start_time = time.time()
        
        try:
            # Extract claims that need validation
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
        """Calculate metrics"""
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
        """Document analysis"""
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
            
            # Generate analysis query
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
        """Run tool function asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, tool_func, *args)
    
    async def _extract_metrics_from_analysis(self) -> str:
        """Extract metrics from document analysis"""
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
        """Extract claims from document analysis"""
        prompt = f"""
        Extract the key ESG claims and statements from the following analysis:

        Analysis: {document_analysis}

        List the main claims that should be validated against news sources.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    async def _generate_analysis_query(self, document_analysis: str) -> str:
        """Generate document analysis query"""
        prompt = f"""
        Based on the following document analysis, generate a focused query for greenwashing detection:

        Analysis: {document_analysis}

        Create a specific query that will help identify potential greenwashing indicators.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def _process_workflow_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Process workflow results"""
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
        
        # Generate summary
        processed_results["summary"] = self._generate_summary(processed_results["results"])
        
        return processed_results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary"""
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
        
        # Generate key findings
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            summary["key_findings"].append("Wikirate data validation completed")
        
        if "news" in results and results["news"]["status"] == "completed":
            summary["key_findings"].append("News validation completed")
        
        if "metrics" in results and results["metrics"]["status"] == "completed":
            summary["key_findings"].append("Greenwashing metrics calculated")
        
        # Generate recommendations
        if summary["failed_tools"] > 0:
            summary["recommendations"].append("Some validation tools failed - consider manual review")
        
        if summary["successful_tools"] >= 2:
            summary["recommendations"].append("Multiple validation sources available for comprehensive analysis")
        
        return summary


class ValidationOrchestrator:
    """Validation orchestrator - advanced workflow management"""
    
    def __init__(self, company_name: str, vector_store=None):
        self.validator = WorkflowValidator(company_name, vector_store)
        self.logger = logging.getLogger(__name__)
    
    async def run_comprehensive_validation(self, document_analysis: str, extracted_metrics: str = None) -> Dict[str, Any]:
        """Run comprehensive validation"""
        try:
            # Run basic validation
            workflow_results = await self.validator.run_validation_workflow(
                document_analysis, extracted_metrics
            )
            
            # Add advanced analysis
            enhanced_results = await self._enhance_results(workflow_results, document_analysis)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Comprehensive validation failed: {str(e)}")
            return {
                "error": f"Comprehensive validation failed: {str(e)}",
                "workflow_results": workflow_results if 'workflow_results' in locals() else None
            }
    
    async def _enhance_results(self, workflow_results: Dict[str, Any], document_analysis: str) -> Dict[str, Any]:
        """Enhance validation results"""
        enhanced_results = workflow_results.copy()
        
        # Add confidence score
        enhanced_results["confidence_score"] = await self._calculate_confidence_score(workflow_results)
        
        # Add risk rating
        enhanced_results["risk_rating"] = await self._calculate_risk_rating(workflow_results)
        
        # Add recommendations
        enhanced_results["recommendations"] = await self._generate_recommendations(workflow_results)
        
        return enhanced_results
    
    async def _calculate_confidence_score(self, workflow_results: Dict[str, Any]) -> float:
        """Calculate confidence score"""
        successful_tools = workflow_results["summary"]["successful_tools"]
        total_tools = workflow_results["summary"]["total_tools"]
        
        if total_tools == 0:
            return 0.0
        
        base_score = (successful_tools / total_tools) * 100
        
        # Adjust score based on tool type
        results = workflow_results["results"]
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            base_score += 10  # Wikirate validation is important
        if "news" in results and results["news"]["status"] == "completed":
            base_score += 5   # News validation provides additional support
        
        return min(base_score, 100.0)
    
    async def _calculate_risk_rating(self, workflow_results: Dict[str, Any]) -> str:
        """Calculate risk rating"""
        results = workflow_results["results"]
        
        # Check key validation results
        risk_factors = 0
        
        if "wikirate" in results and results["wikirate"]["status"] == "completed":
            # Analyze risk indicators in Wikirate results
            wikirate_result = results["wikirate"]["result"]
            if "verification_score" in str(wikirate_result):
                # More complex risk analysis logic can be added here
                pass
        
        if "metrics" in results and results["metrics"]["status"] == "completed":
            # Analyze metrics calculation results
            metrics_result = results["metrics"]["result"]
            if "overall_greenwashing_score" in str(metrics_result):
                # More complex risk analysis logic can be added here
                pass
        
        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _generate_recommendations(self, workflow_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        results = workflow_results["results"]
        
        # Generate recommendations based on validation results
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
        
        # Generate recommendations based on overall results
        if workflow_results["summary"]["failed_tools"] > 0:
            recommendations.append("Some validation tools failed - consider running individual validations")
        
        if workflow_results["summary"]["successful_tools"] >= 3:
            recommendations.append("Multiple validation sources available - comprehensive analysis possible")
        
        return recommendations


async def run_optimized_validation_workflow(
    company_name: str, 
    document_analysis: str, 
    vector_store=None,
    extracted_metrics: str = None
) -> Dict[str, Any]:
    """
    Run optimized validation workflow
    
    Args:
        company_name: Company name
        document_analysis: Document analysis results  
        vector_store: Vector store
        extracted_metrics: Extracted metrics data
        
    Returns:
        Dictionary containing all validation results
    """
    orchestrator = ValidationOrchestrator(company_name, vector_store)
    return await orchestrator.run_comprehensive_validation(document_analysis, extracted_metrics)
