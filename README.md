# ConversationalIVR

**AI-Powered Parking & Toll Violation IVR System**

An AI-powered Interactive Voice Response (IVR) system built on AWS using Amazon Connect, Amazon Lex V2, Amazon Q in Connect with Nova Sonic, and Bedrock AgentCore Gateway.

Callers can look up violations by license plate, citation number, or account; check balances; get violation details; submit disputes; and make payments — all through natural conversation with an AI agent.

## Architecture

Customer (Phone) | v Amazon Connect (IVR Flow) | v Amazon Lex V2 (ParkAndTollBot) <--> Amazon Q in Connect (Nova Sonic LLM) | | v v Fulfillment Lambda Bedrock AgentCore Gateway | | v v Connect Flow Routing Tool Lambdas (via API Gateway) | - lookupByPlate / Citation / Account v - getBalance, getViolationDetails Payment Flow (if needed) - submitDispute, checkDisputeStatus | - buildPaymentCart, initiatePayment v - ESCALATE / RETRIEVE Amazon Lex V2 (PaymentCollectionBot) | v Resume AI Conversation

## Project Structure

ConversationalIVR/ ├── cfn/ # CloudFormation templates │ ├── standalone/ # Independently deployable stacks │ └── nested/ # Nested stack templates ├── lambdas/ # Lambda function source code (16) │ ├── tool-lambdas/ # AI agent tool functions (7) │ ├── fulfillment/ # Lex fulfillment hook (1) │ ├── payment/ # Payment flow functions (6) │ └── connect/ # Connect integration (2) ├── scripts/ # Deployment and bot creation scripts │ └── utilities/ # Data seeding, validation helpers ├── connect-flows/ # Amazon Connect contact flows (JSON) ├── openapi/ # API Gateway OpenAPI specification ├── ai-agent/ # AI agent system prompt ├── knowledge-base/ # Knowledge base content for RETRIEVE tool ├── config/ # Environment parameter templates ├── iam-reference/ # IAM policy snapshots from live environment ├── docs/ # Architecture, deployment, troubleshooting └── tests/ # Unit and integration tests

## Prerequisites

- AWS CLI v2 with configured credentials
- AWS Account with Amazon Connect, Lex V2, Q in Connect, Bedrock (Nova Sonic), AgentCore
- Python 3.12+
- Node.js 20.x+ (for one Lambda)

## Quick Start

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS account details

    Deploy CloudFormation stacks:

    ./scripts/deploy-all.sh

    Create Lex bots:

    ./scripts/create-park-and-toll-bot.sh
    ./scripts/create-payment-bot.sh

    Complete post-deployment steps: See docs/MANUAL_POST_DEPLOYMENT_STEPS.md for the full 16-step checklist.

Lambda Functions (16)
#	Function	Category	Description
1	lookup-by-plate	Tool	Look up customer by license plate
2	lookup-by-citation	Tool	Look up violation by citation number
3	lookup-by-account	Tool	Look up customer by account number
4	get-balance	Tool	Get account balance
5	get-violation-details	Tool	Get violation details
6	submit-dispute	Tool	Submit a dispute
7	check-dispute-status	Tool	Check dispute status
8	qinconnect-dialog-hook	Fulfillment	Lex fulfillment - detects payment routing
9	build-payment-cart	Payment Tool	Build payment cart from violations
10	initiate-payment	Payment Tool	Initiate payment process
11	seed-payment-session	Payment	Seed Lex session for PaymentCollectionBot
12	payment-processing	Payment	Process card payment (Lex fulfillment)
13	update-violation-balance	Payment	Update violation balance after payment
14	save-and-restore-session	Payment	Preserve AI context across payment flow
15	get-call-attributes	Connect	Get call attributes from Connect
16	connect-assistant-update-session	Connect	Update Q in Connect session data
CloudFormation Stacks (Deployment Order)
Order	Template	Resources
1a	01a-client-config-table	Client config DynamoDB table
1b	01b-dynamodb-tables	Customers, violations, disputes tables
1c	01c-session-table	Session context table
2a	02a-tool-lambdas	7 AI agent tool Lambdas + IAM
2b	02b-getCallAttributes	Call attributes Lambda
2c	02c-ConnectAssistantUpdateSessionData	Q in Connect session update Lambda
2d	02d-payments-lambdas	buildPaymentCart, initiatePayment Lambdas
2e	02e-payment-handoff-resources	4 payment handoff Lambdas
2f	02f-fulfillment-hook	QinConnect fulfillment Lambda
3	03-api-gateway	REST API + endpoints + API key
Key Design Decisions

    Fulfillment-based payment routing: QinConnect fulfillment hook detects payment intent via session attributes (Tool=Escalate, escalationReason=PAYMENT_TRANSFER) as fallback when AI response text is unavailable
    PCI compliance: PaymentCollectionBot disables conversation logs; card slots use obfuscation
    Session continuity: SaveAndRestoreSession Lambda preserves AI context across the payment flow interruption
    Idempotent bot scripts: Bot creation scripts check for existing resources before creating

Documentation

    Architecture Overview
    Deployment Guide
    Lambda Handler Mapping
    Troubleshooting
    Post-Deployment Steps

Security

    No AWS account IDs, ARNs, or credentials are stored in this repository
    All environment-specific values use placeholders — configure via .env
    Run ./scripts/utilities/sanitize-check.sh before committing to verify

License

MIT EOF echo " OK"
-------------------------------------------------------------------
2. Fix docs/lambda-handlers.md
-------------------------------------------------------------------

echo ">>> Rewriting docs/lambda-handlers.md"

cat > "${REPO_ROOT}/docs/lambda-handlers.md" << 'EOF'
Lambda Handler Mapping Reference

This document maps each Lambda function to its correct handler configuration.
Lambda Function	Handler	Source File	Runtime
get-call-attributes	index.lambda_handler	index.py	python3.12
connect-assistant-update-session	index.handler	index.js	nodejs20.x
lookup-by-plate	index.lambda_handler	index.py	python3.12
lookup-by-citation	index.lambda_handler	index.py	python3.12
lookup-by-account	index.lambda_handler	index.py	python3.12
get-balance	index.lambda_handler	index.py	python3.12
get-violation-details	index.lambda_handler	index.py	python3.12
submit-dispute	index.lambda_handler	index.py	python3.12
check-dispute-status	index.lambda_handler	index.py	python3.12
qinconnect-dialog-hook	lambda_function.lambda_handler	lambda_function.py	python3.12
build-payment-cart	build_payment_cart.lambda_handler	build_payment_cart.py	python3.12
initiate-payment	initiate_payment.lambda_handler	initiate_payment.py	python3.12
seed-payment-session	seed_session.lambda_handler	seed_session.py	python3.12
payment-processing	index.lambda_handler	index.py	python3.12
update-violation-balance	index.lambda_handler	index.py	python3.12
save-and-restore-session	index.lambda_handler	index.py	python3.12
Important Notes

    Handler format: <module_name>. where module name = filename without .py/.js
    CloudFormation ZipFile inline code creates the file using the module name from the handler
    Only connect-assistant-update-session uses Node.js; all others use Python 3.12 EOF echo " OK"

-------------------------------------------------------------------
3. Fix docs/architecture.md
-------------------------------------------------------------------

echo ">>> Rewriting docs/architecture.md"

cat > "${REPO_ROOT}/docs/architecture.md" << 'EOF'
Architecture Overview
Components
Amazon Connect

    IVR entry point for inbound calls
    Contact flows orchestrate AI conversation and payment collection
    Session attributes pass context between components

Amazon Lex V2

ParkAndTollBot — Primary conversational bot

    AmazonQInConnectIntent with fulfillment code hook enabled
    Fulfillment Lambda detects payment routing signals
    Post-fulfillment returns ((x-amz-lex:q-in-connect-response))

PaymentCollectionBot — PCI card collection

    Slots: cardNumber (obfuscated), expirationDate (obfuscated), cvv (obfuscated), billingZip
    Conversation logs disabled for PCI compliance
    Intents: CollectPayment, CancelPayment, FallbackIntent

Amazon Q in Connect (Nova Sonic)

    AI conversational intelligence via system prompt
    Invokes tools through Bedrock AgentCore Gateway
    Supports RETRIEVE (knowledge base) and ESCALATE (transfer) actions

Bedrock AgentCore Gateway

    Routes tool calls from Q in Connect to API Gateway
    API key authentication
    OpenAPI spec defines all available tools

API Gateway

    REST API with 9 POST endpoints
    API key required for all requests
    Each endpoint backed by a dedicated Lambda

DynamoDB Tables
Table	PK	Purpose
customers	PK + SK	Customer records (GSIs: plate, account)
violations	PK + SK	Violation records (GSIs: citation, customer)
disputes	PK + SK	Dispute records (GSIs: violation, reference)
client-config	PK	Phone number mapping
session-context	contactId	IVR session state
Payment Flow Sequence

    AI determines payment is needed
    AI calls initiatePayment tool — sets session attributes
    AI calls Escalate(PAYMENT_TRANSFER) — signals handoff
    Fulfillment Lambda detects payment signal (text or session attrs)
    Returns dialogAction to Connect flow with routing signal
    Connect invokes SeedPaymentSession — primes PaymentCollectionBot
    Connect routes to PaymentCollectionBot for card collection
    PaymentProcessing Lambda processes the payment
    SaveAndRestoreSession Lambda restores AI context
    Connect returns caller to ParkAndTollBot for continued conversation EOF echo " OK"

-------------------------------------------------------------------
4. Fix docs/troubleshooting.md
-------------------------------------------------------------------

echo ">>> Rewriting docs/troubleshooting.md"

cat > "${REPO_ROOT}/docs/troubleshooting.md" << 'EOF'
Troubleshooting Guide
Common Issues
Call goes directly to "Thank you for calling. Goodbye"

Cause: FulfillmentCodeHook enabled on ParkAndTollBot but bot alias has no Lambda configured. Fix: Configure botAliasLocaleSettings with the QinConnectDialogHook Lambda ARN.
Fulfillment Lambda fires but payment bot not invoked

Cause: x-amz-lex:q-in-connect-response returns "..." instead of full text. Fix: Use session attribute fallback detection (Tool=Escalate + escalationReason=PAYMENT_TRANSFER).
DynamoDB AccessDeniedException in fulfillment Lambda

Cause: Lambda role missing dynamodb:Query and dynamodb:Scan permissions. Fix: Add inline policy for session table access.
SeedPaymentSession Lex PutSession AccessDeniedException

Cause: Lambda role missing lex:PutSession for PaymentCollectionBot. Fix: Add LexPaymentBotAccess inline policy.
Lex can't invoke fulfillment Lambda

Cause: Missing Lambda resource-based policy for lexv2.amazonaws.com. Fix: Add lambda:InvokeFunction permission for Lex principal.
Key Rule: Lex V2 Fulfillment Requires 3 Things

    fulfillmentCodeHook.enabled=true on the intent
    botAliasLocaleSettings with Lambda ARN on the alias
    Resource-based policy on the Lambda for lexv2.amazonaws.com

Missing any one of these causes silent failure — the call drops or goes to goodbye. EOF echo " OK"
-------------------------------------------------------------------
5. Fix docs/deployment-guide.md
-------------------------------------------------------------------

echo ">>> Rewriting docs/deployment-guide.md"

cat > "${REPO_ROOT}/docs/deployment-guide.md" << 'EOF'
Deployment Guide
Prerequisites

    AWS CLI v2 configured with appropriate credentials
    Python 3.12+, Node.js 20.x+
    Amazon Connect instance created
    Bedrock model access enabled (Nova Sonic)

Step 1: Configure Environment

cp .env.example .env
# Edit .env with your AWS account details

Step 2: Deploy CloudFormation Stacks

Deploy in order using the master script:

./scripts/deploy-all.sh

Or deploy individually:

# 1. DynamoDB Tables
aws cloudformation deploy --template-file cfn/standalone/01a-client-config-table.yaml --stack-name anycompany-ivr-client-config-dev ...
aws cloudformation deploy --template-file cfn/standalone/01b-dynamodb-tables.yaml --stack-name anycompany-ivr-tables-dev ...
aws cloudformation deploy --template-file cfn/standalone/01c-session-table.yaml --stack-name anycompany-ivr-session-dev ...

# 2. Lambda Functions
aws cloudformation deploy --template-file cfn/standalone/02a-tool-lambdas.yaml --stack-name anycompany-ivr-tools-dev ...
aws cloudformation deploy --template-file cfn/standalone/02b-getCallAttributes.yaml ...
aws cloudformation deploy --template-file cfn/standalone/02c-ConnectAssistantUpdateSessionData.yaml ...
aws cloudformation deploy --template-file cfn/standalone/02d-payments-lambdas.yaml ...
aws cloudformation deploy --template-file cfn/standalone/02e-payment-handoff-resources.yaml ...
aws cloudformation deploy --template-file cfn/standalone/02f-fulfillment-hook.yaml ...

# 3. API Gateway
aws cloudformation deploy --template-file cfn/standalone/03-api-gateway.yaml --stack-name anycompany-ivr-api-dev ...

Step 3: Create Lex Bots

./scripts/create-park-and-toll-bot.sh
./scripts/create-payment-bot.sh

Step 4: Post-Deployment Configuration

See MANUAL_POST_DEPLOYMENT_STEPS.md for the complete 16-step checklist.
Step 5: Seed Test Data

python scripts/utilities/seed_test_data.py
python scripts/utilities/seed_client_config.py

Step 6: End-to-End Test

Call the phone number associated with your Connect instance and test:

    License plate lookup
    Citation lookup
    Balance inquiry
    Payment flow
    Dispute submission EOF echo " OK"

-------------------------------------------------------------------
6. Fix CHANGELOG.md
-------------------------------------------------------------------

echo ">>> Rewriting CHANGELOG.md"

cat > "${REPO_ROOT}/CHANGELOG.md" << 'EOF'
Changelog

All notable changes to the ConversationalIVR project.
[1.0.0] - 2026-03-24
Initial Release

    AI-powered IVR conversation using Nova Sonic via Amazon Q in Connect
    7 AI agent tools (customer lookup, balance, violations, disputes)
    Payment collection flow with PCI-compliant card handling
    16 Lambda functions (Python 3.12 + Node.js 20.x)
    13+ CloudFormation templates (standalone + nested)
    Automated Lex bot creation scripts (ParkAndTollBot, PaymentCollectionBot)
    Amazon Connect contact flow with payment routing
    Bedrock AgentCore Gateway integration
    REST API Gateway with OpenAPI specification
    DynamoDB tables for customers, violations, disputes, sessions
    Comprehensive deployment and troubleshooting documentation

Known Behaviors

    x-amz-lex:q-in-connect-response may return "..." instead of full text in some environments. Workaround: session attribute-based fallback detection in fulfillment Lambda. EOF echo " OK"

-------------------------------------------------------------------
7. Fix sanitize-check.sh
-------------------------------------------------------------------

echo ">>> Rewriting scripts/utilities/sanitize-check.sh"

cat > "${REPO_ROOT}/scripts/utilities/sanitize-check.sh" << 'EOF' #!/bin/bash
Pre-commit secret scanner for ConversationalIVR project
Usage: ./scripts/utilities/sanitize-check.sh

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)" ERRORS=0 SAFE="123456789012|111111111111|PLACEHOLDER|REPLACE_WITH|xxxxxxxx|XXXXXXXXXX|your-|000000000000|example"

echo "Scanning for secrets in ${REPO_ROOT}..." echo ""

echo "--- [1/5] AWS Account IDs ---" F=$(grep -rn '[0-9]{12}' "${REPO_ROOT}" --include=".py" --include=".js" --include=".json" --include=".yaml" --include="*.sh" --exclude-dir=.git 2>/dev/null | grep -Ev "${SAFE}|sanitize-check" | grep -E '[0-9]{12}' || true) if [ -n "$F" ]; then echo " WARNING:"; echo "$F"; ERRORS=$((ERRORS+1)); else echo " OK"; fi

echo "--- [2/5] Hardcoded ARNs ---" F=$(grep -rn 'arn:aws:' "${REPO_ROOT}" --include=".py" --include=".js" --include="*.sh" --exclude-dir=.git 2>/dev/null | grep -Ev "${SAFE}|# ARN" || true) if [ -n "$F" ]; then echo " WARNING:"; echo "$F"; ERRORS=$((ERRORS+1)); else echo " OK"; fi

echo "--- [3/5] .env files ---" F=$(find "${REPO_ROOT}" -name ".env" -not -name ".env.example" -not -path "/.git/" 2>/dev/null || true) if [ -n "$F" ]; then echo " WARNING:"; echo "$F"; ERRORS=$((ERRORS+1)); else echo " OK"; fi

echo "--- [4/5] UUIDs in source ---" F=$(grep -rn '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' "${REPO_ROOT}" --include=".py" --include=".js" --include="*.sh" --exclude-dir=.git 2>/dev/null | grep -Ev "${SAFE}" || true) if [ -n "$F" ]; then echo " WARNING:"; echo "$F"; ERRORS=$((ERRORS+1)); else echo " OK"; fi

echo "--- [5/5] S3 buckets with account IDs ---" F=$(grep -rn 's3://.[0-9]{12}' "${REPO_ROOT}" --include=".py" --include=".js" --include=".yaml" --include="*.sh" --exclude-dir=.git 2>/dev/null | grep -Ev "${SAFE}" || true) if [ -n "$F" ]; then echo " WARNING:"; echo "$F"; ERRORS=$((ERRORS+1)); else echo " OK"; fi

echo "" if [ $ERRORS -gt 0 ]; then echo "FAILED: ${ERRORS} issue(s) found. Fix before committing." exit 1 else echo "PASSED: No secrets detected." exit 0 fi EOF chmod +x "${REPO_ROOT}/scripts/utilities/sanitize-check.sh" echo " OK"
-------------------------------------------------------------------
8. Fix placeholder READMEs
-------------------------------------------------------------------

echo ">>> Rewriting placeholder READMEs"

cat > "${REPO_ROOT}/knowledge-base/README.md" << 'EOF'
Knowledge Base Content

Place knowledge base documents here for the Amazon Q in Connect RETRIEVE tool.
Expected Content

    Parking violation policies and procedures
    Toll violation policies and procedures
    Payment and dispute resolution guidelines
    FAQ documents

Upload

Upload files to the S3 bucket configured as KB_BUCKET in your .env file. EOF

cat > "${REPO_ROOT}/test-data/README.md" << 'EOF'
Test Data

Seed DynamoDB tables with test data:

python scripts/utilities/seed_test_data.py
python scripts/utilities/seed_client_config.py

