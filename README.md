📌 IntelliDoc AI

(⚠️ Project is currently under active development — features, code structure, and documentation are being refined.)

IntelliDoc AI is an intelligent document-processing system designed to automate text extraction, classification, summarization, and report generation using advanced AI/LLM models.
It supports modular pipelines, microservices via Docker, and seamless integration with Hugging Face models.

🚀 Features

🔍 Document Upload System
Supports PDF, DOCX, TXT and converts them into standardized text format.

🧠 AI-Powered Text Extraction & Understanding
Uses multi-stage pipelines for OCR, chunking, classification, and semantic interpretation.

🤖 Hugging Face Model Integration
Fully authenticated HF Hub connection (via hf auth login).
Supports downloading, loading, and fine-tuning LLMs.

📄 Summarization / Q&A / Metadata Extraction
Generates structured outputs suitable for enterprise workflows.

🐳 Full Docker Support
Easy containerized deployment with:

docker-compose.yml

Separate containers for backend, worker, and model service (if needed)

⚡ FastAPI Backend (Work in Progress)
REST endpoints for document processing, model inference, and pipeline orchestration.
