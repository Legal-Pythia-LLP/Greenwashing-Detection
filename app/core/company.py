from langchain_community.vectorstores import Chroma
from langchain.schema import HumanMessage
from app.core.llm import llm

def extract_company_info(query: str, vector_store: Chroma) -> str:
    """Extract company information from vector store"""
    try:
        docs = vector_store.similarity_search(query, k=5)
        context = "\n\n".join([doc.page_content for doc in docs])
        prompt = f"""
        Extract company information from the following context:
        
        Context: {context}
        
        Query: {query}
        
        Provide specific information about the company based on the query.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Error extracting company info: {str(e)}" 