Amazon Connect Contact Flows
main-ivr-flow.json

Primary IVR contact flow. Import into your Amazon Connect instance.
After Importing, Update These Resource ARNs:

    Lex Bot ARNs (ParkAndTollBot, PaymentCollectionBot)
    Lambda function ARNs (all 16 functions)
    Q in Connect Assistant ARN
    Queue ARNs (if using agent escalation)

See ../docs/MANUAL_POST_DEPLOYMENT_STEPS.md Step 11. EOF

cat > "${REPO_ROOT}/iam-reference/README.md" << 'EOF'
IAM Reference Policies

Snapshots of IAM policies from the live environment, provided for reference during deployment and troubleshooting.

These are NOT used directly by CloudFormation. CFN templates define their own IAM roles and policies. These files document the actual working state.
Structure

iam-reference//
    trust-policy.json           # Lambda assume role trust policy
    managed-policies.json       # Attached AWS managed policies
    inline-*.json              # Custom inline policies (DynamoDB, Connect, etc.)

