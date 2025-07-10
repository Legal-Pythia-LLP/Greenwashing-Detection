import hashlib  # 用于生成哈希值，可能用来对上传文件或内容生成唯一 ID
import os  # 操作系统交互（如读取环境变量、路径操作）
from pathlib import Path  # 更现代的路径管理工具
from typing import Annotated, Any, Dict  # 模块中的几个类用于类型注解
import pandas as pd  # 数据处理库，后续读取公司 CSV 列表等
import torch
from dotenv import load_dotenv  # 从 .env 文件中读取环境变量，如 API 密钥
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware  # 这两行导入 FastAPI 主体和允许跨域的中间件。
from langchain.text_splitter import RecursiveCharacterTextSplitter  # 这是 LangChain 的文本文段拆分工具，用于将长文本拆成可控块，比如按段落或字符长度。
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.chat_engine import CondensePlusContextChatEngine

from llama_index.core.node_parser import LangchainNodeParser, MarkdownElementNodeParser
from llama_index.core.schema import Document
# 这些模块构成了文档处理和问答索引核心：
# •	VectorStoreIndex：将文本转成向量进行索引，支持语义搜索。
# •	ChatEngine：可以基于上下文多轮对话。
# •	NodeParser：将文档结构解析为不同层级（标题/正文/段落）。
# •	Document：文本载体。


# from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.embeddings.openai import OpenAIEmbeddingModelType
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.readers.file.html.base import HTMLTagReader
from llama_parse import LlamaParse
from llama_parse.utils import Language
# 这些模块负责将文件转换成嵌入向量、支持 Azure OpenAI 的 Embedding 与 LLM 接口，适配 HTML 文件格式，适合 ESG 报告结构处理。


from pydantic import BaseModel  # 定义传入请求体的数据结构（如对话内容）
from starlette.responses import StreamingResponse  # 用于返回逐步生成内容
from transformers import AutoModelForSequenceClassification, AutoTokenizer
# 加载预训练模型（如 RoBERTa/BERT）
from webscraper import bbc_search, cnn_search  # 自定义模块，从 BBC 和 CNN 抓 ESG 相关新闻用于“反证”

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from llama_index.llms.langchain import LangChainLLM
from llama_index.embeddings.langchain import LangchainEmbedding


load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY_2 = os.getenv("AZURE_OPENAI_API_KEY_2")
AZURE_OPENAI_ENDPOINT_2 = os.getenv("AZURE_OPENAI_ENDPOINT_2")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
# 从 .env 文件中加载 OpenAI/Azure 的 API 密钥，用于后续调用大模型与嵌入模型

google_api_key = os.getenv("GOOGLE_API_KEY")

BASE_PATH = Path(__file__).parent
# 当前文件所在路径
UPLOAD_DIR = BASE_PATH / "uploads"
# 用户上传的 ESG 报告将保存在这里
COMPANIES_PATH = BASE_PATH / "data_files/companies.csv"


# 公司白名单 CSV 路径，用于识别合法公司

# Class for chat messages
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str

# 定义 FastAPI 请求结构模型（对话用）
# 用于前端与后端交互的格式，包含用户发的问题和当前对话 session_id

# Load valid companies
df = pd.read_csv(COMPANIES_PATH)
VALID_COMPANIES = df["company_names"].to_list()

VALID_COMPANIES = map(str.lower, VALID_COMPANIES)
# 加载合法公司名
# 从 CSV 中提取出所有公司名，统一转为小写，后续上传文档或用户提问时用于验证

# Validates Upload Types
VALID_UPLOAD_TYPES = [
    "application/pdf",
]
# 目前只允许 PDF 格式上传（公司 ESG 报告）


# prompt 字符串变量 用于 GPT 自动判断和分析 ESG 文本是否存在“漂绿”行为的指令模板设计
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
)
# 初始化一个 FastAPI 应用，接口路径前缀设为 /v1

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
    # docs_url=None,
    # redoc_url=None,
)
# 添加跨域中间件（CORS），允许所有来源发起 POST 请求，并携带身份信息（如 token）。关闭了默认的 Swagger 文档与 ReDoc 页面
# 让你的网站能被其他域名的前端访问（比如你的前端在 localhost:3000，后端在 localhost:8000，就算“跨域”了）

# llm = AzureOpenAI(
#     engine="gpt-4o-mini",
#     model="gpt-4o-mini",
#     api_key=AZURE_OPENAI_API_KEY,
#     azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     api_version="2023-07-01-preview",
# )
# 初始化 GPT 模型客户端（这里用的是 GPT-4o-mini），通过 Azure OpenAI 的 API 接入
# embed_model = AzureOpenAIEmbedding(
#     model=OpenAIEmbeddingModelType.TEXT_EMBED_3_LARGE,
#     deployment_name="text-embedding-3-large",
#     api_key=AZURE_OPENAI_API_KEY_2,
#     azure_endpoint=AZURE_OPENAI_ENDPOINT_2,
#     api_version="2023-05-15",
#     embed_batch_size=100,
#     num_workers=8,
# )
# 初始化文本嵌入模型（embedding model），使用的是 OpenAI 的 text-embedding-3-large，批处理大小为 100，支持 8 个工作线程并发处理。用于后续构建向量数据库（如用于相似度检索）

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # flash比较快
    temperature=0,  # 控制生成文本的“随机性” 0 表示完全确定，0.7 稍微有创造性，1.0 比较随机
    max_tokens=None,  # 最多生成多少 token（字词） None 表示使用模型默认（可不写）
    timeout=None,  # 单次请求最长等待时间 None 表示默认等待，可设置为 60 秒等
    max_retries=2,  # max_retries出错时重试次数 推荐设置为 2~3
    # other params...
)

embed_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",  # 最新版本
    task_type="retrieval_document"
)
embed_model_gemini = LangchainEmbedding(embed_model)

llm_wrapper = LangChainLLM(llm=llm_gemini)

llama_parser = LlamaParse(
    result_type="markdown",
    language=Language.ENGLISH,
    api_key=LLAMA_CLOUD_API_KEY,
)
# LlamaParse 是一个 PDF / 文本解析工具，可以将报告解析为 markdown 格式结构化文本

lang_chain_parser = LangchainNodeParser(RecursiveCharacterTextSplitter())
# 这个解析器使用 LangChain 的节点切分器（基于字符分块），用于文档分段处理
node_parser = MarkdownElementNodeParser(llm=llm_wrapper)
# 基于 markdown 的结构元素进行分块解析，使用 LLM 来辅助理解内容结构。

Settings.llm = llm_gemini
Settings.embed_model = embed_model_gemini
# 将上述 LLM 和嵌入模型设置为全局默认（Settings 应该是你项目中定义的配置类）

# Initialise ClimateBERT model
# Using the pre-trained ClimateBERT model (without fine-tuning) for ESG classification
climatebert_model_name = "climatebert/distilroberta-base-climate-f"
climatebert_tokenizer = AutoTokenizer.from_pretrained(
    climatebert_model_name, local_files_only=True
)
climatebert_model = AutoModelForSequenceClassification.from_pretrained(
    climatebert_model_name, local_files_only=True
)
# 从本地加载 ClimateBERT 模型和 tokenizer。该模型是基于 DistilRoBERTa 的 ESG 微调模型，专门用于判断文本是否与 ESG / 气候变化相关

# chat_store = SimpleChatStore()

# Store document indexes for each session in fromat {session_id: document_index}
document_indexes: Dict[
    str, VectorStoreIndex
] = {}  # Once multiple sessions are setup this can be put into a new database


# 这是一个以 session_id 为 key 的字典，缓存每个用户上传的文档向量索引。可用于相似段落检索、问答等


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
    # 对输入文本进行分词并编码为模型输入张量（最多 512 个 token）
    with torch.no_grad():
        outputs = climatebert_model(**inputs)
    # 使用模型做预测，torch.no_grad() 表示不计算梯度，提高推理效率

    # Compute softmax probabilities over labels
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
    # 对模型输出的 logits 做 softmax，得到属于每个类别的概率值
    # Assume label index 1 corresponds to ESG relevance.
    esg_prob = probabilities[0][1].item()
    return esg_prob >= threshold
    # 假设类别索引 1 是 “ESG 相关”，如果其概率大于等于设定的阈值（默认 0.5），就认为文本是 ESG 相关的，返回 True，否则返回 False


# 定义一个函数，用来判断输入文本是否是“ESG 相关”的

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


# 对上传文件的内容生成唯一的哈希值（SHA-256）

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
    #llm_wrapper = LangChainLLM(llm=llm_gemini)
    company_doc = Document(text=text)
    company_index = VectorStoreIndex.from_documents([company_doc])
    # 把输入文本转换为文档，生成向量索引

    company_query_engine = company_index.as_query_engine(llm=llm_wrapper)
    #company_query_engine = company_index.as_query_engine()
    # 使用向量索引创建查询引擎，支持语义搜索 + GPT 查询

    extraction_prompt = "What is the name of the company that published this financial report? Return only the company name."
    response = await company_query_engine.aquery(extraction_prompt)
    # 异步向 GPT 发送问题，提取公司名称
    return response.response.strip()
    # 返回公司名称，去除空格


# 该功能通过基于文档的向量存储索引和查询引擎处理输入文本，并根据预定义的提示词提取公司名称。

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
    # 拒绝非法文件类型（如 txt、exe 等），只允许合法 PDF 类型上传
    file_b = await file.read()
    file_hash = hash_file(file_b)
    # 读取文件并计算唯一哈希值

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    # 保存路径：uploads/{file_hash}.pdf

    with file_path.open("wb") as f:
        f.write(file_b)
    # 将上传的 PDF 写入服务器本地

    documents = await llama_parser.aload_data(str(file_path))
    # 用 LlamaParse 异步解析 PDF 内容为结构化文档对象
    first_pages_text = "\n\n".join(
        [doc.text for doc in documents[: min(3, len(documents))]]
    )

    company_name = await extract_company_name(first_pages_text)
    ##取前三页内容，通过 GPT 提取公司名

    # 如果该用户 session 没有缓存过索引，则重新构建
    recursive_index = document_indexes.get(session_id, None)
    if not recursive_index:
        nodes = await lang_chain_parser.aget_nodes_from_documents(
            documents, show_progress=True
        )
        # 用 Langchain 解析器异步将文档切成节点（段落、标题、列表等结构块）

        # Filter ESG-related nodes using ClimateBERT
        filtered_nodes = []
        for node in nodes:
            node_text = node.get_text() if hasattr(node, "get_text") else str(node)

            if is_esg_related(node_text):
                filtered_nodes.append(node)
        # 逐个判断节点是否与 ESG 相关，保留相关内容
        if not filtered_nodes:
            filtered_nodes = nodes
        # 若没有 ESG 内容，退化为使用全部节点
        base_nodes, objects = node_parser.get_nodes_and_objects(filtered_nodes)
        recursive_index = VectorStoreIndex(
            nodes=base_nodes + objects, show_progress=True
        )
        # node_parser 使用 GPT + Markdown 分析结构关系。
        # 将所有节点生成向量索引，用于后续问答
        document_indexes[session_id] = recursive_index
        # 缓存向量索引到内存字典，供该用户后续查询使用

    #query_engine = recursive_index.as_query_engine(similarity_top_k=25)
    query_engine = recursive_index.as_query_engine(
        llm=llm_wrapper, similarity_top_k=25
    )
    # 使用向量索引生成语义检索器，最多返回最相似的 25 条文本块

    query_response = await query_engine.aquery(PRESET_INITIAL_QUERY)
    # 发送预设漂绿检测 prompt，生成主分析报告（定性）
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
    # 保留前面分析分数
    # 要求输出每项评分（如 Vague Language、Evidence 等）
    # 每项包括：指标名、分数、证据、是否包含百分比
    # 用于前端绘制雷达图、条形图等可视化分析

    file_path.unlink(missing_ok=True)
    # 删除临时保存的 PDF 文件
    return {
        "filename": file_path.name,
        "response": query_response.response,
        "graphdata": graph_response.response,
        "companyName": company_name,
    }


# 这个 /validate API 不会在用户上传 PDF 后自动执行，它是一个 由前端用户主动触发的二次验证接口
# 根据新闻网页验证漂绿评分的合理性，以比对原始报告分析（summary）和真实新闻内容的一致性
# 不需要用户自己动手复制粘贴summary ，你完全可以在前端自动处理这个过程
# /validate 中的 session_id 和 /upload 中的 session_id 是同一个东西，用于标识用户的当前会话，以便共享和复用前面处理过的文档内容和索引数据
# 前端自动保存并发送 summary、companyName、session_id
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
        # 用户提交的报告分析摘要（GPT分析结果）
        company_name = json_data["companyName"]
        session_id = json_data["session_id"]
        # 用于访问用户缓存的向量索引
    except KeyError:
        raise HTTPException(status_code=400, detail="invalid content")
    # 提取 JSON 内容，如果缺少任意字段，就抛出 HTTP 400 异常
    recursive_index = document_indexes.get(session_id, None)
    if not recursive_index:
        raise HTTPException(status_code=400, detail="invalid content")
    # 检查用户是否已经上传过文档、生成过索引。否则拒绝验证请求
    # chat_memory = chat_store_setup(chat_store, session_id)

    if company_name.lower() in VALID_COMPANIES:
        bbc_articles = bbc_search(company_name)
        cnn_articles = cnn_search(company_name)
        # 确认公司名在已知公司白名单 VALID_COMPANIES 中，执行 BBC 和 CNN 新闻抓取函数
        news_articles = {}
        if bbc_articles:
            news_articles.update(bbc_articles)
        if cnn_articles:
            news_articles.update(cnn_articles)
        # 整合两方新闻的搜索结果。它们都是 {title: html_file_path} 的形式
        if news_articles is None:
            return {"filenames": None, "response": "No web articles available"}
    else:
        return {"filenames": None, "response": "Company name not recognised"}

    html_reader = HTMLTagReader(tag="section", ignore_no_id=False)
    file_names = []
    documents = []
    # 初始化一个 HTML 读取器，用于解析 HTML 中的 <section> 标签内容
    for html_file_path_str in news_articles.values():
        html_file_path = Path(html_file_path_str)
        docs = html_reader.load_data(html_file_path)
        # 逐个读取 HTML 文件中的内容，并转化为文档对象
        for doc in docs:
            document = Document(text=doc.text, metadata=doc.metadata)
            documents.append(document)
        # 每个 <section> 标签块都变成一个 Document 对象，供后续构建索引使用
        file_names.append(html_file_path.name)
        html_file_path.unlink(missing_ok=True)
    # 记录该文件名并从磁盘删除 HTML 文件

    nodes = lang_chain_parser.aget_nodes_from_documents(documents, show_progress=True)
    # 使用 LangChain 解析器将新闻文档切分为节点块（段落或结构元素）
    base_nodes, objects = node_parser.get_nodes_and_objects(nodes)
    # 调用结构分析工具对节点进行“主内容 + 子结构”的抽取

    #recursive_index = VectorStoreIndex(nodes=base_nodes + objects, show_progress=True)
    # 构建基于节点的向量索引，供 GPT 使用语义搜索
    recursive_index = VectorStoreIndex(
        nodes=base_nodes + objects,
        llm=llm_wrapper,
        show_progress=True
    )

    query_engine = recursive_index.as_query_engine(
        llm=llm_wrapper,
        similarity_top_k=25
    )
    #query_engine = recursive_index.as_query_engine(similarity_top_k=25)
    # 最多选择相似度前 25 的节点块作为上下文
    query_response = await query_engine.aquery(
        PRESET_VALIDATE_QUERY_START + summary + PRESET_VALIDATE_QUERY_END + company_name
    )
    # 向 GPT 发送验证 prompt
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
    # “整体 greenwashing 得分”作为定值 保持不变，然后只为图表化打出每个子项的分数（比如模糊语言打几分，证据缺失打几分等）

    return {
        "filenames": file_names,
        "response": query_response.response,
        "graphdata": graph_response.response,
    }


# 定义了一个 POST 请求接口，路由为 /chat。
# 接收一个 json_data 参数，其类型为 ChatBaseMessage，包含用户输入消息（message）和 session ID（session_id）。
# 异步函数：允许处理 IO 操作，如 LLM 请求、检索等
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
    # 从 JSON 数据中提取用户提问和当前对话的 session ID
    document_index = document_indexes.get(session_id)
    # 从全局字典 document_indexes 中获取与当前 session_id 关联的文档索引（VectorStoreIndex）。
    # 这是之前通过 /upload 或 /validate 路由构建好的，包含 ESG 报告或新闻文章

    retriever = document_index.as_retriever(similarity_top_k=10)
    # 创建一个检索器（retriever），用于从文档中选出与用户消息最相似的前 10 个片段（节点）。
    # 这为 LLM 提供上下文增强（context augmentation）

    # chat_engine = CondensePlusContextChatEngine.from_defaults(
    #     retriever=retriever,
    #     llm=llm,
    #     system_prompt=CHAT_QUERY_TEMPLATE,
    # )
    chat_engine = CondensePlusContextChatEngine.from_defaults(
        retriever=retriever,
        llm=llm_wrapper,  # ✅ 改为 Gemini
        system_prompt=CHAT_QUERY_TEMPLATE,
    )
    # 创建一个带上下文增强的对话引擎 CondensePlusContextChatEngine
    # 利用 retriever 检索相关文档片段；
    # 使用当前配置的 llm（Azure OpenAI GPT-4o-mini）进行生成；
    # 提供系统 prompt（规则提示词）CHAT_QUERY_TEMPLATE，设定 AI 回答的角色和语气。

    chat_response = await chat_engine.astream_chat(user_message)
    # 异步地对用户消息执行“streaming chat”，即边生成边发送响应。
    # 输出是一个支持 async 流式生成的响应对象

    return StreamingResponse(
        content=chat_response.async_response_gen(),
        media_type="text/event-stream",
    )
    # 使用 StreamingResponse 将 LLM 的响应实时推送到前端（类似 ChatGPT 那种一边加载一边显示的体验）。
# async_response_gen() 是生成响应内容的异步生成器。
# media_type="text/event-stream" 告诉前端这是一个 Server-Sent Events 流式传输。
