from typing import Dict, Any, List, Optional
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
import os, json
from app.core.utils import is_esg_related
from app.core.company import extract_company_info
from app.core.metrics_tools import get_metrics_tool
from app.core.metrics_tools.schema_utils import ensure_unified_metrics_schema as _ensure_unified_metrics_schema

# Global object cache
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
    - External data verification and verification methods required(If external data verification is not required, you can write “none.” Your current external data access is limited to **company news and open ESG data**. You do not have extensive access to long-term historical performance data or comprehensive peer comparison data beyond what might be present in open ESG datasets or mentioned in news.)

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
    selected_thoughts = state.get("selected_thoughts") or state.get("initial_thoughts", [])


    if not vector_store:
        state["error"] = "No vector store available for analysis"
        return state

    try:
        analysis_tool = ESGDocumentAnalysisTool(vector_store)
        analysis_results = []

        def as_text(x):
            if isinstance(x, dict):
                return json.dumps(x, ensure_ascii=False)
            return str(x)

        for thought in selected_thoughts:
            query = (
                "Analyze the document using this approach:\n"
                f"{as_text(thought)}\nReturn concise bullet points."
            )
            ok = False
            try:
                result = analysis_tool._run(query)
                if not isinstance(result, str):
                    result = json.dumps(result, ensure_ascii=False)
                
                if "[ERROR" in result or "list object has no attribute 'replace'" in result:
                    raise RuntimeError("downstream returned error text")
                ok = True
            except Exception as e:
                
                docs = vector_store.similarity_search(
                    "ESG claims, targets, metrics, offsets, scope 1/2/3, carbon neutral, PAS 2060, REC, GO, ISAE 3000",
                    k=8
                )
                result = "\n".join(getattr(d, "page_content", "") for d in docs if getattr(d, "page_content", ""))
                result = result or f"[fallback-no-content due to {e}]"

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
    - greenwashing_likelihood_score
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

    #  Force parse string JSON (if needed)
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

            Given the following ESG quotation and its explanation, Select the appropriate tools. You can select one or more, or none if none are suitable.:
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

    #  STEP 1: Collect quotations needing validation
    news_quotations = []
    wiki_quotations = []

    for item in tool_plan:
        if "news_validation" in item["tools"]:
            news_quotations.append(item["quotation"])
        if "wikirate_validation" in item["tools"]:
            wiki_quotations.append(item["quotation"])

    # STEP 2: Batch call news_validation
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

    # STEP 3: Batch call wikirate_validation
    wiki_results = []
    if wiki_quotations:
        try:
            prompt = "Verify the following ESG metrics using public ESG databases.\n\n"
            for i, q in enumerate(wiki_quotations, 1):
                prompt += f"{i}. Claim: {q['quotation']}\nExplanation: {q['explanation']}\n\n"

            full_result = wikirate_tool._run(prompt)

            if lower_name not in VALID_COMPANIES:
                full_result = f"[Warning] '{company_name}' not in whitelist. Forced Wikirate validation.\n\n{full_result}"

            wiki_results = full_result.strip().split("\n\n")
        except Exception as e:
            wiki_results = [f"[Error] {str(e)}"] * len(wiki_quotations)

    # STEP 4: Assign results back to each quotation
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

import os, json
from app.core.metrics_tools import get_metrics_tool
from app.core.metrics_tools.schema_utils import ensure_unified_metrics_schema as _ensure_unified_metrics_schema

def _pad_five_dimensions(m: dict) -> dict:
    """Ensure both `breakdown` and `radar` always contain all 5 dimensions; fill missing ones with 0."""
    wanted = [
        ("Vague or unsubstantiated claims", "vague"),
        ("Lack of specific metrics or targets", "lack_metrics"),
        ("Misleading terminology", "misleading"),
        ("Cherry-picked data", "cherry"),
        ("Absence of third-party verification", "no_3rd"),
    ]
    m.setdefault("breakdown", [])
    existing_labels = {(x.get("type") or "").strip() for x in m["breakdown"] if isinstance(x, dict)}
    for label, _ in wanted:
        if label not in existing_labels:
            m["breakdown"].append({"type": label, "value": 0})

    m.setdefault("radar", {})
    for _, key in wanted:
        m["radar"].setdefault(key, 0)
    return m

def calculate_metrics(state: ESGAnalysisState) -> ESGAnalysisState:
    """Compute metrics with rules/LLM hybrid or legacy, normalize schema, and guarantee 5-dim output."""
    if state.get("error"):
        return state

    # Select scoring mode: request param takes precedence, then environment variable.
    mode = (state.get("rules_mode") or os.getenv("RULES_MODE", "legacy")).lower().strip()
    tool = get_metrics_tool(mode=mode)
    print(f"[METRICS] mode={mode} tool={type(tool).__name__}")

    # Build the text to score (try to include as much meaningful content as possible).
    parts = []
    doc_analysis = state.get("document_analysis", "")
    if isinstance(doc_analysis, list):
        parts.extend([str(x) for x in doc_analysis if x])
    elif isinstance(doc_analysis, str) and doc_analysis.strip():
        parts.append(doc_analysis)

    vals = state.get("validations", [])
    if isinstance(vals, list):
        for item in vals:
            if isinstance(item, dict):
                q = item.get("quotation", {})
                if isinstance(q, dict):
                    qt = q.get("quotation", "")
                    ex = q.get("explanation", "")
                    if qt:
                        parts.append(str(qt))
                    if ex:
                        parts.append(str(ex))

    combined_text = "\n".join(p for p in parts if isinstance(p, str)).strip()
    if not combined_text:
        combined_text = "No prior analysis content. Please score based on rules evidence only."

    try:
        # Tool may return a JSON string or an already-parsed dict.
        raw = tool._run(combined_text)
        metrics = json.loads(raw) if isinstance(raw, str) else (raw or {})
        # Normalize field names/scales and ensure 5-dim completeness.
        metrics = _ensure_unified_metrics_schema(metrics)
        metrics = _pad_five_dimensions(metrics)
        state["metrics"] = metrics
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
    Create a comprehensive final ESG greenwashing assessment report that synthesizes all findings:
    
    Document Analysis: {analysis}
    Validation Results: {json.dumps(validations, indent=2)}
    Metrics: {metrics}
    
    Structure:
    1. Executive Summary
    2. Key ESG Claims and Validation
    3. Greenwashing Risk Evaluation (with score)
    4. Stakeholder Recommendations
    5. Risk Areas and Uncertainties
    
    Your report should be professional, detailed, and suitable for executive review, structured as follows:
        1.  **Executive Summary**: Provide a concise overview of the assessment, including the overall greenwashing score (0-10).
        2.  **Key Findings and Evidence from Document Analysis**: 
            Detail the following content：
            2.1 quotation
            2.2 explanation
            2.3 greenwashing_likelihood_score
            2.4 External verification conducted and verification results
            2.5 further verification required for each statement
            * For 2.2 explanation and 2.3 greenwashing_likelihood_score, please revise the explanations and scores in the quotation based on the verification results to obtain new explanations and scores.
            * For 2.5 further verification required， If, after conducting news and Wikirate verification, additional external data is still required to verify whether this reference is greenwashing, please provide a detailed description of the additional external verification required..
        3.  **Greenwashing Types, Likelihood, and Overall Score**:
            * For each of the five greenwashing types identified in the Metrics, describe its likelihood.
            * Present the final overall greenwashing score.
        4.  **Specific Recommendations for Stakeholders**: Offer actionable recommendations tailored for relevant stakeholders.
        5.  **Risk Assessment and Concerns**: Outline potential risks and areas of concern related to the identified greenwashing.
        

    
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
    workflow.add_node("evaluate_thoughts", evaluate_and_select_thoughts)  # ✅ New
    workflow.add_node("document_analysis", perform_document_analysis)
    workflow.add_node("extract_quotations", extract_quotations_and_tools)
    workflow.add_node("select_tools", determine_tools_for_each_quotation)
    workflow.add_node("validate_quotations", validate_each_quotation_independently)
    workflow.add_node("calculate_metrics", calculate_metrics)
    workflow.add_node("final_synthesis", synthesize_final_report)

    workflow.set_entry_point("generate_thoughts")
    workflow.add_edge("generate_thoughts", "evaluate_thoughts")  # ✅ Critical fix
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

# This function performs a comprehensive ESG analysis, first trying the LangGraph workflow, then falling back to agent-based analysis if workflow creation/execution fails
async def comprehensive_esg_analysis(session_id: str, 
                                     vector_store: Chroma, 
                                     company_name: str, 
                                     output_language: str = "en",
                                     rules_mode: Optional[str] = None) -> Dict[str, Any]:
    """Execute comprehensive ESG analysis using LangGraph workflow"""
    
    # Create the analysis graph
    try:
        # Build and compile LangGraph workflow for ESG analysis
        analysis_graph = create_esg_analysis_graph()
    except Exception as e:
        print(f"Error creating LangGraph workflow: {e}")
        # Fallback to agent-based analysis
        # If LangGraph workflow creation fails, immediately fall back to calling fallback_agent_analysis async function
        return await fallback_agent_analysis(session_id, vector_store, company_name,output_language, rules_mode=rules_mode)
    
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
        output_language=output_language,
        rules_mode=rules_mode
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

async def fallback_agent_analysis(session_id: str, vector_store: Chroma, company_name: str, output_language: str = "en",rules_mode: Optional[str] = None) -> Dict[str, Any]:
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
