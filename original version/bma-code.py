import hashlib
import os
from pathlib import Path
from typing import Annotated, Any, Dict

import pandas as pd
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.chat_engine import CondensePlusContextChatEngine

from llama_index.core.node_parser import LangchainNodeParser, MarkdownElementNodeParser
from llama_index.core.schema import Document

# from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.embeddings.openai import OpenAIEmbeddingModelType
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.readers.file.html.base import HTMLTagReader
from llama_parse import LlamaParse
from llama_parse.utils import Language
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from webscraper import bbc_search, cnn_search

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# add ------------------
AZURE_OPENAI_API_KEY_EMBED = os.getenv("AZURE_OPENAI_API_KEY_EMBED")
AZURE_OPENAI_ENDPOINT_EMBED = os.getenv("AZURE_OPENAI_ENDPOINT_EMBED")
# add ------------------
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

BASE_PATH = Path(__file__).parent
UPLOAD_DIR = BASE_PATH / "uploads"
COMPANIES_PATH = BASE_PATH / "data_files/companies.csv"


# Class for chat messages
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str


# Load valid companies
df = pd.read_csv(COMPANIES_PATH)
VALID_COMPANIES = df["company_names"].to_list()

VALID_COMPANIES = map(str.lower, VALID_COMPANIES)

# Validates Upload Types
VALID_UPLOAD_TYPES = [
    "application/pdf",
]

# Preset query for identifying potential greenwashing in a given financial document.
PRESET_INITIAL_QUERY = """ 
You are an ESG analyst reviewing a company's financial report. 
Your task is to analyse the report and identify any signs of greenwashing - such as vague language, unsubstantiated promises, or lack of measurable goals - and give a greenwashing likelihood score and explain your reasoning with specific references to the text. 
If applicable, cite quotes from the document to support your analysis.
Be specific about what makes claims suspicious or credible.
Prioritise the quality of your analysis over the quantity of text.

Start your response with the greenwashing likelihood score and a brief justification and then provide your key findings.

Keep your response concise and focused, and avoid unnecessary elaboration.
"""

# First part of validation query, will be followed by inputted summary
PRESET_VALIDATE_QUERY_START = """
Find evidence from the given news articles supporting or contradicting the claims made in the following summary:\n
Start your response with the adjusted greenwashing likelihood score and a brief justification and then provide your validation analysis.
"""

# Just needs to be followed with company name
PRESET_VALIDATE_QUERY_END = """\n
Generate a concise report on the validity of the summary.
Include quotes from the news articles where relevant, and the name of news site.
Only include articles on 
"""

# Chat response query template
CHAT_QUERY_TEMPLATE = """
You are an AI assistant specialised in analysing financial reports for greenwashing. 
You have access to the complete financial report that was uploaded.
You can answer questions about specific parts of the document, even if they weren't mentioned in your initial analysis.

Provide a concise yet informative response based on the document content - answer exactly what was asked without unnecessary elaboration
Remember that the user can ask follow-up questions if they want more detail on any point.
Reference specific parts of the financial report and explain your reasoning clearly.

If you don't have enough information to answer the question, explain what you know and what additional information would be helpful.
For questions unrelated to the document or greenwashing, provide very brief responses.
"""

GRAPH_PROMPT = """
Now, you need to build on the analysis in a quantitive way by scoring the greenwashing likelihood for each key figure identified and any others you find applicable. 
This will be used for graphing to provide the user with data visualisation of the greenwashing likelihood in the report.
For each key figure identified, structure the output into three distinct sections:
1. **Metric**: Name of the greenwashing metric (e.g., "Vague Language Score", "Lack of Evidence Score").
2. **Score**: Numerical value (e.g., 0-100) indicating the severity of greenwashing for that metric.
3. **Evidence**: Specific quotes or data points from the user's analysis that justify the score.
4. **Contains %**: "Yes" or "No" indicating if percentages are used in the evidence.
**Format**:
| Metric          | Score  |
|-----------------|--------|
| [Metric Name]   | [0-100]|
Provide an overall greenwashing score (0-10) Separate to the above example as number or decimal and not a fraction.   
"""

app = FastAPI(
    title="API",
    root_path="/v1",
    # add ------------------
    docs_url=None,
    redoc_url=None,
    # add ------------------
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
    # docs_url=None,
    # redoc_url=None,
)

llm = AzureOpenAI(
    engine="gpt-4o-mini",
    model="gpt-4o-mini",
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2023-07-01-preview",
)

embed_model = AzureOpenAIEmbedding(
    model=OpenAIEmbeddingModelType.TEXT_EMBED_3_LARGE,
    deployment_name="text-embedding-3-large",
    api_key=AZURE_OPENAI_API_KEY_EMBED,
    azure_endpoint=AZURE_OPENAI_ENDPOINT_EMBED,
    api_version="2023-05-15",
    embed_batch_size=100,
    num_workers=8,
)

llama_parser = LlamaParse(
    result_type="markdown",
    language=Language.ENGLISH,
    api_key=LLAMA_CLOUD_API_KEY,
)

lang_chain_parser = LangchainNodeParser(RecursiveCharacterTextSplitter())
node_parser = MarkdownElementNodeParser(llm=llm)

Settings.llm = llm
Settings.embed_model = embed_model

# Initialise ClimateBERT model
# Using the pre-trained ClimateBERT model (without fine-tuning) for ESG classification
climatebert_model_name = "climatebert/distilroberta-base-climate-f"
climatebert_tokenizer = AutoTokenizer.from_pretrained(
    climatebert_model_name, local_files_only=False
)
climatebert_model = AutoModelForSequenceClassification.from_pretrained(
    climatebert_model_name, local_files_only=False
)

# chat_store = SimpleChatStore()

# Store document indexes for each session in fromat {session_id: document_index}
document_indexes: Dict[
    str, VectorStoreIndex
] = {}  # Once multiple sessions are setup this can be put into a new database


def is_esg_related(text: str, threshold: float = 0.5) -> bool:
    """
    Use ClimateBERT to determine if the provided text is ESG-related.

    Args:
        text (str): The text to classify.
        threshold (float): The probability threshold for considering text ESG-related.

    Returns:
        bool: True if ESG-related, False otherwise.
    """
    # Tokenise and encode the text (limit to 512 tokens)
    inputs = climatebert_tokenizer(
        text, return_tensors="pt", truncation=True, padding=True, max_length=512
    )
    with torch.no_grad():
        outputs = climatebert_model(**inputs)

    # Compute softmax probabilities over labels
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

    # Assume label index 1 corresponds to ESG relevance.
    esg_prob = probabilities[0][1].item()
    return esg_prob >= threshold


def hash_file(file_b):
    """
    Computes the SHA-256 hash of the given file content.

    Args:
        file_b: The content of the file.

    Returns:
        str: The hexadecimal representation of the SHA-256 hash of the file content.
    """
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest()


async def extract_company_name(text: str):
    """
    Extracts the name of the company from the uploaded pdf.
    This function uses a document-based vector store index and a query engine to process the
    input text and extract the company name based on a predefined prompt.

    Args:
        text (str): The text of the financial report from which the company name is to be extracted.

    Returns:
        str: The extracted company name as a string.
    """
    company_doc = Document(text=text)
    company_index = VectorStoreIndex.from_documents([company_doc])
    company_query_engine = company_index.as_query_engine()

    extraction_prompt = "What is the name of the company that published this financial report? Return only the company name."
    response = await company_query_engine.aquery(extraction_prompt)

    return response.response.strip()


async def translate_to_english(text: str):
    """
    使用 LLM 将输入文本翻译成英文，只返回英文翻译结果。
    """
    translation_prompt = "Translate the following text to English. Only return the translated English text:\n" + text
    # 这里直接用 extract_company_name 里的方式
    doc = Document(text=text)
    index = VectorStoreIndex.from_documents([doc])
    query_engine = index.as_query_engine()
    response = await query_engine.aquery(translation_prompt)
    return response.response.strip()


@app.post("/upload")
async def upload(
    file: Annotated[UploadFile, File()], session_id: Annotated[str, Form()]
) -> dict[str, Any]:
    """
    Handles the upload of a file, processes it, and returns the filename and query response.
    Incorporates ClimateBERT filtering to extract ESG-related nodes before querying GPT-4.

    Args:
        file (UploadFile): The file to be uploaded and processed.

    Returns:
        dict: A dictionary containing the filename and the query response.

    Raises:
        HTTPException: If the file's content type is invalid.
    """

    if file.content_type not in VALID_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="invalid content type")

    file_b = await file.read()
    file_hash = hash_file(file_b)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"

    with file_path.open("wb") as f:
        f.write(file_b)

    documents = await llama_parser.aload_data(str(file_path))
    # 翻译每个 doc.text
    translated_texts = []
    for doc in documents:
        translated = await translate_to_english(doc.text)
        translated_texts.append(translated)
    # 如果你需要新的 Document 列表
    translated_documents = [Document(text=t) for t in translated_texts]

    md_output_path = BASE_PATH / f"{file_path.stem}_parsed.md"

    with open(md_output_path, "w", encoding="utf-8") as md_file:
        for i, doc in enumerate(translated_documents):
            md_file.write(f"# Document {i+1}\n\n")
            md_file.write(doc.text.strip())
            md_file.write("\n\n---\n\n")  # 分隔線


    for i, doc in enumerate(translated_documents):
        print(f"\n--- Document {i+1} ---")
        print(doc.text)

    first_pages_text = "\n\n".join(
        [doc.text for doc in documents[: min(3, len(documents))]]
    )

    company_name = await extract_company_name(first_pages_text)

    recursive_index = document_indexes.get(session_id, None)
    if not recursive_index:
        nodes = await lang_chain_parser.aget_nodes_from_documents(
            translated_documents, show_progress=True
        )

        # Filter ESG-related nodes using ClimateBERT
        filtered_nodes = []
        for node in nodes:
            node_text = node.get_text() if hasattr(node, "get_text") else str(node)

            if is_esg_related(node_text):
                filtered_nodes.append(node)

        if not filtered_nodes:
            filtered_nodes = nodes

        base_nodes, objects = node_parser.get_nodes_and_objects(filtered_nodes)
        recursive_index = VectorStoreIndex(
            nodes=base_nodes + objects, show_progress=True
        )

        document_indexes[session_id] = recursive_index

    query_engine = recursive_index.as_query_engine(similarity_top_k=25)

    query_response = await query_engine.aquery(PRESET_INITIAL_QUERY)
    graph_response = await query_engine.aquery(
        f"""
    **Task**: You have just completed a qualitative analysis of a financial report and identified potential greenwashing.  
    **Constraint**: The greenwashing score MUST remain EXACTLY the same as in the original analysis. Keep the scores from 1-10.

    **Validation Analysis**:  
    {query_response.response}  

    **Graph Data Requirements**:  
    {GRAPH_PROMPT}  
    """
    )

    file_path.unlink(missing_ok=True)

    return {
        "filename": file_path.name,
        "response": query_response.response,
        "graphdata": graph_response.response,
        "companyName": company_name,
    }


@app.post("/validate")
async def validate_upload(json_data: dict) -> dict[str, Any]:
    """
    Handles the upload of a summary and a company name, processes them, and returns the filenames of stored HTML files and query response.

    Args:
        json_data (dict): A dictionary containing the summary, company name and session id.

    Returns:
        dict: A dictionary containing the file names of the stored HTML files (None if company name not recognised) and the query response ("Company name not recognised" if company name not recognised).

    Raises:
        HTTPException: If the json_data content is invalid (needs to contain summary and companyName).
    """

    try:
        summary = json_data["summary"]
        company_name = json_data["companyName"]
        session_id = json_data["session_id"]
    except KeyError:
        raise HTTPException(status_code=400, detail="invalid content")

    recursive_index = document_indexes.get(session_id, None)
    if not recursive_index:
        raise HTTPException(status_code=400, detail="invalid content")

    # chat_memory = chat_store_setup(chat_store, session_id)

    if company_name.lower() in VALID_COMPANIES:
        bbc_articles = bbc_search(company_name)
        cnn_articles = cnn_search(company_name)

        news_articles = {}
        if bbc_articles:
            news_articles.update(bbc_articles)
        if cnn_articles:
            news_articles.update(cnn_articles)

        if news_articles is None:
            return {"filenames": None, "response": "No web articles available"}
    else:
        return {"filenames": None, "response": "Company name not recognised"}

    html_reader = HTMLTagReader(tag="section", ignore_no_id=False)
    file_names = []
    documents = []

    for html_file_path_str in news_articles.values():
        html_file_path = Path(html_file_path_str)
        docs = html_reader.load_data(html_file_path)

        for doc in docs:
            document = Document(text=doc.text, metadata=doc.metadata)
            documents.append(document)

        file_names.append(html_file_path.name)
        html_file_path.unlink(missing_ok=True)

    nodes = await lang_chain_parser.aget_nodes_from_documents(documents, show_progress=True)
    base_nodes, objects = node_parser.get_nodes_and_objects(nodes)
    recursive_index = VectorStoreIndex(nodes=base_nodes + objects, show_progress=True)
    query_engine = recursive_index.as_query_engine(similarity_top_k=25)

    query_response = await query_engine.aquery(
        PRESET_VALIDATE_QUERY_START + summary + PRESET_VALIDATE_QUERY_END + company_name
    )
    graph_response = await query_engine.aquery(
        f"""
    **Task**: Validate a financial report's greenwashing score against news articles. 
    **Constraint**: The score MUST remain unchanged from the validation analysis from 1-10. 

    Validation Analysis:
    {query_response.response}

    Graph Data Requirements:
    {GRAPH_PROMPT}
    """
    )

    return {
        "filenames": file_names,
        "response": query_response.response,
        "graphdata": graph_response.response,
    }


@app.post("/chat")
async def chat(json_data: ChatBaseMessage) -> dict[str, Any]:
    """
    Handles chat messages from the user about the greenwashing analysis.
    Uses both chat history and the original document index for context.

    Args:
        json_data (ChatBaseMessage): A ChatBaseMessage object containing the user's message and session id.

    Returns:
        dict: A dictionary containing the AI's response to the user's question.
    """

    user_message = json_data.message
    session_id = json_data.session_id

    document_index = document_indexes.get(session_id)
    retriever = document_index.as_retriever(similarity_top_k=10)

    chat_engine = CondensePlusContextChatEngine.from_defaults(
        retriever=retriever,
        llm=llm,
        system_prompt=CHAT_QUERY_TEMPLATE,
    )

    # add ------------
    # chat_response = await chat_engine.achat(user_message)
    # return {"response": chat_response.response}
    # add ------------

    chat_response = await chat_engine.astream_chat(user_message)

    return StreamingResponse(
        content=chat_response.async_response_gen(),
        media_type="text/event-stream",
    )
