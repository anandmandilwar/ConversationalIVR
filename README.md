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
├── ai-agent/                   # AI agent system prompt
├── knowledge-base/             # Knowledge base content for RETRIEVE tool
├── config/                     # Environment parameter templates
├── iam-reference/              # IAM policy snapshots from live environment
├── docs/                       # Architecture, deployment, troubleshooting
```

---

## Prerequisites

- AWS CLI v2 with configured credentials
- AWS Account with Amazon Connect, Lex V2, Q in Connect, Bedrock (Nova Sonic), AgentCore
- Python 3.12+
- Node.js 20.x+ (for one Lambda)
- **API Gateway CloudWatch Logs role** (one-time per account/region) — required before deploying the API Gateway stack:
  ```bash
  # Create the IAM role
  aws iam create-role \
    --role-name ApiGatewayCloudWatchLogsRole \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "apigateway.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'

  # Attach the managed policy
  aws iam attach-role-policy \
    --role-name ApiGatewayCloudWatchLogsRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

  # Set it in API Gateway account settings
  ROLE_ARN=$(aws iam get-role --role-name ApiGatewayCloudWatchLogsRole --query 'Role.Arn' --output text)
  aws apigateway update-account \
    --patch-operations op=replace,path=/cloudwatchRoleArn,value=$ROLE_ARN \
    --region us-east-1
  ```

---

## Quick Start

1. **Configure environment:**
   ```bash
   cp env.sh.example env.sh
   # Edit env.sh with your AWS account details
   ```

2. **Deploy CloudFormation stacks:**
   ```bash
   ./scripts/deploy-all.sh
   ```

3. **Create Lex bots:**
   ```bash
   ./create-park-and-toll-bot.sh
   ./create-payment-bot.sh
   ```

4. **Fix contact flow placeholder ARNs::**
   ```bash
   ./fix-contact-flow.sh
   ```

5. **Complete post-deployment steps:**
   See [docs/Manual-post-phase1-and-2-deployment-steps.md](docs/Manual-post-phase1-and-2-deployment-steps.md) for the full post-deployment checklist.

---

## Connect Flow Update Process

### Problem

When Amazon Connect contact flows are imported or created from templates, they may contain placeholder ARNs — references to resources that use a dummy AWS account ID (e.g., `123456789012`) or placeholder resource identifiers (e.g., `PARK_BOT_ID_PLACEHOLDER`). These placeholder ARNs prevent the flow from functioning correctly at runtime, even though the Connect visual editor may display the correct resource names in the dropdown selections.

Symptoms of placeholder ARNs:

- Caller hears "Thank you for calling. Goodbye." immediately
- Lex bot blocks return instantly without engaging the AI agent
- Lambda invocations fail silently (error paths are followed)
- Contact flow appears correct in the visual editor but fails at runtime

### How the Fix Script Works

The `fix-contact-flow.sh` script automates the replacement of all placeholder ARNs with real deployed resource ARNs. It reads environment configuration from `env.sh` and performs the following steps:

```
┌──────────────────────────────────┐
│  1. Source env.sh                │  Reads REGION, ACCOUNT_ID,
│     Validate required variables  │  CONNECT_INSTANCE_ID
├──────────────────────────────────┤
│  2. Discover real resource ARNs  │  Looks up ParkAndTollBot (bot ID + alias)
│                                  │  Fetches all Lambda function ARNs
├──────────────────────────────────┤
│  3. Export the contact flow      │  Downloads current flow JSON from Connect
│     Save original as backup      │  Counts placeholder references
├──────────────────────────────────┤
│  4. Replace placeholder ARNs     │  Lex bot: PARK_BOT_ID_PLACEHOLDER → real
│                                  │  Lambdas: 123456789012 → real account ID
├──────────────────────────────────┤
│  5. Show diff and confirm        │  Displays before/after changes
│                                  │  Prompts for confirmation
├──────────────────────────────────┤
│  6. Update and publish flow      │  Pushes updated JSON to Connect
│                                  │  Sets flow state to ACTIVE
├──────────────────────────────────┤
│  7. Verify                       │  Re-exports flow, confirms zero
│     Export verified flow         │  placeholders remain
└──────────────────────────────────┘
```

### Prerequisites

Ensure `env.sh` exists in the project root with the following variables:

```bash
# env.sh
export REGION="us-east-1"
export ACCOUNT_ID="123456789012"           # Your real AWS account ID
export CONNECT_INSTANCE_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

The following resources must already be deployed:

- Amazon Connect instance with the contact flow imported
- ParkAndTollBot (Lex V2) with a `live` alias
- All Lambda functions deployed via CloudFormation stacks

### Usage

```bash
# Make the script executable (first time only)
chmod +x fix-contact-flow.sh

# Run the script
./fix-contact-flow.sh
```

### What Gets Replaced

The script automatically detects and replaces the following placeholder patterns:

| Resource Type | Placeholder Pattern | Replaced With |
|---|---|---|
| Lex Bot (ParkAndTollBot) | `arn:aws:lex:REGION:123456789012:bot-alias/PARK_BOT_ID_PLACEHOLDER/PARK_BOT_ALIAS_PLACEHOLDER` | Real bot-alias ARN discovered via `lexv2-models` API |
| Lambda Functions | `arn:aws:lambda:REGION:123456789012:function:FUNCTION_NAME` | Real Lambda ARN discovered via `lambda list-functions` API |

Lambda functions resolved automatically:

| Flow Block | Placeholder Function Name | Real Function |
|---|---|---|
| Update Connect session data Lambda | `ConnectAssistantUpdateSessionDataNew` | Auto-discovered |
| Save Session for Payment | `ivr-dev-SaveAndRestoreSession` | Auto-discovered |
| Restore Session Lambda | `ivr-dev-SaveAndRestoreSession` | Auto-discovered |
| Update Violation Balance | `ivr-dev-UpdateViolationBalance` | Auto-discovered |
| Seed Payment Bot Session | `ivr-dev-SeedPaymentSession` | Auto-discovered |

> **Note:** The script discovers placeholder function names directly from the flow JSON and resolves them against your deployed Lambda functions. No manual ARN mapping is required.

### Output Files

All files are saved to the `flow-updates/` directory:

| File | Description |
|---|---|
| `flow-original-TIMESTAMP.json` | Backup of the flow before any changes |
| `flow-updated-TIMESTAMP.json` | The flow with placeholders replaced (pre-publish) |
| `flow-verified-TIMESTAMP.json` | Re-exported flow after publishing (post-verification) |

### Example Output

```
╔══════════════════════════════════════════════════════╗
║   Contact Flow ARN Fix                               ║
║   Replace placeholder ARNs with real deployed ARNs   ║
╚══════════════════════════════════════════════════════╝

  Environment (from env.sh):
    Region:              us-east-1
    Account ID:          123456789012
    Connect Instance ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    Flow Name:           Main Flow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 1: Discovering Real Resource ARNs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ ParkAndTollBot ARN: arn:aws:lex:us-east-1:123456789012:bot-alias/XXXXXXXX/YYYYYYYY
  ✅ Found 18 Lambda functions in account

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 3: Replacing Placeholder ARNs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Replaced 2 Lex bot placeholder(s)
  ✅ Replaced Lambda (2x): ivr-dev-SaveAndRestoreSession
  ✅ Replaced Lambda (1x): ivr-dev-UpdateViolationBalance
  ✅ Replaced Lambda (1x): ConnectAssistantUpdateSessionDataNew
  ✅ Replaced Lambda (1x): ivr-dev-SeedPaymentSession
  ✅ All placeholders replaced successfully! ✨

  Apply changes and publish? (y/N): y

  ✅ Contact flow content updated!
  ✅ Contact flow is ACTIVE and PUBLISHED!

  ┌───────────────────────────────────────────────────────┐
  │ Verification Results                                   │
  ├───────────────────────────────────────────────────────┤
  │  Placeholder account refs:  0    (should be 0)        │
  │  PLACEHOLDER strings:       0    (should be 0)        │
  │  Real account refs:         12   (should be > 0)      │
  └───────────────────────────────────────────────────────┘

  ╔══════════════════════════════════════════════════════╗
  ║  ✅ CONTACT FLOW UPDATED SUCCESSFULLY!              ║
  ║  🎉 Test it now — call your phone number!           ║
  ╚══════════════════════════════════════════════════════╝
```

### Customization

The script supports optional environment variables for non-default configurations:

```bash
# Override defaults (set in env.sh or export before running)
export FLOW_NAME="Main Flow"                    # Default: "Main Flow"
export PLACEHOLDER_ACCOUNT="123456789012"       # Default: "123456789012"
export PARK_BOT_NAME="ParkAndTollBot"           # Default: "ParkAndTollBot"
export PARK_BOT_ALIAS_NAME="live"               # Default: "live"
```

### Idempotency

The script is safe to run multiple times:

- If no placeholders are found, it exits early with a success message
- Original flow is always backed up before changes
- Changes require explicit confirmation before being applied
- Post-publish verification ensures the update was applied correctly

### Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `env.sh` not found | Script can't find environment file | Create `env.sh` in the same directory as the script |
| Missing required variables | `env.sh` is incomplete | Add all 3 required exports: `REGION`, `ACCOUNT_ID`, `CONNECT_INSTANCE_ID` |
| ParkAndTollBot not found | Bot not yet created | Run `./create-park-and-toll-bot.sh` first |
| Alias 'live' not found | Bot alias not created | Create the `live` alias on ParkAndTollBot |
| Contact flow not found | Flow name doesn't match | Check `FLOW_NAME` variable; script lists available flows |
| Lambda NOT found in account | Lambda not deployed | Deploy the missing CloudFormation stack |
| Placeholders remain after fix | Unrecognized placeholder pattern | Check the verified JSON and update manually in the Connect console |

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
- [Known Issues](docs/KNOWN_ISSUES.md)
- [Post-Deployment Steps](docs/Manual-post-phase1-and-2-deployment-steps.md)

---

## Security

- No AWS account IDs, ARNs, or credentials are stored in this repository
- All environment-specific values use placeholders — configure via `env.sh`
- Run `./scripts/utilities/sanitize-check.sh` before committing to verify

---

## License

MIT
