from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
import os

load_dotenv(override=True)

MODEL = "gpt-oss:20b"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "huggingface")  # 'huggingface' or 'openai'
RETRIEVAL_K = 10

# Choose embeddings based on config
if EMBEDDING_MODEL == "openai":
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    DB_NAME = str(Path(__file__).parent.parent / "vector_db_openai")
else:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},  # Use 'cuda' if you have GPU
        encode_kwargs={'normalize_embeddings': True}  # Better for similarity search
    )
    DB_NAME = str(Path(__file__).parent.parent / "vector_db_huggingface")

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
If relevant, use the given context to answer any question.
If you don't know the answer, say so.
Context:
{context}
"""

# Initialize vector store
try:
    vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
except Exception as e:
    print(f"Error loading vector store: {e}")
    print(f"You may need to rebuild the vector database with the current embedding model.")
    raise

llm = ChatOllama(model=MODEL)


def fetch_context(question: str) -> list[Document]:
    """
    Retrieve relevant context documents for a question.
    
    Args:
        question: The user's question
        
    Returns:
        List of relevant documents
    """
    try:
        # Note: retriever already has k configured, but we can override
        return retriever.invoke(question)
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return []  # Return empty list on error


def combined_question(question: str, history: list[dict] = []) -> str:
    """
    Combine all the user's messages into a single string for better retrieval.
    
    Args:
        question: Current question
        history: Conversation history
        
    Returns:
        Combined question string
    """
    prior = "\n".join(m["content"] for m in history if m["role"] == "user")
    if prior:
        return f"{prior}\n{question}"
    return question


def answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Document]]:
    """
    Answer the given question with RAG; return the answer and the context documents.
    
    Args:
        question: User's question
        history: Conversation history
        
    Returns:
        Tuple of (answer string, list of retrieved documents)
    """
    try:
        combined = combined_question(question, history)
        docs = fetch_context(combined)
        
        if not docs:
            context = "No relevant context found."
        else:
            context = "\n\n".join(doc.page_content for doc in docs)
        
        system_prompt = SYSTEM_PROMPT.format(context=context)
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(convert_to_messages(history))
        messages.append(HumanMessage(content=question))
        
        response = llm.invoke(messages)
        return response.content, docs
    
    except Exception as e:
        error_msg = f"Error generating answer: {str(e)}"
        print(error_msg)
        return error_msg, []