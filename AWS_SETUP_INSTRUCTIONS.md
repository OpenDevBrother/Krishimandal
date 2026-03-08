# KrishiMandal — AWS Deployment & Service Setup Guide

This document provides step-by-step instructions for setting up
all required AWS services to deploy the KrishiMandal multi-agent
platform in production.

---

## Prerequisites

- An **AWS Account** with billing enabled
- AWS CLI v2 installed and configured (`aws configure`)
- Python 3.11+
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- Region: **ap-south-1** (Mumbai) — closest to target users

---

## 1. Amazon Bedrock — Foundation Models

### 1.1 Enable Model Access

1. Go to **Amazon Bedrock Console** → **Model access**
2. Request access for:
   - `anthropic.claude-sonnet-4-5-20250514` (Claude Sonnet 4.5)
   - `amazon.nova-embed-multimodal-v1:0` (Nova Multimodal Embeddings)
3. Wait for approval (usually instant for Anthropic models)

### 1.2 Create Bedrock Guardrails

```bash
aws bedrock create-guardrail \
  --name "krishimandal-guardrail" \
  --description "Agricultural advisory safety guardrails" \
  --region ap-south-1 \
  --topic-policy-config '{
    "topicsConfig": [
      {
        "name": "non-agricultural-advice",
        "definition": "Medical, legal, financial investment, or political advice unrelated to farming",
        "type": "DENY",
        "examples": ["Should I invest in stocks?", "What medicine should I take?"]
      },
      {
        "name": "harmful-chemicals",
        "definition": "Recommendations for banned pesticides like DDT, endosulfan, monocrotophos",
        "type": "DENY",
        "examples": ["Use DDT on crops", "Apply endosulfan"]
      }
    ]
  }' \
  --content-policy-config '{
    "filtersConfig": [
      {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"}
    ]
  }' \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "PHONE_NUMBER", "action": "ANONYMIZE"},
      {"type": "EMAIL_ADDRESS", "action": "ANONYMIZE"},
      {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"}
    ]
  }' \
  --contextual-grounding-policy-config '{
    "filtersConfig": [
      {"type": "GROUNDING", "threshold": 0.7},
      {"type": "RELEVANCE", "threshold": 0.7}
    ]
  }' \
  --blocked-input-messaging "I can only help with farming-related questions." \
  --blocked-outputs-messaging "I cannot provide this information. Please contact your local KVK."
```

Note the `guardrailId` returned — add it to your `.env` file.

---

## 2. Amazon Bedrock Knowledge Bases (RAG)

### 2.1 Create the S3 Knowledge Bucket

```bash
aws s3 mb s3://krishimandal-knowledge-content --region ap-south-1
```

### 2.2 Upload Knowledge Content

Organize your content into the following S3 structure:

```
krishimandal-knowledge-content/
├── government-schemes/        # PM-KISAN, PMFBY, PM-KUSUM guidelines
├── crop-management/           # Pest control, irrigation, fertilizer guides
├── market-practices/          # Mandi procedures, grading standards
├── icar-bulletins/            # ICAR research summaries
├── state-agriculture/         # Maharashtra-specific extension materials
├── organic-farming/           # Organic certification and practices
├── water-management/          # Drip irrigation, rainwater harvesting
└── farmer-success-stories/    # Case studies in Hindi/Marathi
```

Upload documents (PDF, TXT, MD, DOCX, CSV, HTML supported):

```bash
aws s3 sync ./knowledge-content/ s3://krishimandal-knowledge-content/ --region ap-south-1
```

### 2.3 Create Knowledge Base

1. Go to **Amazon Bedrock Console** → **Knowledge bases** → **Create**
2. Configure:
   - Name: `krishimandal-agricultural-kb`
   - Embedding model: `Amazon Nova Multimodal Embeddings v1`
   - Dimensions: `1024`
   - Vector store: **OpenSearch Serverless** (auto-managed)
3. Add data source:
   - Type: **S3**
   - Bucket: `s3://krishimandal-knowledge-content`
   - Chunking strategy: **Semantic** (max 512 tokens)
4. Click **Create** and **Sync** the data source

Note the `knowledgeBaseId` — add it to your `.env` file.

### 2.4 Auto-Sync Setup

Content added to S3 is auto-synced. For manual re-sync:

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID \
  --region ap-south-1
```

---

## 3. Amazon Bedrock Agents (Multi-Agent Collaboration)

### 3.1 Create the Supervisor Agent

```bash
aws bedrock-agent create-agent \
  --agent-name "KrishiMandal-Supervisor" \
  --foundation-model "anthropic.claude-sonnet-4-5-20250514" \
  --instruction "You are KrishiMandal's agricultural intelligence supervisor.
You coordinate 6 specialized farming agents to help Indian smallholder farmers.
Analyze the farmer's query, determine which agents are needed, and synthesize
a clear, actionable response in the farmer's language.
For simple single-domain queries, route directly to the relevant agent.
For complex multi-domain queries, invoke multiple agents in parallel.
Always consider the farmer's profile, location, and current crop state." \
  --agent-collaboration "SUPERVISOR_ROUTER" \
  --guardrail-configuration '{
    "guardrailIdentifier": "YOUR_GUARDRAIL_ID",
    "guardrailVersion": "DRAFT"
  }' \
  --region ap-south-1
```

### 3.2 Create Sub-Agents

Create each sub-agent with its own instruction and action groups:

```bash
# Digital Twin Agent
aws bedrock-agent create-agent \
  --agent-name "KrishiMandal-DigitalTwin" \
  --foundation-model "anthropic.claude-sonnet-4-5-20250514" \
  --instruction "You manage virtual farm replicas for Indian farmers.
Provide farm status, weather, harvest predictions, risk alerts, and scenario simulations.
Always ground your answers in the farm's actual data." \
  --region ap-south-1

# Price Predictor Agent
aws bedrock-agent create-agent \
  --agent-name "KrishiMandal-PricePredictor" \
  --foundation-model "anthropic.claude-sonnet-4-5-20250514" \
  --instruction "You forecast mandi crop prices and advise sell/store decisions.
Provide current prices, 7-day and 30-day forecasts, best mandi suggestions,
and net realisation calculations. Always cite data sources." \
  --region ap-south-1

# Repeat for: CropManagement, SchemeCredit, SupplyChain, LearningPlatform
```

### 3.3 Associate Sub-Agents with Supervisor

```bash
aws bedrock-agent associate-agent-collaborator \
  --agent-id SUPERVISOR_AGENT_ID \
  --agent-descriptor '{"aliasArn": "SUB_AGENT_ALIAS_ARN"}' \
  --collaboration-instruction "Route farm status, weather, harvest, and simulation queries here." \
  --agent-version "DRAFT" \
  --region ap-south-1
```

### 3.4 Attach Action Groups (Lambda Functions)

Each sub-agent needs Lambda-backed action groups. Deploy them:

```bash
# Package and deploy each agent's Lambda
sam build
sam deploy --guided --stack-name krishimandal-agents --region ap-south-1
```

Then attach the Lambda ARN to each agent as an action group:

```bash
aws bedrock-agent create-agent-action-group \
  --agent-id SUB_AGENT_ID \
  --action-group-name "farm-operations" \
  --action-group-executor '{"lambda": "LAMBDA_ARN"}' \
  --api-schema '{"s3": {"s3BucketName": "krishimandal-schemas", "s3ObjectKey": "agent-api-schema.json"}}' \
  --region ap-south-1
```

### 3.5 Prepare and Create Aliases

```bash
aws bedrock-agent prepare-agent --agent-id AGENT_ID --region ap-south-1
aws bedrock-agent create-agent-alias \
  --agent-id AGENT_ID \
  --agent-alias-name "production" \
  --region ap-south-1
```

---

## 4. AWS Lambda Functions

### 4.1 Create IAM Role

```bash
aws iam create-role \
  --role-name KrishiMandalLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy --role-name KrishiMandalLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name KrishiMandalLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name KrishiMandalLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam attach-role-policy --role-name KrishiMandalLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

### 4.2 Deploy via SAM

Create a `template.yaml` in the project root for SAM deployment.
Each agent becomes a Lambda function triggered by API Gateway + EventBridge.

---

## 5. Amazon API Gateway

```bash
aws apigateway create-rest-api \
  --name "KrishiMandal-API" \
  --description "API for KrishiMandal platform" \
  --endpoint-configuration '{"types": ["REGIONAL"]}' \
  --region ap-south-1
```

Configure routes:
- `POST /query` → Supervisor Lambda
- `GET /farm/{farmerId}` → Digital Twin Lambda
- `GET /price/{crop}` → Price Predictor Lambda
- `GET /farm/{farmerId}/schemes` → Scheme Credit Lambda
- `POST /rag/ask` → Learning Platform Lambda

Enable WAF for production.

---

## 6. Database Setup

### 6.1 Amazon DynamoDB (Sessions & Events)

```bash
aws dynamodb create-table \
  --table-name krishimandal-sessions \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=farmer_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --global-secondary-indexes '[{
    "IndexName": "farmer-index",
    "KeySchema": [{"AttributeName": "farmer_id", "KeyType": "HASH"}],
    "Projection": {"ProjectionType": "ALL"},
    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
  }]' \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region ap-south-1

aws dynamodb create-table \
  --table-name krishimandal-events \
  --attribute-definitions \
    AttributeName=event_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=event_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region ap-south-1
```

### 6.2 Amazon RDS PostgreSQL (Farm Data, Schemes)

```bash
aws rds create-db-instance \
  --db-instance-identifier krishimandal-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password YOUR_SECURE_PASSWORD \
  --allocated-storage 20 \
  --region ap-south-1
```

### 6.3 Amazon ElastiCache Redis (Caching)

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id krishimandal-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --region ap-south-1
```

---

## 7. Amazon EventBridge (Event-Driven Workflows)

```bash
# Create custom event bus
aws events create-event-bus --name krishimandal-events --region ap-south-1

# Rule: Harvest predicted → trigger Supply Chain + Price Predictor
aws events put-rule \
  --name "harvest-predicted" \
  --event-bus-name krishimandal-events \
  --event-pattern '{
    "source": ["krishimandal.digital-twin"],
    "detail-type": ["HARVEST_PREDICTED"],
    "detail": {"days_until_harvest": [{"numeric": ["<=", 14]}]}
  }' \
  --region ap-south-1

# Rule: Pest alert → trigger Learning Platform
aws events put-rule \
  --name "pest-alert" \
  --event-bus-name krishimandal-events \
  --event-pattern '{
    "source": ["krishimandal.crop-management"],
    "detail-type": ["PEST_ALERT"]
  }' \
  --region ap-south-1
```

Add Lambda targets to each rule:

```bash
aws events put-targets \
  --rule "harvest-predicted" \
  --event-bus-name krishimandal-events \
  --targets '[
    {"Id": "supply-chain-lambda", "Arn": "SUPPLY_CHAIN_LAMBDA_ARN"},
    {"Id": "price-predictor-lambda", "Arn": "PRICE_PREDICTOR_LAMBDA_ARN"}
  ]' \
  --region ap-south-1
```

---

## 8. Amazon S3 Buckets

```bash
# Knowledge content (RAG source)
aws s3 mb s3://krishimandal-knowledge-content --region ap-south-1

# Farm documents (uploaded photos, scanned docs)
aws s3 mb s3://krishimandal-farm-documents --region ap-south-1

# Static web app
aws s3 mb s3://krishimandal-webapp --region ap-south-1

# Satellite imagery cache
aws s3 mb s3://krishimandal-satellite-data --region ap-south-1
```

Enable versioning and encryption:

```bash
aws s3api put-bucket-versioning \
  --bucket krishimandal-farm-documents \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket krishimandal-farm-documents \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'
```

---

## 9. Amazon Cognito (Authentication)

```bash
aws cognito-idp create-user-pool \
  --pool-name "KrishiMandal-Users" \
  --auto-verified-attributes "phone_number" \
  --sms-authentication-message "Your KrishiMandal OTP is {####}" \
  --mfa-configuration "OPTIONAL" \
  --region ap-south-1

aws cognito-idp create-user-pool-client \
  --user-pool-id USER_POOL_ID \
  --client-name "krishimandal-web" \
  --explicit-auth-flows "ALLOW_USER_SRP_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" \
  --region ap-south-1
```

---

## 10. Twilio Setup (Voice / SMS / WhatsApp)

1. Create a Twilio account at [twilio.com](https://www.twilio.com)
2. Purchase an Indian toll-free number or use a US number for testing
3. Configure webhooks:
   - Voice URL: `https://YOUR_API_GATEWAY/ivr/incoming`
   - SMS URL: `https://YOUR_API_GATEWAY/sms/incoming`
4. Enable WhatsApp Business API via Twilio
5. Set up WhatsApp sandbox for testing:
   - Go to **Twilio Console** → **Messaging** → **WhatsApp Sandbox**
   - Configure webhook: `https://YOUR_API_GATEWAY/whatsapp/incoming`
6. Add credentials to `.env`:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=your_phone_number
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```

---

## 11. Sarvam AI Setup (STT / TTS)

1. Sign up at [sarvam.ai](https://www.sarvam.ai)
2. Get an API key from the dashboard
3. Add to `.env`:
   ```
   SARVAM_AI_API_KEY=your_api_key
   SARVAM_AI_BASE_URL=https://api.sarvam.ai/v1
   ```
4. Test with:
   ```bash
   curl -X POST https://api.sarvam.ai/v1/speech-to-text \
     -H "Authorization: Bearer YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"audio_url": "https://example.com/test.wav", "language_code": "auto", "model": "saaras:v3"}'
   ```

---

## 12. Monitoring & Observability

### CloudWatch Alarms

```bash
# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "krishimandal-lambda-errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region ap-south-1

# API Gateway 5xx alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "krishimandal-api-5xx" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region ap-south-1
```

### X-Ray Tracing

Enable in Lambda configuration:

```bash
aws lambda update-function-configuration \
  --function-name krishimandal-supervisor \
  --tracing-config Mode=Active \
  --region ap-south-1
```

---

## 13. Local Development

### Run the API Server Locally

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Copy environment file
copy .env.example .env
# Edit .env with your API keys (or leave USE_DUMMY_DATA=true for testing)

# 3. Run FastAPI server
uvicorn src.app:app --reload --port 8000

# 4. Test
curl http://localhost:8000/
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the price of wheat?", "farmer_id": "F1001"}'
```

### Run the Interactive CLI Demo

```bash
python -m src.demo
```

---

## 14. Cost Estimates (Pilot — 10,000 Farmers)

| Service                  | Monthly Estimate |
|--------------------------|----------------:|
| Amazon Bedrock (Claude)  |         ~$500   |
| Bedrock Knowledge Bases  |         ~$100   |
| AWS Lambda               |          ~$50   |
| API Gateway              |          ~$30   |
| DynamoDB                 |          ~$25   |
| RDS PostgreSQL (t3.micro)|          ~$15   |
| ElastiCache Redis        |          ~$15   |
| S3 Storage               |          ~$10   |
| CloudFront               |           ~$5   |
| Twilio Voice/SMS         |    ~$200-500    |
| Sarvam AI                |    ~$100-300    |
| **Total**                |  **~$1,050-1,550** |

---

## Quick Reference — Environment Variables

See `.env.example` in the project root for all required variables.
Key ones to set:

```env
AWS_REGION=ap-south-1
BEDROCK_GUARDRAIL_ID=<from step 1.2>
BEDROCK_KNOWLEDGE_BASE_ID=<from step 2.3>
SARVAM_AI_API_KEY=<from step 11>
TWILIO_ACCOUNT_SID=<from step 10>
TWILIO_AUTH_TOKEN=<from step 10>
USE_DUMMY_DATA=false  # set to true for local testing without APIs
```
