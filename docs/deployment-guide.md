# Deployment Guide

## Prerequisites

- AWS CLI v2 configured with appropriate credentials
- Python 3.12+, Node.js 20.x+
- Amazon Connect instance created
- Bedrock model access enabled (Nova Sonic)
- An S3 bucket for CloudFormation templates (referenced in `env.sh`)
- **API Gateway CloudWatch Logs role** — one-time setup per account/region (see [README prerequisites](../README.md#prerequisites))

---

## Step 1: Configure Environment

Both `deploy-all.sh` and `env.sh` must be in the **root** of the project folder.

```bash
cp env.sh.example env.sh
# Edit env.sh with your AWS account details
```

> **Important:** After any change to `env.sh`, always re-source it before running scripts:
> ```bash
> source env.sh
> ```
> Forgetting to re-source is a common cause of deployment failures (e.g., stale instance alias causing `AlreadyExists` errors).

### Connect Instance Alias

If you get an `AlreadyExists` error for the Connect instance alias during deployment, change `INSTANCE_ALIAS` in `env.sh` to a unique value and re-source the file.

---

## Step 2: Deploy CloudFormation Stacks (Phased)

Run the master deployment script:

```bash
./deploy-all.sh
```

The script deploys in multiple phases. Review the confirmation prompt before each phase.

### Phase 0 — Backend Infrastructure

Deploys DynamoDB tables, Lambda functions (stubs), and API Gateway:

| Stack | Template |
|-------|----------|
| anycompany-ivr-client-config | 01a-client-config-table.yaml |
| anycompany-ivr-dynamodb | 01b-dynamodb-tables.yaml |
| anycompany-ivr-session-table | 01c-session-table.yaml |
| anycompany-ivr-lambdas | 02a-tool-lambdas.yaml |
| anycompany-ivr-payments-lambdas | 02d-payments-lambdas.yaml |
| anycompany-ivr-fulfillment-hook | 02f-fulfillment-hook.yaml |
| anycompany-ivr-getCallAttributes | 02b-getCallAttributes.yaml |
| anycompany-ivr-api | 03-api-gateway.yaml |

After Phase 0, the script automatically updates `openapi.yaml` with the real API Gateway URL.

### Phase 1 — Connect + AgentCore + Q in Connect

Uploads nested templates to S3 and deploys the root nested stack:

| Stack | Template |
|-------|----------|
| anycompany-ivr (root) | root.yaml (nests connect-instance, connect-config, agentcore-gateway, agentcore-target, bootstrap, mcp-application) |

### Phase 1b — Connect-Dependent Stacks

Deploys stacks that require the Connect instance from Phase 1:

| Stack | Template |
|-------|----------|
| anycompany-ivr-payment-handoff | 02e-payment-handoff-resources.yaml |
| anycompany-ivr-update-session | 02c-ConnectAssistantUpdateSessionData.yaml |
| anycompany-ivr-agent-screen-pop | agent-screen-pop-view.yaml |

### ⏸️ Manual Steps Required Before Phase 2

The script pauses here. Complete the following before pressing ENTER to continue:

1. **Associate Q in Connect domain with Connect instance**
   - Navigate to Amazon Connect console → your instance → Amazon Q
   - Select "Use an existing domain" and choose the domain created by Phase 1
   - Add an S3 integration for the knowledge base bucket (configured in `env.sh`)
   - Upload knowledge base files (`faq.txt`, `policies.txt`, `services.txt`) to the S3 bucket
   -    Files are available under knowledge-base directory

2. **Verify OpenAPI schema is at the root of the S3 bucket**
   - The AgentCore Gateway Target requires the OpenAPI schema file at the bucket root

3. **Update AgentCore Target Inbound Audience**
   - Copy the Gateway ID from the Gateway details section
   - Click Edit on the Inbound Identity
   - Paste the Gateway ID in the Audiences text box
   - Ensure "Allowed clients" is unchecked, then save

4. **Reconfigure the MCP Integration**
   - Delete the existing MCP application created by automation (it may not work correctly)
   - In Amazon Connect console → Third-party applications → Add application
   - Display name: `anycompany-IVR-mcp`, Type: MCP server
   - Select the gateway (auto-populated) and associate with your instance

5. **Create Connect Admin user**
   ```bash
   cd scripts/utilities/
   python3 create_connect_admin.py \
     --region us-east-1 \
     --instance-id "<CONNECT_INSTANCE_ID>" \
     --username "admin" \
     --password '<PASSWORD>' \
     --email "<EMAIL>" \
     --first-name "Admin" \
     --last-name "User"
   ```

6. **Create Security Profile in Connect Admin console**
   - Log into the Connect admin interface via the Access URL
   - Users → Security profiles → Add new security profile
   - Name: `ParkandToll-AI-Agent`
   - Enable: Contact Control Panel access, Connect assistant - View
   - Grant "Access" to all 10 MCP tools (lookupByPlate, lookupByCitation, lookupByAccount, getBalance, getViolationDetails, submitDispute, checkDisputeStatus, buildPaymentCart, initiatePayment, applyPaymentResult)

### Phase 2 — AI Agent Configuration

After completing the manual steps above, press ENTER. The script deploys:

| Stack | Template |
|-------|----------|
| anycompany-ivr-phase2-qagents | qagents-v49.yaml |

This configures 13 tool definitions (9 MCP + 2 RTC + 2 payment) for the AI agent.

---

## Step 3: Post-Phase 2 Manual Steps

### 3a. Update the AI Agent Prompt

- Refresh the Connect Admin console to see the agent created by Phase 2
- Find the AI Agent: `<Instance_Alias>-orchestration-agent`
- Edit in Agent Builder → replace the AI Prompt with contents of `ai-agent/Final-System-Prompt-03242026_1230.txt`
- Save and Publish the prompt
- Open the Agent → Add Prompt → select the v2 prompt you just saved

### 3b. Set the Default Agent

- Navigate to AI Agents page → Default AI Agent Configurations
- In the "Self-service" row, select your `<Instance_Alias>-orchestration-agent`
- Save

### 3c. Enable Bot Management in Connect

- Amazon Connect console → your instance → Flows
- Toggle "Enable Lex Bot Management in Amazon Connect" OFF → Save → ON → Save
- Ensure both are enabled:
  - ✅ Enable Lex Bot Management in Amazon Connect
  - ✅ Enable Bot Analytics and Transcripts in Amazon Connect

### 3d. Associate Lambdas with Connect Instance

Ensure `CONNECT_INSTANCE_ID` is set in `env.sh`, then:

```bash
cd scripts
./associate_lamnbda_to_connect.sh
```

This associates 5 Lambda functions with the Connect instance (ConnectAssistantUpdateSessionDataNew, getCallAttributes, SeedPaymentSession, SaveAndRestoreSession, UpdateViolationBalance).

---

## Step 4: Create Lex Bots

Both scripts must be in the project root folder (alongside `env.sh`).

### 4a. ParkAndTollBot (Conversational AI)

```bash
./create-park-and-toll-bot.sh
```

Creates the bot with AmazonQInConnect intent, fulfillment code hook, `live` alias, Lambda permissions, and Connect association.

### 4b. PaymentCollectionBot (PCI Payment)

```bash
./create-payment-bot.sh
```

Creates the bot with CollectPayment/CancelPayment intents, card slots (obfuscated for PCI), `live` alias, and Connect association.

> **Note:** If the payment bot script fails on slot creation, delete the bot and re-run:
> ```bash
> BOT_ID=$(aws lexv2-models list-bots --region us-east-1 \
>   --filters name=BotName,values=PaymentCollectionBot,operator=EQ \
>   --query "botSummaries[0].botId" --output text)
> [ "$BOT_ID" != "None" ] && aws lexv2-models delete-bot --bot-id "$BOT_ID" --region us-east-1
> ./create-payment-bot.sh
> ```

### 4c. Update SeedPaymentSession Lambda Environment Variables

After creating the PaymentCollectionBot, update the `ivr-dev-SeedPaymentSession` Lambda with the bot IDs from the script output:

- `PAYMENT_BOT_ID` = (Bot ID from script output)
- `PAYMENT_BOT_ALIAS_ID` = (Alias ID from script output)

---

## Step 5: Import Connect Contact Flows

### 5a. Fix Placeholder ARNs in Flow JSON

Before importing, replace placeholder ARNs in the local flow JSON:

```bash
./fix-connect-flow.sh connect-flows/main-ivr-flow.json
```

Also replace the `WisdomAssistantArn` placeholder with the actual ARN, and update the PCI Bot ID and Alias ID in the main flow JSON.

### 5b. Import Flows (in order)

1. **Basic Settings Module** — In Connect Admin: Routing → Flows → Modules tab → Create flow module → Import `Basic-setting-configurations.json`
2. **Main IVR Flow** — Routing → Flows → Create flow → Import `main-ivr-flow.json`

### 5c. Fix Live Contact Flow ARNs

After importing, run the fix script against the live flow in Connect:

```bash
./fix-connect-flow.sh
```

---

## Step 6: Deploy Lambda Code

Replace CloudFormation stub code with actual Lambda source:

```bash
./update-lambda-code.sh
```

This packages and uploads code for all 16 Lambda functions, validates handlers, and preserves existing environment variables.

---

## Step 7: Update Lambda Environment Variables

- Update `CONNECT_INSTANCE_ID` environment variable on `anycompany-ivr-initiate-payment-dev`

---

## Step 8: Seed DynamoDB Test Data

```bash
python3 scripts/utilities/seed_client_config.py
python3 scripts/utilities/seed_test_data.py
```

This populates:
- `anycompany-ivr-client-config-dev` — client configurations (4 clients)
- `anycompany-ivr-customers-dev` — customer records (25 customers)
- `anycompany-ivr-violations-dev` — violation records

---

## Step 9: Claim Phone Number & Update Client Config

1. Claim a phone number in Amazon Connect and assign it to the Main Flow
2. Update the client config table with the claimed phone number:
   ```bash
   ./scripts/utilities/update-client-phone.sh +1XXXXXXXXXX
   ```

---

## Step 10: End-to-End Test

Call the phone number associated with your Connect instance and test:

- License plate lookup
- Citation lookup
- Balance inquiry
- Payment flow
- Dispute submission

---

## Troubleshooting Notes

### AgentCore Gateway Permission Errors

If you see `GetResourceApiKey` or `secretsmanager:GetSecretValue` 403 errors in AgentCore Gateway logs, the gateway role needs additional permissions. Run:

```bash
./fix-agentcore-gateway-permission.sh
```

If a second error appears for Secrets Manager access, run:

```bash
./fix-agentcore-secrets-permission.sh
```

### AI Agent Not Responding

If the AI agent created by Phase 2 automation doesn't work correctly, create a new AI Agent manually in the Connect console:
- Attach the same prompt and all tools
- Set it as the "Self Service" default under Default AI Agent Configurations

### Connect Flow Issues

See the [Connect Flow Update Process](../README.md#connect-flow-update-process) section in the README and [Troubleshooting](troubleshooting.md) for common flow issues.

---

## Deployment Summary (12 Stacks)

| Phase | Stacks |
|-------|--------|
| Phase 0 | anycompany-ivr-client-config, anycompany-ivr-dynamodb, anycompany-ivr-session-table, anycompany-ivr-lambdas, anycompany-ivr-payments-lambdas, anycompany-ivr-fulfillment-hook, anycompany-ivr-getCallAttributes, anycompany-ivr-api |
| Phase 1 | anycompany-ivr (root + nested stacks) |
| Phase 1b | anycompany-ivr-payment-handoff, anycompany-ivr-update-session, anycompany-ivr-agent-screen-pop |
| Phase 2 | anycompany-ivr-phase2-qagents |
