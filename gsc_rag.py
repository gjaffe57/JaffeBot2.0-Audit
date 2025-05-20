import os
from typing import List, Dict, Any
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.document_loaders import JSONLoader
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GSCRAG:
    def __init__(self, persist_directory: str = "./gsc_vector_store"):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self.qa_chain = None

    def process_gsc_data(self, gsc_data: List[Dict[str, Any]]) -> List[str]:
        """Process GSC data into documents for vectorization."""
        documents = []
        for page in gsc_data:
            doc = f"URL: {page.get('url', 'N/A')}\n"
            doc += f"Title: {page.get('title', 'N/A')}\n"
            doc += f"Content: {page.get('content', 'N/A')}\n"
            if 'metrics' in page:
                doc += f"Performance Metrics: {json.dumps(page['metrics'])}\n"
            documents.append(doc)
        return documents

    def create_vector_store(self, gsc_data: List[Dict[str, Any]]) -> None:
        """Create and persist vector store from GSC data."""
        # Process data into documents
        documents = self.process_gsc_data(gsc_data)
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        texts = text_splitter.create_documents(documents)
        
        # Create and persist vector store
        self.vectorstore = Chroma.from_documents(
            documents=texts,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        self.vectorstore.persist()

    def load_vector_store(self) -> None:
        """Load existing vector store from disk."""
        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

    def setup_qa_chain(self) -> None:
        """Setup the RAG QA chain."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Create or load it first.")
        
        llm = OpenAI(temperature=0)
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 3}
            )
        )

    def query(self, query: str) -> str:
        """Query the RAG system."""
        if not self.qa_chain:
            raise ValueError("QA chain not initialized. Call setup_qa_chain first.")
        return self.qa_chain.run(query)

    def update_vector_store(self, new_data: List[Dict[str, Any]]) -> None:
        """Update vector store with new data."""
        if not self.vectorstore:
            self.create_vector_store(new_data)
        else:
            # Process new data
            documents = self.process_gsc_data(new_data)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            texts = text_splitter.create_documents(documents)
            
            # Add new documents to existing store
            self.vectorstore.add_documents(texts)
            self.vectorstore.persist() 