# Manual Post-Deployment Steps

**Document Version:** 1.0  
**Date:** 2026-03-23

These steps **cannot be fully automated** in CloudFormation due to dependency ordering, runtime-generated values, or manual configuration requirements. Execute after CFN stack deployment.

---

## Step 1: Update AI Prompt Model ID

**Template:** Connect Config (Q in Connect)  
**Resource:** OrchestrationPrompt

CFN deploys with `us.amazon.nova-lite-v1:0`. Must be updated to the correct model.

```bash
aws wisdom update-ai-prompt \
    --assistant-id <assistant_id> \
    --ai-prompt-id  \
    --model-id "us.anthropic.claude-haiku-4-5-20251001-v1:0" \
    --region us-east-1
```

---

## Step 2: Update AI Prompt Content (Add Payment Tools)

**Template:** Connect Config (Q in Connect)  
**Resource:** OrchestrationPrompt

The orchestration prompt needs to include instructions for:
- `buildPaymentCart` tool usage
- `initiatePayment` tool usage
- Payment flow sequence: buildCart → initiatePayment → Escalate PAYMENT_TRANSFER

**Action:** Update prompt text via Console or CLI:
- Add `buildPaymentCart` and `initiatePayment` to the tools section
- Add payment flow examples
- Add payment-specific instructions

---

## Step 3: Update Escalate Tool Input Schema and Instructions on AI Agent

**Template:** AI Agent  
**Resource:** OrchestrationAIAgent → Escalate tool

The CFN-deployed Escalate tool has a minimal schema with only a `reason` field. It must be updated manually via the Amazon Q in Connect console with the full schema, instructions, and examples.

### Input Schema

Delete the existing schema and replace with:

```json
{
  "type": "object",
  "properties": {
    "customerIntent": {
      "type": "string",
      "description": "A brief phrase (10-15words) describing what the customer wants to accomplish"
    },
    "sentiment": {
      "type": "string",
      "description": "Customer's emotional state during the conversation",
      "enum": [
        "positive",
        "neutral",
        "frustrated"
      ]
    },
    "escalationSummary": {
      "type": "string",
      "description": "Detailed summary for the human agent including what the customer asked for, what was attempted, and why escalation is needed",
      "maxLength": 500
    },
    "escalationReason": {
      "type": "string",
      "description": "Category for the escalation reason",
      "enum": [
        "complex_booking",
        "technical_issue",
        "customer_frustration",
        "policy_exception",
        "out_of_scope",
        "other"
      ]
    }
  },
  "required": [
    "escalationReason",
    "escalationSummary",
    "customerIntent",
    "sentiment"
  ]
}
```

### Instructions

Replace the existing instruction with:

```
Escalate to a human agent when:

**Volume & Complexity Triggers:**
1. Request involves more than 3 vehicles or license plates
2. Request involves more than 5 violations to address
3. Request involves multiple accounts (personal + business, duplicate accounts needing merger)
4. Fleet or commercial account management is needed

**Specialized Expertise Required:**
5. Estate settlement or deceased account holder situations
6. Commercial account setup with custom requirements (emergency exemptions, multi-user access, custom invoicing)
7. Rental car billing disputes involving multiple rental companies
8. Vehicle ownership transfers for multiple vehicles
9. Account migration or system transition issues
10. Requests requiring legal documentation (court cases, probate, tax audits)

**Multi-Domain Coordination:**
11. Combined parking and toll issues in one request
12. Disputes requiring evidence review (dashcam footage, photos, documents)
13. Payment investigations requiring bank coordination
14. Requests needing coordination across multiple departments

**System & Satisfaction Issues:**
15. Multiple tools fail or return errors repeatedly
16. Knowledge base lacks required policy information
17. Customer expresses frustration, dissatisfaction, or explicitly requests a human
18. You cannot provide adequate assistance with available tools

When escalating, acknowledge the complexity or importance of their request, briefly summarize what you understood (to show you listened), and reassure them that the specialist will have all the context to help efficiently.
```

### Examples

Add the following examples to the Escalate tool:

**Good example — Complex coordination request:**
```
<message>
I understand you had a difficult day - a parking ticket from an app issue and a toll violation from police-directed traffic, and you have dashcam footage of both. Since this involves both our parking and toll systems with video evidence to review, plus the documentation you need for work reimbursement, let me connect you with a specialist who can coordinate everything and get you the proper receipts.
</message>
```

**Good example — Technical difficulties:**
```
<message>
I apologize, but I'm experiencing technical difficulties right now. To make sure you get accurate information, let me connect you with a representative who can help you directly right away.
</message>
```

**Good example — Frustrated customer:**
```
<message>
I'm really sorry for all the trouble you've been through. That's not the experience you should have. Let me get you to someone who can resolve this and make sure this gets handled properly.
</message>
```

**Good example — Complex fleet coordination:**
```
<message>
Setting up a fleet account with multiple ownership types, separate billing categories, and custom access levels is exactly what our commercial accounts team handles. They can coordinate the transponder shipments to your three locations and configure everything to meet your two-week deadline. Let me connect you with a business account specialist right away.
</message>
```

**Bad example (avoid — too abrupt, no empathy):**
```
<message>
I can't help with that. Let me transfer you to someone else.
</message>
```

---

## Step 4: Add Retrieve Tool to AI Agent

The RETRIEVE tool is NOT deployed via CloudFormation. It must be added manually via the Amazon Q in Connect console.

### Step 4a: Navigate to Your AI Agent

1. In the Amazon Connect admin console, click **AI agent designer** in the left navigation
2. Click **AI agents**
3. Click on your AI Agent deployed as part of the deployment
4. Click **Edit** in Agent Builder

### Step 4b: Add the Retrieve Tool

1. In the **Tools** section, click the **Add tool** button
2. For **Namespace**, select **Amazon Connect**
3. For **Tool**, select **Retrieve**
4. For **Assistant Association**, select your assistant association from the dropdown
5. Configure the tool settings:

**Tool name:** `Retrieve`

**Instructions:**

```
Search the knowledge base using semantic search to find client-specific information about parking violations, tolling, payments, disputes, policies, and procedures.

Rules:
1. ALWAYS filter by clientId - never return information from other clients
2. Use multiple searches if the first query doesn't fully answer the question
3. Only provide information that is explicitly found in the knowledge base
4. If information is not found, say "I don't have that specific information" and offer agent transfer
5. Never make assumptions about client policies or procedures

Use this tool to answer questions about: payment methods, fees, dispute eligibility, business hours, late penalties, payment plans, and account policies.
```

### Step 4c: Add Examples

**Good example — Detailed policy response:**
```
<message>
Metro Parking Authority accepts several payment methods. You can pay with credit cards including Visa, MasterCard, American Express, and Discover. We also accept debit cards and electronic checks. Please note there is a small convenience fee - 2.5% for card payments with a minimum of $1.50, or a flat $1.00 fee for electronic checks. Would you like to make a payment now?.
</message>
```

**Good example query:** `"What happens if I don't pay my ticket on time?"`

**Bad example query:** `"don't pay ticket"`

### Step 4d: Save and Publish

1. Click **Add** to add the tool
2. Click **Publish** to update your agent with the new tool

---

## Step 5: Verify All Tool Configurations on AI Agent

**Template:** AI Agent  
**Resource:** OrchestrationAIAgent → ToolConfigurations

Verify all tools are registered with correct ToolName, ToolId, and Instructions:

- [ ] lookupByPlate
- [ ] lookupByCitation
- [ ] lookupByAccount
- [ ] getBalance
- [ ] getViolationDetails
- [ ] submitDispute
- [ ] checkDisputeStatus
- [ ] buildPaymentCart
- [ ] initiatePayment
- [ ] Escalate (RETURN_TO_CONTROL)
- [ ] Complete (RETURN_TO_CONTROL)
- [ ] RETRIEVE (Knowledge Base — may be auto-configured)

**ToolId format:** `gateway_{gatewayId}__{targetName}___{toolName}`

---

## Step 6: Redeploy Payment Handoff Stack with Real Bot IDs

**Template:** Payment Handoff (`02e-payment-handoff-resources.yaml`)  
**Why:** PaymentCollectionBot is created AFTER this stack deploys. The `PaymentBotId` and `PaymentBotAliasId` parameters default to `PENDING`, which means:
- The `SeedPaymentSession` Lambda env vars point to `PENDING`
- The IAM policy grants `lex:PutSession` on `bot-alias/PENDING/PENDING` (useless)

**CRITICAL:** This step must be done after `create-payment-bot.sh` completes. Bot IDs are in `payment-bot-config.json`.

```bash
# Get bot IDs from the config file generated by create-payment-bot.sh
BOT_ID=$(python3 -c "import json; print(json.load(open('payment-bot-config.json'))['botId'])")
ALIAS_ID=$(python3 -c "import json; print(json.load(open('payment-bot-config.json'))['botAliasId'])")

# Redeploy the stack with real bot IDs
aws cloudformation deploy --region us-east-1 \
  --stack-name anycompany-ivr-payment-handoff \
  --template-file cfn/standalone/02e-payment-handoff-resources.yaml \
  --capabilities CAPABILITY_NAMED_IAM --no-fail-on-empty-changeset \
  --parameter-overrides \
    Environment=dev \
    DynamoDBStackName=anycompany-ivr-dynamodb \
    SessionTableStackName=anycompany-ivr-session-table \
    ConnectInstanceArn=arn:aws:connect:us-east-1:${ACCOUNT_ID}:instance/${CONNECT_INSTANCE_ID} \
    PaymentBotId=$BOT_ID \
    PaymentBotAliasId=$ALIAS_ID
```

This updates both the Lambda env vars AND the IAM policy in one step.

---

## Step 7: Deploy Actual Lambda Code

All 16 Lambda functions are created with stub/placeholder code. Actual code must be deployed.

**Handler-to-filename mapping (CRITICAL — must match):**

| Lambda | Handler | Source File |
|--------|---------|-------------|
| anycompany-ivr-dev-getCallAttributes | `index.lambda_handler` | `index.py` |
| ConnectAssistantUpdateSessionDataNew | `index.handler` | `index.js` |
| ivr-dev-SaveAndRestoreSession | `index.lambda_handler` | `index.py` |
| ivr-dev-SeedPaymentSession | `seed_session.lambda_handler` | `seed_session.py` |
| ivr-dev-UpdateViolationBalance | `index.lambda_handler` | `index.py` |
| anycompany-ivr-dev-QinConnectDialogHook | `lambda_function.lambda_handler` | `lambda_function.py` |
| ivr-dev-PaymentProcessing | `index.lambda_handler` | `index.py` |
| anycompany-ivr-build-payment-cart | `build_payment_cart.lambda_handler` | `build_payment_cart.py` |
| anycompany-ivr-initiate-payment | `initiate_payment.lambda_handler` | `initiate_payment.py` |
| All 7 tool lambdas | `index.lambda_handler` | `index.py` |

**Deploy each:**

```bash
cd 
zip -r code.zip 
aws lambda update-function-code \
    --function-name  \
    --zip-file fileb://code.zip \
    --region us-east-1
```

---

## Step 8: Associate Bots with Connect Instance

ParkAndTollBot and PaymentCollectionBot must be associated with the Connect instance.

```bash
aws connect associate-bot \
    --instance-id  \
    --lex-v2-bot AliasArn=arn:aws:lex:us-east-1::bot-alias// \
    --region us-east-1
```

---

## Step 9: Associate Lambdas with Connect Instance

These Lambdas must be associated with Connect:

- `anycompany-ivr-dev-getCallAttributes`
- `ivr-dev-SaveAndRestoreSession`
- `ivr-dev-SeedPaymentSession`
- `ivr-dev-UpdateViolationBalance`
- `ConnectAssistantUpdateSessionDataNew` (may be done by CFN via IntegrationAssociation)

```bash
aws connect associate-lambda-function \
    --instance-id  \
    --function-arn  \
    --region us-east-1
```

---

## Step 10: Configure ParkAndTollBot

After bot creation:

1. Enable FulfillmentCodeHook on `AmazonQInConnect` intent
2. Configure bot alias locale settings with QinConnectDialogHook Lambda ARN
3. Add Lambda resource policy for `lexv2.amazonaws.com`
4. Build locale, create version, update alias to new version
5. Use Service-Linked Role: `AWSServiceRoleForLexV2Bots_AmazonConnect_`
6. Tag: `AmazonConnectEnabled=True`

---

## Step 11: Configure PaymentCollectionBot

After bot creation:

1. Configure bot alias locale settings with PaymentProcessing Lambda ARN
2. Add Lambda resource policy for `lexv2.amazonaws.com`
3. Build locale, create version, update alias

---

## Step 12: Import/Create Contact Flow

The Main Flow must be created/imported with correct:

- Lambda ARNs (all 5 pointing to new account)
- ParkAndTollBot alias ARN (new account)
- PaymentCollectionBot alias ARN (new account)
- Flow module references (Basic setting configurations)
- Queue references (BasicQueue)
- Agent Screen Pop flow reference
- TTS voice settings
- Speech timeout attributes

---

## Step 13: Associate Q in Connect with Connect Instance

The Q in Connect assistant must be integrated with the Connect instance.

**Action:** Connect Console → Amazon Q → Enable

---

## Step 14: Upload Knowledge Base Content

Upload client-specific KB documents to:

```
s3:////
```

Then sync the knowledge base via Console or CLI.

---

## Step 15: Seed DynamoDB Test Data

Populate test data in:

- `anycompany-ivr-client-config-dev` (client configurations)
- `anycompany-ivr-customers-dev` (customer records)
- `anycompany-ivr-violations-dev` (violation records)

```bash
python3 scripts/utilities/seed_client_config.py
python3 scripts/utilities/seed_test_data.py
```

---

## Step 16: Claim Phone Number

Claim a phone number in Connect and associate it with the Main Flow.

**Action:** Connect Console → Phone numbers → Claim

---

## Step 17: Update Client Config with Claimed Phone Number

After claiming a phone number in Step 15, update the client config table so the IVR system maps incoming calls to the correct client.

```bash
./scripts/utilities/update-client-phone.sh +1XXXXXXXXXX
```

Replace `+1XXXXXXXXXX` with the phone number claimed in Connect (E.164 format).

---

## Step 18: End-to-End Test

Test the complete flow:

- [ ] Call → AI greets correctly
- [ ] Provide plate → AI looks up account
- [ ] Ask about violations → AI retrieves details
- [ ] Request payment → AI builds cart → initiatePayment
- [ ] Fulfillment Lambda detects `PAYMENT_TRANSFER`
- [ ] Route to PaymentCollectionBot
- [ ] Collect card details → process payment
- [ ] Resume AI conversation
- [ ] Ask policy question → RETRIEVE from KB
- [ ] Request agent → Escalate to queue
