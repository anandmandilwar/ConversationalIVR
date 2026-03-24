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

## Step 3: Update Escalate Tool Input Schema on AI Agent

**Template:** AI Agent  
**Resource:** OrchestrationAIAgent → Escalate tool

Current schema has only `reason` field. Must be updated to include:

| Field | Type | Description |
|-------|------|-------------|
| `escalationReason` | string | Category code: `PAYMENT_TRANSFER`, `CUSTOMER_REQUEST`, etc. |
| `customerIntent` | string | What the customer wants to accomplish |
| `escalationSummary` | string | Detailed context for receiving agent |
| `sentiment` | string | Customer emotional state |

These fields are read by:
- QinConnectDialogHook Lambda (detects `PAYMENT_TRANSFER`)
- Connect flow (routes based on `Tool` attribute)
- Agent screen pop (displays escalation context)

---

## Step 4: Add All Tool Configurations to AI Agent

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

## Step 5: Update PaymentBotId and PaymentBotAliasId

**Template:** Payment Handoff  
**Resource:** SeedPaymentSession Lambda

PaymentCollectionBot is created AFTER this stack deploys. The env vars default to `PENDING`.

```bash
aws lambda update-function-configuration \
    --function-name ivr-dev-SeedPaymentSession \
    --environment '{
        "Variables": {
            "KMS_KEY_ARN": "",
            "ENVIRONMENT": "dev",
            "SESSION_TABLE_NAME": "",
            "PAYMENT_BOT_ID": "",
            "PAYMENT_BOT_ALIAS_ID": ""
        }
    }' \
    --region us-east-1
```

Also update the IAM policy with actual bot ARN:

```bash
aws iam put-role-policy \
    --role-name ivr-dev-SeedPaymentSessionRole \
    --policy-name LexPaymentBotAccess \
    --policy-document '{...with actual bot ARN...}'
```

---

## Step 6: Deploy Actual Lambda Code

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

## Step 7: Associate Bots with Connect Instance

ParkAndTollBot and PaymentCollectionBot must be associated with the Connect instance.

```bash
aws connect associate-bot \
    --instance-id  \
    --lex-v2-bot AliasArn=arn:aws:lex:us-east-1::bot-alias// \
    --region us-east-1
```

---

## Step 8: Associate Lambdas with Connect Instance

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

## Step 9: Configure ParkAndTollBot

After bot creation:

1. Enable FulfillmentCodeHook on `AmazonQInConnect` intent
2. Configure bot alias locale settings with QinConnectDialogHook Lambda ARN
3. Add Lambda resource policy for `lexv2.amazonaws.com`
4. Build locale, create version, update alias to new version
5. Use Service-Linked Role: `AWSServiceRoleForLexV2Bots_AmazonConnect_`
6. Tag: `AmazonConnectEnabled=True`

---

## Step 10: Configure PaymentCollectionBot

After bot creation:

1. Configure bot alias locale settings with PaymentProcessing Lambda ARN
2. Add Lambda resource policy for `lexv2.amazonaws.com`
3. Build locale, create version, update alias

---

## Step 11: Import/Create Contact Flow

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

## Step 12: Associate Q in Connect with Connect Instance

The Q in Connect assistant must be integrated with the Connect instance.

**Action:** Connect Console → Amazon Q → Enable

---

## Step 13: Upload Knowledge Base Content

Upload client-specific KB documents to:

```
s3:////
```

Then sync the knowledge base via Console or CLI.

---

## Step 14: Seed DynamoDB Test Data

Populate test data in:

- `anycompany-ivr-client-config-dev` (client configurations)
- `anycompany-ivr-customers-dev` (customer records)
- `anycompany-ivr-violations-dev` (violation records)

```bash
python3 scripts/utilities/seed_client_config.py
python3 scripts/utilities/seed_test_data.py
```

---

## Step 15: Claim Phone Number

Claim a phone number in Connect and associate it with the Main Flow.

**Action:** Connect Console → Phone numbers → Claim

---

## Step 16: End-to-End Test

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
