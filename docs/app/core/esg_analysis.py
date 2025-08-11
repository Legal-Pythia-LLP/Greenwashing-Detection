from typing import Dict, Any, List
from app.core.tools import (
    ESGDocumentAnalysisTool,
    NewsValidationTool,
    ESGMetricsCalculatorTool,
    WikirateValidationTool,
)
from app.core.llm import llm
from app.config import VALID_COMPANIES
from app.models import ESGAnalysisState
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage
from langchain_community.vectorstores import Chroma
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import Tool
import re
import json
from app.core.utils import is_esg_related
from app.core.company import extract_company_info

# 全局对象缓存
document_stores: Dict[str, Chroma] = {}
agent_executors: Dict[str, AgentExecutor] = {}
memories: Dict[str, ConversationBufferWindowMemory] = {}

def generate_initial_thoughts(state: ESGAnalysisState) -> ESGAnalysisState:
    output_language = state.get("output_language", "en")

    prompt = f"""
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
    - External data verification and verification methods required
      (If no verification needed, just write “none.”)

    Please output as a JSON list of 4 analytical approaches.
    Respond in {output_language}.
    """

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        thoughts_text = response.content

        try:
            thoughts = json.loads(thoughts_text)
            if isinstance(thoughts, list):
                state["initial_thoughts"] = thoughts
            else:
                state["initial_thoughts"] = thoughts_text.split('\n\n')
        except json.JSONDecodeError:
            state["initial_thoughts"] = thoughts_text.split('\n\n')

        return state

    except Exception as e:
        state["error"] = f"Error generating thoughts: {str(e)}"
        return state


def evaluate_and_select_thoughts(state: ESGAnalysisState) -> ESGAnalysisState:
    """Evaluate the quality of generated thoughts and select the best ones"""
    output_language = state.get("output_language", "en")
    
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
    Please respond in {output_language}.
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
    if state.get("error"):
        return state

    vector_store = state.get("vector_store")
    selected_thoughts = state.get("selected_thoughts", [])


    if not vector_store:
        state["error"] = "No vector store available for analysis"
        return state

    try:
        analysis_tool = ESGDocumentAnalysisTool(vector_store)
        analysis_results = []

        for thought in selected_thoughts:
            query = f"Analyze the document using this approach: {thought}"
            result = analysis_tool._run(query)
            analysis_results.append(result)

        state["document_analysis"] = analysis_results
    
        return state

    except Exception as e:
        state["error"] = f"Error in document analysis: {str(e)}"
        return state

def extract_quotations_and_tools(state: ESGAnalysisState) -> ESGAnalysisState:
    if state.get("error"):
        return state

    raw_analysis = state.get("document_analysis", [])
    flattened = [entry if isinstance(entry, str) else json.dumps(entry) for entry in raw_analysis]
    analysis = "\n".join(flattened)

    output_language = state.get("output_language", "en")

    quotation_extraction_prompt = f"""
    From the following ESG analysis, extract individual claims (quotations) along with the information below for each:

    - quotation
    - explanation
    - data_needed
    - verification_required (true/false)
    - verification_method

    Respond as a JSON list. Do not use markdown. Respond in {output_language}.

    ESG Analysis: {analysis}
    """

    try:
        response = llm.invoke([HumanMessage(content=quotation_extraction_prompt)])
        text = response.content.strip()

        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        # Try loading JSON
        try:
            quotations = json.loads(text)
            if not isinstance(quotations, list):
                raise ValueError("Parsed quotations is not a list.")
        except Exception as e:
            print("[ERROR] Failed to parse quotations JSON:", str(e))
            print("[RAW TEXT]", text[:500])
            quotations = []

        state["quotations"] = quotations
        return state

    except Exception as e:
        state["error"] = f"Error extracting quotations: {str(e)}"
        return state

def determine_tools_for_each_quotation(state: ESGAnalysisState) -> ESGAnalysisState:

    if state.get("error"):
        return state

    quotations = state.get("quotations", [])

    # ✅ 强制解析字符串 JSON（如果需要）
    if isinstance(quotations, str):
        print("[WARNING] quotations is a string. Attempting to parse JSON...")
        try:
            quotations = json.loads(quotations)
        except Exception as e:
            print("[ERROR] Failed to parse quotations string:", e)
            quotations = []

    tool_decisions = []

    for idx, q in enumerate(quotations):
        raw_required = q.get("verification_required")

        is_required = str(raw_required).strip().lower() == "true"

        if not is_required:
            tools = ["none"]
        else:
            prompt = f"""
            You are an ESG validation planner.

            Given the following ESG quotation and its explanation, choose one best tool from this list, If there is no suitable one, then choose two.:
            - news_validation
            - wikirate_validation

            You must return only:
            - "news_validation"
            - "wikirate_validation"
            - "news_validation, wikirate_validation"
            - or "none"

            Quotation: "{q.get("quotation")}"
            Explanation: "{q.get("explanation")}"
            Data Needed: "{q.get("data_needed")}"
            Verification Method: "{q.get("verification_method")}"

            Respond with ONLY a comma-separated list. No explanation.
            """

            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                tools = [t.strip() for t in response.content.lower().split(",") if t.strip()]
                if not tools:
                    tools = ["none"]
            except Exception as e:
                print(f"[ERROR] Tool selection failed for quotation {idx + 1}: {e}")
                tools = ["none"]

        tool_decisions.append({"quotation": q, "tools": tools})

    state["tool_plan"] = tool_decisions


    print(f"[ FINAL TOOL PLAN SUMMARY]\n{json.dumps(tool_decisions, indent=2)}")
    return state


def validate_each_quotation_independently(state: ESGAnalysisState) -> ESGAnalysisState:
    if state.get("error"):
        return state

    company_name = state.get("company_name", "")
    lower_name = company_name.lower()
    tool_plan = state.get("tool_plan", [])
    validated = []

    news_tool = NewsValidationTool(company_name)
    wikirate_tool = WikirateValidationTool(company_name)

    # ✅ STEP 1: 收集需要验证的 quotation
    news_quotations = []
    wiki_quotations = []

    for item in tool_plan:
        if "news_validation" in item["tools"]:
            news_quotations.append(item["quotation"])
        if "wikirate_validation" in item["tools"]:
            wiki_quotations.append(item["quotation"])

    # ✅ STEP 2: 批量调用 news_validation
    news_results = []
    if news_quotations:
        try:
            prompt = "Validate the following ESG claims using recent news.\n\n"
            for i, q in enumerate(news_quotations, 1):
                prompt += f"{i}. Claim: {q['quotation']}\nExplanation: {q['explanation']}\n\n"

            full_result = news_tool._run(prompt)

            if lower_name not in VALID_COMPANIES:
                full_result = f"[Warning] '{company_name}' not in whitelist. Forced news validation.\n\n{full_result}"

            news_results = full_result.strip().split("\n\n")
        except Exception as e:
            news_results = [f"[Error] {str(e)}"] * len(news_quotations)

    # ✅ STEP 3: 批量调用 wikirate_validation
    wiki_results = []
    if wiki_quotations:
        try:
            prompt = "Verify the following ESG metrics using public ESG databases.\n\n"
            for i, q in enumerate(wiki_quotations, 1):
                prompt += f"{i}. Claim: {q['quotation']}\nData Needed: {q['data_needed']}\n\n"

            full_result = wikirate_tool._run(prompt)

            if lower_name not in VALID_COMPANIES:
                full_result = f"[Warning] '{company_name}' not in whitelist. Forced Wikirate validation.\n\n{full_result}"

            wiki_results = full_result.strip().split("\n\n")
        except Exception as e:
            wiki_results = [f"[Error] {str(e)}"] * len(wiki_quotations)

    # ✅ STEP 4: 分配结果回每条 quotation
    news_index = 0
    wiki_index = 0

    for item in tool_plan:
        quotation = item["quotation"]
        tools = item["tools"]
        result = {
            "quotation": quotation,
            "tools_selected": tools,
            "validation": {}
        }

        if "news_validation" in tools:
            if news_index < len(news_results):
                result["validation"]["news"] = news_results[news_index]
                news_index += 1
            else:
                result["validation"]["news"] = "[Error] Missing news result."

        if "wikirate_validation" in tools:
            if wiki_index < len(wiki_results):
                result["validation"]["wikirate"] = wiki_results[wiki_index]
                wiki_index += 1
            else:
                result["validation"]["wikirate"] = "[Error] Missing Wikirate result."

        validated.append(result)

    state["validations"] = validated
    return state

def calculate_metrics(state: ESGAnalysisState) -> ESGAnalysisState:
    if state.get("error"):
        return state

    document_analysis = state.get("document_analysis", "")
    metrics_tool = ESGMetricsCalculatorTool()

    try:
        combined_text = f"Document Analysis: {document_analysis}"
        result = metrics_tool._run(combined_text)

        if isinstance(result, str):
            raw_metrics = result.strip()
            if raw_metrics.startswith("```"):
                raw_metrics = re.sub(r"^```[a-zA-Z]*\n", "", raw_metrics)
                raw_metrics = re.sub(r"\n```$", "", raw_metrics)
            try:
                result = json.loads(raw_metrics)
            except json.JSONDecodeError:
                print("[calculate_metrics] JSON 解析失败，原始内容：", raw_metrics)
                result = {}

        state["metrics"] = result
        return state

    except Exception as e:
        state["error"] = f"Error calculating metrics: {str(e)}"
        return state

def synthesize_final_report(state: ESGAnalysisState) -> ESGAnalysisState:
    if state.get("error"):
        return state

    analysis = state.get("document_analysis", "")
    validations = state.get("validations", [])
    metrics = state.get("metrics", "")
    lang = state.get("output_language", "en")

    prompt = f"""
    Generate a comprehensive ESG greenwashing assessment report.
    
    Document Analysis: {analysis}
    Validation Results: {json.dumps(validations, indent=2)}
    Metrics: {metrics}
    
    Structure:
    1. Executive Summary
    2. Key ESG Claims and Validation
    3. Greenwashing Risk Evaluation (with score)
    4. Stakeholder Recommendations
    5. Risk Areas and Uncertainties
    
    Please write the full report in {lang}.
    """

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        state["final_synthesis"] = response.content
        return state
    except Exception as e:
        state["error"] = f"Error generating final report: {str(e)}"
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

def debug_state_log(state: ESGAnalysisState) -> ESGAnalysisState:
    return state

# Create LangGraph workflow
def create_esg_analysis_graph():
    workflow = StateGraph(ESGAnalysisState)

    workflow.add_node("generate_thoughts", generate_initial_thoughts)
    workflow.add_node("evaluate_thoughts", evaluate_and_select_thoughts)  # ✅ 新增
    workflow.add_node("document_analysis", perform_document_analysis)
    workflow.add_node("extract_quotations", extract_quotations_and_tools)
    workflow.add_node("select_tools", determine_tools_for_each_quotation)
    workflow.add_node("validate_quotations", validate_each_quotation_independently)
    workflow.add_node("calculate_metrics", calculate_metrics)
    workflow.add_node("final_synthesis", synthesize_final_report)

    workflow.set_entry_point("generate_thoughts")
    workflow.add_edge("generate_thoughts", "evaluate_thoughts")  # ✅ 关键修复
    workflow.add_edge("evaluate_thoughts", "document_analysis")
    workflow.add_edge("document_analysis", "extract_quotations")
    workflow.add_node("debug_log", debug_state_log)
    workflow.add_edge("extract_quotations", "debug_log")
    workflow.add_edge("debug_log", "select_tools")
    workflow.add_edge("select_tools", "validate_quotations")
    workflow.add_edge("validate_quotations", "calculate_metrics")
    workflow.add_edge("calculate_metrics", "final_synthesis")

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
async def comprehensive_esg_analysis(session_id: str, vector_store: Chroma, company_name: str, output_language: str = "en") -> Dict[str, Any]:
    """Execute comprehensive ESG analysis using LangGraph workflow"""
    
    # Create the analysis graph
    try:
        # 构建和编译 ESG 分析的 LangGraph 工作流
        analysis_graph = create_esg_analysis_graph()
    except Exception as e:
        print(f"Error creating LangGraph workflow: {e}")
        # Fallback to agent-based analysis
        #  LangGraph 工作流创建失败，函数会立即回退到调用一个名为 fallback_agent_analysis 的异步函数
        return await fallback_agent_analysis(session_id, vector_store, company_name,output_language)
    
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
        error=None,
        output_language=output_language
    )
    
    try:
        # Execute the workflow
        print("Executing LangGraph ESG analysis workflow...")
        result = analysis_graph.invoke(initial_state)
        
        # Extract results
        return {
            "initial_analysis": "\n".join(result.get("initial_thoughts", [])),
            "document_analysis": result.get("document_analysis", ""),
            "news_validation": "\n\n".join(
                v["validation"]["news"]
                for v in result.get("validations", [])
                if "news" in v.get("validation", {})
            ),
            "wikirate_validation": "\n\n".join(
                v["validation"]["wikirate"]
                for v in result.get("validations", [])
                if "wikirate" in v.get("validation", {})
            ),
            "metrics": result.get("metrics", ""),
            "final_synthesis": result.get("final_synthesis", ""),
            "tool_plan": result.get("tool_plan", []),  
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
        return await fallback_agent_analysis(session_id, vector_store, company_name,output_language)

async def fallback_agent_analysis(session_id: str, vector_store: Chroma, company_name: str, output_language: str = "en") -> Dict[str, Any]:
    """Fallback to agent-based analysis if LangGraph fails"""
    
    agent = create_esg_agent(session_id, vector_store, company_name)
    agent_executors[session_id] = agent
    wikirate_validation = "" 
    
    document_analysis = agent.run(
        f"Perform a detailed analysis of the ESG document. "
        f"Identify specific greenwashing indicators, vague language, "
        f"unsubstantiated claims, and missing evidence.\n\n"
        f"Please respond in {output_language}."
    )
    
    if company_name.lower() in VALID_COMPANIES:
        news_validation = agent.run(
            f"Validate the ESG claims found in the document analysis against "
            f"recent news articles for {company_name}.\n\n"
            f"Please respond in {output_language}."
        )
    else:
        news_validation = agent.run(
            f"Validate the ESG claims found in the document analysis against "
            f"recent news articles for {company_name}.\n\n"
            f"Please respond in {output_language}."
        )
        news_validation = (
            f"[Warning] Company '{company_name}' is not in the whitelist. "
            f"Proceeding with forced news validation.\n\n{news_validation}"
        )

        wikirate_validation = agent.run(
            f"Use the Wikirate database to verify ESG metrics and claims for {company_name}. "
            f"Compare document data with verified Wikirate database entries.\n\n"
            f"Please respond in {output_language}."
        )
    if company_name.lower() not in VALID_COMPANIES:
        wikirate_validation = (
            f"[Warning] Company '{company_name}' is not in the whitelist. "
            f"Proceeding with forced Wikirate validation.\n\n{wikirate_validation}"
        )


    
    metrics_calculation = agent.run(
        f"Calculate detailed greenwashing metrics based on the analysis: "
        f"Document Analysis: {document_analysis}\n"
        f"News Validation: {news_validation}\n\n"
        f"Please respond in {output_language}."
    )
    
    final_synthesis = agent.run(
        f"Create a comprehensive ESG greenwashing assessment report "
        f"synthesizing all findings from the analysis.\n\n"
        f"Please respond in {output_language}."
    )
    
    return {
        "initial_analysis": "Fallback analysis due to workflow error",
        "document_analysis": document_analysis,
        "news_validation": news_validation,
        "wikirate_validation": wikirate_validation,
        "metrics": metrics_calculation,
        "final_synthesis": final_synthesis,
        "comprehensive_analysis": f"""
        Document Analysis: {document_analysis}
        
        News Validation: {news_validation}
        
        Metrics: {metrics_calculation}
        """,
        "error": None
    }