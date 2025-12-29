#!/usr/bin/env python3
"""
LLM-RAG Implementation Module
Based on the research paper's Gemma3 + FAISS approach for LEED report generation.
Implements retrieval-augmented generation for factual, contextually relevant documentation.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

# RAG components
try:
    from sentence_transformers import SentenceTransformer
    from faiss import IndexFlatIP
    import torch
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# LLM components
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

@dataclass
class KnowledgeChunk:
    """Knowledge base chunk with metadata"""
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

@dataclass
class RetrievalResult:
    """Retrieval result with relevance score"""
    chunk: KnowledgeChunk
    score: float
    rank: int

@dataclass
class GenerationPrompt:
    """Structured prompt for LLM generation"""
    context: str
    query: str
    format_instructions: str
    examples: List[str]

class KnowledgeBaseBuilder:
    """
    Knowledge base construction for LEED domain-specific information.
    Based on the research paper's metadata-aligned chunking strategy.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.embedding_model = embedding_model
        self.logger = logging.getLogger(__name__)
        
        if RAG_AVAILABLE:
            self.embedder = SentenceTransformer(embedding_model)
        else:
            self.embedder = None
            self.logger.warning("Sentence transformers not available. Install with: pip install sentence-transformers")
    
    def build_from_leed_credits(self, leed_credits_path: str) -> List[KnowledgeChunk]:
        """
        Build knowledge base from extracted LEED credits.
        Uses metadata-aligned chunking by credit unit.
        """
        chunks = []
        
        try:
            with open(leed_credits_path, 'r', encoding='utf-8') as f:
                credits = json.load(f)
            
            for credit in credits:
                # Create chunk for each credit
                chunk_text = self._format_credit_text(credit)
                metadata = {
                    'credit_code': credit.get('credit_code'),
                    'credit_name': credit.get('credit_name'),
                    'category': credit.get('category'),
                    'type': credit.get('credit_type'),
                    'points_min': credit.get('points_min'),
                    'points_max': credit.get('points_max'),
                    'version': credit.get('version', 'v4.1'),
                    'pages': credit.get('sources', {}).get('pages', [])
                }
                
                chunk = KnowledgeChunk(
                    text=chunk_text,
                    metadata=metadata
                )
                chunks.append(chunk)
                
        except Exception as e:
            self.logger.error(f"Error building knowledge base: {e}")
        
        return chunks
    
    def _format_credit_text(self, credit: Dict[str, Any]) -> str:
        """Format credit data into searchable text"""
        text_parts = []
        
        # Credit header
        credit_code = credit.get('credit_code', 'Unknown')
        credit_name = credit.get('credit_name', 'Unknown Credit')
        credit_type = credit.get('credit_type', 'Credit')
        
        text_parts.append(f"{credit_code} {credit_type}: {credit_name}")
        
        # Intent
        if credit.get('intent'):
            text_parts.append(f"Intent: {credit['intent']}")
        
        # Requirements
        if credit.get('requirements'):
            text_parts.append("Requirements:")
            for req in credit['requirements']:
                text_parts.append(f"- {req}")
        
        # Options
        if credit.get('options'):
            for option in credit['options']:
                text_parts.append(f"{option.get('heading', 'Option')}:")
                for line in option.get('lines', []):
                    text_parts.append(f"- {line}")
        
        # Documentation
        if credit.get('documentation'):
            text_parts.append("Submittals:")
            for doc in credit['documentation']:
                text_parts.append(f"- {doc}")
        
        # Applicability
        if credit.get('applicability'):
            text_parts.append("Applicability:")
            for app in credit['applicability']:
                text_parts.append(f"- {app}")
        
        return "\n".join(text_parts)
    
    def generate_embeddings(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Generate embeddings for knowledge chunks"""
        if not self.embedder:
            self.logger.error("Embedding model not available")
            return chunks
        
        for chunk in chunks:
            try:
                embedding = self.embedder.encode(chunk.text, convert_to_tensor=True)
                chunk.embedding = embedding.cpu().numpy()
            except Exception as e:
                self.logger.error(f"Error generating embedding: {e}")
        
        return chunks

class FAISSIndex:
    """
    FAISS-based vector storage and retrieval architecture.
    Based on the research paper's approximate nearest neighbor search.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.chunks = []
        self.logger = logging.getLogger(__name__)
    
    def build_index(self, chunks: List[KnowledgeChunk]) -> bool:
        """Build FAISS index from knowledge chunks"""
        try:
            if not chunks:
                return False
            
            # Filter chunks with embeddings
            valid_chunks = [chunk for chunk in chunks if chunk.embedding is not None]
            if not valid_chunks:
                self.logger.error("No chunks with embeddings found")
                return False
            
            # Create FAISS index
            embeddings = np.array([chunk.embedding for chunk in valid_chunks])
            self.index = IndexFlatIP(self.dimension)
            self.index.add(embeddings.astype('float32'))
            
            self.chunks = valid_chunks
            self.logger.info(f"Built FAISS index with {len(valid_chunks)} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building FAISS index: {e}")
            return False
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[RetrievalResult]:
        """Search for similar chunks"""
        try:
            if not self.index or not self.chunks:
                return []
            
            # Search FAISS index
            scores, indices = self.index.search(
                query_embedding.reshape(1, -1).astype('float32'), 
                k
            )
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.chunks):
                    result = RetrievalResult(
                        chunk=self.chunks[idx],
                        score=float(score),
                        rank=i + 1
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching FAISS index: {e}")
            return []
    
    def save_index(self, path: str) -> bool:
        """Save FAISS index to disk"""
        try:
            if not self.index:
                return False
            
            # Save FAISS index
            import faiss
            faiss.write_index(self.index, f"{path}.faiss")
            
            # Save chunks metadata
            chunks_data = []
            for chunk in self.chunks:
                chunks_data.append({
                    'text': chunk.text,
                    'metadata': chunk.metadata
                })
            
            with open(f"{path}.json", 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving index: {e}")
            return False
    
    def load_index(self, path: str) -> bool:
        """Load FAISS index from disk"""
        try:
            # Load FAISS index
            import faiss
            self.index = faiss.read_index(f"{path}.faiss")
            
            # Load chunks metadata
            with open(f"{path}.json", 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            self.chunks = []
            for chunk_data in chunks_data:
                chunk = KnowledgeChunk(
                    text=chunk_data['text'],
                    metadata=chunk_data['metadata']
                )
                self.chunks.append(chunk)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading index: {e}")
            return False

class Gemma3Generator:
    """
    Gemma3-based report generation with RAG integration.
    Based on the research paper's local deployment approach.
    """
    
    def __init__(self, model_name: str = "google/gemma-2-9b-it"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        if LLM_AVAILABLE:
            self._load_model()
        else:
            self.logger.warning("Transformers not available. Install with: pip install transformers torch")
    
    def _load_model(self):
        """Load Gemma3 model locally"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.logger.info(f"Loaded model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
    
    def generate_report(self, 
                       query: str,
                       retrieved_chunks: List[RetrievalResult],
                       credit_data: Dict[str, Any]) -> str:
        """
        Generate LEED credit report using RAG.
        Based on the research paper's structured prompt design.
        """
        try:
            if not self.model or not self.tokenizer:
                return "Model not available"
            
            # Build context from retrieved chunks
            context = self._build_context(retrieved_chunks)
            
            # Create structured prompt
            prompt = self._create_prompt(query, context, credit_data)
            
            # Generate response
            response = self._generate_response(prompt)
            
            # Post-process response
            return self._post_process_response(response, credit_data)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return f"Error generating report: {e}"
    
    def _build_context(self, retrieved_chunks: List[RetrievalResult]) -> str:
        """Build context from retrieved chunks"""
        context_parts = []
        
        for result in retrieved_chunks:
            context_parts.append(f"Reference {result.rank} (Score: {result.score:.3f}):")
            context_parts.append(result.chunk.text)
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str, credit_data: Dict[str, Any]) -> str:
        """Create structured prompt for generation"""
        prompt = f"""You are a LEED certification expert. Generate a comprehensive report for the following credit:

Credit: {credit_data.get('credit_code', 'Unknown')} {credit_data.get('credit_name', 'Unknown')}
Type: {credit_data.get('credit_type', 'Credit')}
Points: {credit_data.get('points_min', 0)}-{credit_data.get('points_max', 0)}

Query: {query}

Relevant LEED Reference Information:
{context}

Instructions:
1. Analyze the project data against LEED requirements
2. Determine compliance status and points earned
3. Provide specific recommendations for improvement
4. Include relevant calculations and justifications
5. Format the response as a professional LEED documentation

Generate a detailed, factual report based on the provided information:"""
        
        return prompt
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemma3 model"""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_length=2048,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the generated part (after the prompt)
            if prompt in response:
                response = response.split(prompt)[-1].strip()
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "Error generating response"
    
    def _post_process_response(self, response: str, credit_data: Dict[str, Any]) -> str:
        """Post-process and validate generated response"""
        # Add credit header
        header = f"# {credit_data.get('credit_code', 'Unknown')} {credit_data.get('credit_name', 'Unknown')}\n\n"
        
        # Basic validation
        if len(response) < 100:
            response = "Insufficient information to generate a complete report. Please provide more project details."
        
        return header + response

class LEEDReportGenerator:
    """
    Main report generation system combining RAG and LLM.
    Based on the research paper's end-to-end workflow.
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 llm_model: str = "google/gemma-2-9b-it"):
        self.kb_builder = KnowledgeBaseBuilder(embedding_model)
        self.faiss_index = FAISSIndex()
        self.generator = Gemma3Generator(llm_model)
        self.logger = logging.getLogger(__name__)
    
    def initialize_knowledge_base(self, leed_credits_path: str, index_path: str) -> bool:
        """Initialize knowledge base from LEED credits"""
        try:
            # Build knowledge base
            chunks = self.kb_builder.build_from_leed_credits(leed_credits_path)
            
            # Generate embeddings
            chunks = self.kb_builder.generate_embeddings(chunks)
            
            # Build FAISS index
            success = self.faiss_index.build_index(chunks)
            
            if success:
                # Save index
                self.faiss_index.save_index(index_path)
                self.logger.info(f"Knowledge base initialized with {len(chunks)} chunks")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error initializing knowledge base: {e}")
            return False
    
    def load_knowledge_base(self, index_path: str) -> bool:
        """Load existing knowledge base"""
        return self.faiss_index.load_index(index_path)
    
    def generate_credit_report(self, 
                             credit_code: str,
                             project_data: Dict[str, Any],
                             query: str) -> str:
        """Generate report for specific LEED credit"""
        try:
            # Create query embedding
            if not self.kb_builder.embedder:
                return "Embedding model not available"
            
            query_embedding = self.kb_builder.embedder.encode(query, convert_to_tensor=True)
            query_embedding = query_embedding.cpu().numpy()
            
            # Retrieve relevant chunks
            retrieved_chunks = self.faiss_index.search(query_embedding, k=5)
            
            if not retrieved_chunks:
                return "No relevant information found in knowledge base"
            
            # Generate report
            report = self.generator.generate_report(
                query=query,
                retrieved_chunks=retrieved_chunks,
                credit_data=project_data
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating credit report: {e}")
            return f"Error generating report: {e}"
    
    def generate_comprehensive_report(self, 
                                    project_data: Dict[str, Any],
                                    target_credits: List[str]) -> Dict[str, str]:
        """Generate comprehensive LEED report for multiple credits"""
        reports = {}
        
        for credit_code in target_credits:
            try:
                query = f"Analyze compliance for {credit_code} based on project data"
                
                report = self.generate_credit_report(
                    credit_code=credit_code,
                    project_data=project_data,
                    query=query
                )
                
                reports[credit_code] = report
                
            except Exception as e:
                self.logger.error(f"Error generating report for {credit_code}: {e}")
                reports[credit_code] = f"Error: {e}"
        
        return reports

def main():
    """Main function for testing the LLM-RAG module"""
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    generator = LEEDReportGenerator()
    
    # Initialize knowledge base
    leed_credits_path = "data/raw/leed_credits.json"
    index_path = "models/leed_knowledge_base"
    
    if os.path.exists(leed_credits_path):
        success = generator.initialize_knowledge_base(leed_credits_path, index_path)
        if success:
            print("Knowledge base initialized successfully!")
        else:
            print("Failed to initialize knowledge base")
    else:
        print("LEED credits file not found. Run credit extraction first.")
    
    print("LLM-RAG Module initialized successfully!")
    print("Ready for LEED report generation.")

if __name__ == "__main__":
    main() 