"""
KrishiMandal Serverless — Configuration
Reads from Lambda environment variables.
"""
import os


class Config:
    TABLE_NAME: str = os.environ.get("TABLE_NAME", "krishimandal-farm")
    EVENTS_BUS_NAME: str = os.environ.get("EVENTS_BUS_NAME", "krishimandal-events")
    S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
    EC2_FALLBACK_URL: str = os.environ.get("EC2_FALLBACK_URL", "http://100.27.155.251:8000")

    # Bedrock
    BEDROCK_MODEL_ID: str = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250514")
    BEDROCK_EMBEDDING_MODEL_ID: str = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    BEDROCK_GUARDRAIL_ID: str = os.environ.get("BEDROCK_GUARDRAIL_ID", "")

    # Pinecone
    PINECONE_API_KEY: str = os.environ.get("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = os.environ.get("PINECONE_INDEX", "krishimandal-knowledge")

    # OpenWeather
    OPENWEATHER_API_KEY: str = os.environ.get("OPENWEATHER_API_KEY", "")

    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")


config = Config()
