                  Streamlit Frontend
                           |
                           v
                    n8n Webhook API
                           |
                   AI Decision Agent
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
  Policy Tool      Receipt Tool      Limit Tool
        |                  |                  |
        +------------------+------------------+
                           |
                    Duplicate Check
                           |
                           v
                   Final LLM Reasoning
                           |
                           v
                   Structured JSON






  Streamlit Frontend
                            |
                            v
                    Python Backend API
                            |
            +---------------+----------------+
            |                                |
            v                                v
        OCR Service                    n8n Workflow
            |                                |
            +---------------+----------------+
                            |
                            v
                    Decision Agent
                            |
                            v
                    Structured Output



PaddleOCR