from typing import Dict, Any, List
from app.core.tools import ESGDocumentAnalysisTool, NewsValidationTool, ESGMetricsCalculatorTool, WikirateValidationTool
from app.core.llm import llm, climatebert_tokenizer, climatebert_model
from app.config import VALID_COMPANIES
from app.models import ESGAnalysisState
from langchain.schema import HumanMessage
from langchain_community.vectorstores import Chroma
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import Tool
import json
import torch
from app.core.utils import is_esg_related
from app.core.company import extract_company_info

# Global storage for document stores and agents
document_stores: Dict[str, Chroma] = {}
agent_executors: Dict[str, AgentExecutor] = {}
memories: Dict[str, ConversationBufferWindowMemory] = {}


# LangGraph Node Functions
def generate_initial_thoughts(state: ESGAnalysisState) -> ESGAnalysisState:
    """Generate multiple analytical thoughts for ESG analysis"""
    
    thought_generation_prompt = """
    You are an expert ESG analyst tasked with identifying greenwashing in corporate reports.
    Generate 4 different analytical approaches to examine this ESG document for greenwashing indicators.
    
    Each approach should focus on a different aspect:
    1. Quantitative analysis of specific metrics and targets
    2. Qualitative analysis of language and claims
    3. Comparative analysis against industry standards
    4. Temporal analysis of commitments vs. achievements
    
    For each approach, provide:
    - A specific analytical question to investigate
    - The methodology to use
    - What evidence to look for
    - Potential red flags to identify
    
    Format your response as a JSON list of 4 analytical approaches.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=thought_generation_prompt)])
        thoughts_text = response.content
        
        # Try to parse as JSON, fallback to splitting if needed
        try:
            thoughts = json.loads(thoughts_text)
            if isinstance(thoughts, list):
                state["initial_thoughts"] = thoughts
            else:
                # Fallback: split by numbered items
                state["initial_thoughts"] = thoughts_text.split('\n\n')
        except json.JSONDecodeError:
            # Fallback: split by numbered items
            state["initial_thoughts"] = thoughts_text.split('\n\n')
            
        return state
        
    except Exception as e:
        state["error"] = f"Error generating thoughts: {str(e)}"
        return state

def evaluate_and_select_thoughts(state: ESGAnalysisState) -> ESGAnalysisState:
    """Evaluate the quality of generated thoughts and select the best ones"""
    
    if state.get("error"):
        return state
        
    thoughts = state.get("initial_thoughts", [])
    
    evaluation_prompt = f"""
    Evaluate the following analytical approaches for ESG greenwashing analysis:
    
    Approaches: {thoughts}
    
    Rate each approach based on:
    1. Specificity of methodology
    2. Likelihood of finding evidence
    3. Comprehensiveness of analysis
    4. Practical applicability
    
    Select the top 3 approaches and explain why they are most suitable.
    Return the selected approaches as a JSON list.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=evaluation_prompt)])
        evaluation_text = response.content
        
        # Try to extract selected thoughts
        try:
            selected = json.loads(evaluation_text)
            if isinstance(selected, list):
                state["selected_thoughts"] = selected
            else:
                # Fallback: use first 3 thoughts
                state["selected_thoughts"] = thoughts[:3]
        except json.JSONDecodeError:
            # Fallback: use first 3 thoughts
            state["selected_thoughts"] = thoughts[:3]
            
        return state
        
    except Exception as e:
        state["error"] = f"Error evaluating thoughts: {str(e)}"
        return state

def perform_document_analysis(state: ESGAnalysisState) -> ESGAnalysisState:
    """Perform detailed document analysis using selected thoughts"""
    
    if state.get("error"):
        return state
        
    vector_store = state.get("vector_store")
    selected_thoughts = state.get("selected_thoughts", [])
    
    if not vector_store:
        state["error"] = "No vector store available for analysis"
        return state
    
    try:
        # Create analysis tool
        analysis_tool = ESGDocumentAnalysisTool(vector_store)
        
        # Perform analysis based on selected thoughts
        analysis_results = []
        
        for thought in selected_thoughts:
            query = f"Analyze the document using this approach: {thought}"
            result = analysis_tool._run(query)
            analysis_results.append(result)
        
        # Combine results
        combined_analysis = "\n\n=== ANALYSIS APPROACH ===\n\n".join(analysis_results)
        state["document_analysis"] = combined_analysis
        
        return state
        
    except Exception as e:
        state["error"] = f"Error in document analysis: {str(e)}"
        return state

def validate_with_news(state: ESGAnalysisState) -> ESGAnalysisState:
    """Validate findings against news sources"""
    
    if state.get("error"):
        return state
        
    company_name = state.get("company_name", "")
    document_analysis = state.get("document_analysis", "")
    
    if not company_name or company_name.lower() not in VALID_COMPANIES:
        state["news_validation"] = "Company name not recognized in valid companies list. News validation skipped."
        return state
    
    try:
        # Create news validation tool
        news_tool = NewsValidationTool(company_name)
        
        # Extract key claims from document analysis
        claims_extraction_prompt = f"""
        Extract the key ESG claims and statements from the following analysis:
        
        Analysis: {document_analysis}
        
        List the main claims that should be validated against news sources.
        """
        
        claims_response = llm.invoke([HumanMessage(content=claims_extraction_prompt)])
        claims = claims_response.content
        
        # Validate claims
        validation_result = news_tool._run(claims)
        state["news_validation"] = validation_result
        
        return state
        
    except Exception as e:
        state["error"] = f"Error in news validation: {str(e)}"
        return state


def validate_with_wikirate(state: ESGAnalysisState) -> ESGAnalysisState:
    """新增：使用Wikirate数据库验证ESG指标"""

    if state.get("error"):
        return state

    company_name = state.get("company_name", "")
    document_analysis = state.get("document_analysis", "")

    if not company_name:
        state["wikirate_validation"] = "No company name provided for Wikirate validation."
        return state

    try:
        wikirate_tool = WikirateValidationTool(company_name)

        # 提取文档中的ESG指标
        metrics_extraction_prompt = f"""
        Extract specific numerical ESG metrics and values from the following analysis:

        Analysis: {document_analysis}

        Focus on extracting:
        - Scope 1, 2, 3 emissions (in tonnes CO2e)
        - Energy consumption data
        - Water usage metrics
        - Waste generation figures
        - Any other quantifiable ESG metrics

        Include the reported values, units, and time periods.
        """

        metrics_response = llm.invoke([HumanMessage(content=metrics_extraction_prompt)])
        extracted_metrics = metrics_response.content

        # 使用Wikirate验证
        validation_result = wikirate_tool._run(extracted_metrics)
        state["wikirate_validation"] = validation_result

        return state

    except Exception as e:
        state["error"] = f"Error in Wikirate validation: {str(e)}"
        return state


def calculate_metrics(state: ESGAnalysisState) -> ESGAnalysisState:
    """Calculate quantitative greenwashing metrics"""
    
    if state.get("error"):
        return state
        
    document_analysis = state.get("document_analysis", "")
    news_validation = state.get("news_validation", "")
    
    combined_analysis = f"""
    Document Analysis: {document_analysis}
    
    News Validation: {news_validation}
    """
    
    try:
        # Create metrics calculator
        metrics_tool = ESGMetricsCalculatorTool()
        
        # Calculate metrics
        metrics_result = metrics_tool._run(combined_analysis)
        state["metrics"] = metrics_result
        
        return state
        
    except Exception as e:
        state["error"] = f"Error calculating metrics: {str(e)}"
        return state

def synthesize_final_report(state: ESGAnalysisState) -> ESGAnalysisState:
    """Create final comprehensive report"""
    
    if state.get("error"):
        return state
        
    document_analysis = state.get("document_analysis", "")
    news_validation = state.get("news_validation", "")
    metrics = state.get("metrics", "")
    
    synthesis_prompt = f"""
    Create a comprehensive final ESG greenwashing assessment report that synthesizes all findings:
    
    Document Analysis: {document_analysis}
    
    News Validation: {news_validation}
    
    Metrics: {metrics}
    
    Your report should include:
    1. Executive Summary with overall greenwashing score (0-10)
    2. Key findings and evidence
    3. News validation results and their implications
    4. Specific recommendations for stakeholders
    5. Risk assessment and concferns
    6. Areas requiring further investigation
    
    Provide a professional, detailed report suitable for executive review.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=synthesis_prompt)])
        state["final_synthesis"] = response.content
        
        return state
        
    except Exception as e:
        state["error"] = f"Error in final synthesis: {str(e)}"
        return state

def check_completion(state: ESGAnalysisState) -> str:
    """Check if analysis is complete or needs iteration"""
    
    if state.get("error"):
        return "error"
        
    if state.get("final_synthesis"):
        return "complete"
    
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if iteration >= max_iterations:
        return "complete"
    
    return "continue"

# Create LangGraph workflow
def create_esg_analysis_graph():
    """Create the ESG analysis workflow using LangGraph"""
    
    # Initialize the graph
    from langgraph.graph import StateGraph, END
    workflow = StateGraph(ESGAnalysisState)
    
    # Add nodes
    workflow.add_node("generate_thoughts", generate_initial_thoughts)
    workflow.add_node("evaluate_thoughts", evaluate_and_select_thoughts)
    workflow.add_node("document_analysis", perform_document_analysis)
    workflow.add_node("news_validation", validate_with_news)
    workflow.add_node("wikirate_validation", validate_with_wikirate)  # 新增节点
    workflow.add_node("calculate_metrics", calculate_metrics)
    workflow.add_node("final_synthesis", synthesize_final_report)
    
    # Add edges
    workflow.add_edge("generate_thoughts", "evaluate_thoughts")
    workflow.add_edge("evaluate_thoughts", "document_analysis")
    workflow.add_edge("document_analysis", "news_validation")
    workflow.add_edge("news_validation", "wikirate_validation")  # 新增边
    workflow.add_edge("wikirate_validation", "calculate_metrics")
    workflow.add_edge("calculate_metrics", "final_synthesis")
    
    # Set entry point
    workflow.set_entry_point("generate_thoughts")
    
    # Add conditional edges for completion check
    workflow.add_conditional_edges(
        "final_synthesis",
        check_completion,
        {
            "complete": END,
            "error": END,
            "continue": "generate_thoughts"
        }
    )
    
    return workflow.compile()

# Agent creation function
def create_esg_agent(session_id: str, vector_store: Chroma, company_name: str) -> AgentExecutor:
    """Create a ReAct agent for ESG analysis"""
    
    from langchain.agents import initialize_agent
    from langchain.agents.agent_types import AgentType
    
    # Create tools
    tools = [
        ESGDocumentAnalysisTool(vector_store),
        NewsValidationTool(company_name),
        WikirateValidationTool(company_name),
        ESGMetricsCalculatorTool(),
        Tool(
            name="company_info_extractor",
            description="Extracts company information from documents",
            func=lambda query: extract_company_info(query, vector_store)
        ),
        Tool(
            name="esg_classifier",
            description="Classifies text as ESG-related or not using ClimateBERT",
            func=lambda text: str(is_esg_related(text))
        )
    ]
    
    # Create memory
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=10,
        return_messages=True
    )
    memories[session_id] = memory
    
    # Initialize agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        max_iterations=15,
        early_stopping_method="force"
    )
    
    return agent

# 这个函数旨在执行一个全面的 ESG 分析，它首先尝试使用 LangGraph 工作流，如果工作流创建或执行失败，则回退到基于代理（Agent）的分析
async def comprehensive_esg_analysis(session_id: str, vector_store: Chroma, company_name: str) -> Dict[str, Any]:
    """Execute comprehensive ESG analysis using LangGraph workflow"""
    
    # Create the analysis graph
    try:
        # 构建和编译 ESG 分析的 LangGraph 工作流
        analysis_graph = create_esg_analysis_graph()
    except Exception as e:
        print(f"Error creating LangGraph workflow: {e}")
        # Fallback to agent-based analysis
        #  LangGraph 工作流创建失败，函数会立即回退到调用一个名为 fallback_agent_analysis 的异步函数
        return await fallback_agent_analysis(session_id, vector_store, company_name)
    
    # Create agent for fallback
    agent = create_esg_agent(session_id, vector_store, company_name)
    agent_executors[session_id] = agent
    
    # Initialize state
    initial_state = ESGAnalysisState(
        company_name=company_name,
        vector_store=vector_store,
        initial_thoughts=[],
        selected_thoughts=[],
        document_analysis="",
        news_validation="",
        wikirate_validation="",
        metrics="",
        final_synthesis="",
        iteration=0,
        max_iterations=3,
        error=None
    )
    
    try:
        # Execute the workflow
        print("Executing LangGraph ESG analysis workflow...")
        result = analysis_graph.invoke(initial_state)
        
        # Extract results
        return {
            "initial_analysis": "\n".join(result.get("initial_thoughts", [])),
            "document_analysis": result.get("document_analysis", ""),
            "news_validation": result.get("news_validation", ""),
            "wikirate_validation": result.get("wikirate_validation", ""),  # 新增返回字段
            "metrics": result.get("metrics", ""),
            "final_synthesis": result.get("final_synthesis", ""),
            "comprehensive_analysis": f"""
            Initial Thoughts: {result.get('initial_thoughts', [])}
            
            Document Analysis: {result.get('document_analysis', '')}
            
            News Validation: {result.get('news_validation', '')}
            
            Metrics: {result.get('metrics', '')}
            """,
            "error": result.get("error")
        }
        
    except Exception as e:
        print(f"LangGraph workflow failed: {str(e)}")
        print("Falling back to agent-based analysis...")
        return await fallback_agent_analysis(session_id, vector_store, company_name)

async def fallback_agent_analysis(session_id: str, vector_store: Chroma, company_name: str) -> Dict[str, Any]:
    """Fallback to agent-based analysis if LangGraph fails"""
    
    agent = create_esg_agent(session_id, vector_store, company_name)
    agent_executors[session_id] = agent
    
    document_analysis = agent.run(
        "Perform a detailed analysis of the ESG document. "
        "Identify specific greenwashing indicators, vague language, "
        "unsubstantiated claims, and missing evidence."
    )
    
    if company_name.lower() in VALID_COMPANIES:
        news_validation = agent.run(
            f"Validate the ESG claims found in the document analysis against "
            f"recent news articles for {company_name}."
        )
    else:
        news_validation = "Company name not recognized. News validation skipped."

        # 新增Wikirate验证
        wikirate_validation = agent.run(
            f"Use the Wikirate database to verify ESG metrics and claims for {company_name}. "
            f"Compare document data with verified Wikirate database entries."
        )


    
    metrics_calculation = agent.run(
        f"Calculate detailed greenwashing metrics based on the analysis: "
        f"Document Analysis: {document_analysis}\n"
        f"News Validation: {news_validation}"
    )
    
    final_synthesis = agent.run(
        f"Create a comprehensive ESG greenwashing assessment report "
        f"synthesizing all findings from the analysis."
    )
    
    return {
        "initial_analysis": "Fallback analysis due to workflow error",
        "document_analysis": document_analysis,
        "news_validation": news_validation,
        "wikirate_validation": wikirate_validation,  # 新增返回字段
        "metrics": metrics_calculation,
        "final_synthesis": final_synthesis,
        "comprehensive_analysis": f"""
        Document Analysis: {document_analysis}
        
        News Validation: {news_validation}
        
        Metrics: {metrics_calculation}
        """,
        "error": None
    } 