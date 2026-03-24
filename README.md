# ConversationalIVR

**AI-Powered Parking & Toll Violation IVR System**

An AI-powered Interactive Voice Response (IVR) system built on AWS using Amazon Connect, Amazon Lex V2, Amazon Q in Connect with Nova Sonic, and Bedrock AgentCore Gateway.

Callers can look up violations by license plate, citation number, or account; check balances; get violation details; submit disputes; and make payments — all through natural conversation with an AI agent.

---

## Architecture

```
Customer (Phone)
       |
       v
Amazon Connect (IVR Flow)
       |
       v
Amazon Lex V2 (ParkAndTollBot) <---> Amazon Q in Connect (Nova Sonic LLM)
       |                                           |
       v                                           v
Fulfillment Lambda                    Bedrock AgentCore Gateway
       |                                           |
       v                                           v
Connect Flow Routing                  Tool Lambdas (via API Gateway)
       |                               - lookupByPlate / Citation / Account
       v                               - getBalance, getViolationDetails
Payment Flow (if needed)               - submitDispute, checkDisputeStatus
       |                               - buildPaymentCart, initiatePayment
       v                               - ESCALATE / RETRIEVE
Amazon Lex V2 (PaymentCollectionBot)
       |
       v
Resume AI Conversation
```

---

## Project Structure

```
ConversationalIVR/
├── cfn/                        # CloudFormation templates
│   ├── standalone/             # Independently deployable stacks
│   └── nested/                 # Nested stack templates
├── lambdas/                    # Lambda function source code (16)
│   ├── tool-lambdas/           # AI agent tool functions (7)
│   ├── fulfillment/            # Lex fulfillment hook (1)
│   ├── payment/                # Payment flow functions (6)
│   └── connect/                # Connect integration (2)
├── scripts/                    # Deployment and bot creation scripts
│   └── utilities/              # Data seeding, validation helpers
├── connect-flows/              # Amazon Connect contact flows (JSON)
├── openapi/                    # API Gateway OpenAPI specification
├── ai-agent/                   # AI agent system prompt
├── knowledge-base/             # Knowledge base content for RETRIEVE tool
├── config/                     # Environment parameter templates
├── iam-reference/              # IAM policy snapshots from live environment
├── docs/                       # Architecture, deployment, troubleshooting
└── tests/                      # Unit and integration tests
```

---

## Prerequisites

- AWS CLI v2 with configured credentials
- AWS Account with Amazon Connect, Lex V2, Q in Connect, Bedrock (Nova Sonic), AgentCore
- Python 3.12+
- Node.js 20.x+ (for one Lambda)

---

## Quick Start

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS account details
   ```

2. **Deploy CloudFormation stacks:**
   ```bash
   ./scripts/deploy-all.sh
   ```

3. **Create Lex bots:**
   ```bash
   ./scripts/create-park-and-toll-bot.sh
   ./scripts/create-payment-bot.sh
   ```

4. **Complete post-deployment steps:**
   See [docs/MANUAL_POST_DEPLOYMENT_STEPS.md](docs/MANUAL_POST_DEPLOYMENT_STEPS.md) for the full 16-step checklist.

---

## Lambda Functions (16)

| # | Function | Category | Description |
|---|----------|----------|-------------|
| 1 | lookup-by-plate | Tool | Look up customer by license plate |
| 2 | lookup-by-citation | Tool | Look up violation by citation number |
| 3 | lookup-by-account | Tool | Look up customer by account number |
| 4 | get-balance | Tool | Get account balance |
| 5 | get-violation-details | Tool | Get violation details |
| 6 | submit-dispute | Tool | Submit a dispute |
| 7 | check-dispute-status | Tool | Check dispute status |
| 8 | qinconnect-dialog-hook | Fulfillment | Lex fulfillment — detects payment routing |
| 9 | build-payment-cart | Payment Tool | Build payment cart from violations |
| 10 | initiate-payment | Payment Tool | Initiate payment process |
| 11 | seed-payment-session | Payment | Seed Lex session for PaymentCollectionBot |
| 12 | payment-processing | Payment | Process card payment (Lex fulfillment) |
| 13 | update-violation-balance | Payment | Update violation balance after payment |
| 14 | save-and-restore-session | Payment | Preserve AI context across payment flow |
| 15 | get-call-attributes | Connect | Get call attributes from Connect |
| 16 | connect-assistant-update-session | Connect | Update Q in Connect session data |

---

## CloudFormation Stacks (Deployment Order)

| Order | Template | Resources |
|-------|----------|-----------|
| 1a | 01a-client-config-table | Client config DynamoDB table |
| 1b | 01b-dynamodb-tables | Customers, violations, disputes tables |
| 1c | 01c-session-table | Session context table |
| 2a | 02a-tool-lambdas | 7 AI agent tool Lambdas + IAM |
| 2b | 02b-getCallAttributes | Call attributes Lambda |
| 2c | 02c-ConnectAssistantUpdateSessionData | Q in Connect session update Lambda |
| 2d | 02d-payments-lambdas | buildPaymentCart, initiatePayment Lambdas |
| 2e | 02e-payment-handoff-resources | 4 payment handoff Lambdas |
| 2f | 02f-fulfillment-hook | QinConnect fulfillment Lambda |
| 3 | 03-api-gateway | REST API + endpoints + API key |

---

## Key Design Decisions

- **Fulfillment-based payment routing**: QinConnect fulfillment hook detects payment intent via session attributes (`Tool=Escalate`, `escalationReason=PAYMENT_TRANSFER`) as fallback when AI response text is unavailable
- **PCI compliance**: PaymentCollectionBot disables conversation logs; card slots use obfuscation
- **Session continuity**: SaveAndRestoreSession Lambda preserves AI context across the payment flow interruption
- **Idempotent bot scripts**: Bot creation scripts check for existing resources before creating

---

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Lambda Handler Mapping](docs/lambda-handlers.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Post-Deployment Steps](docs/MANUAL_POST_DEPLOYMENT_STEPS.md)

---

## Security

- No AWS account IDs, ARNs, or credentials are stored in this repository
- All environment-specific values use placeholders — configure via `.env`
- Run `./scripts/utilities/sanitize-check.sh` before committing to verify

---

## License

MIT
