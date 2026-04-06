#!/usr/bin/env python3
"""
Create an Amazon Connect admin user for CONNECT_MANAGED instances.

It will:
- Find the Connect instance by InstanceId or by InstanceAlias (if provided)
- Find the built-in "Admin" security profile (or fall back to the first profile)
- Find a routing profile (tries "BasicRoutingProfile" first, else first profile)
- Create a user with a password (required for CONNECT_MANAGED)

Docs:
- CreateUser requires Password for CONNECT_MANAGED: https://docs.aws.amazon.com/connect/latest/APIReference/API_CreateUser.html
- Default security profiles include "Admin": https://docs.aws.amazon.com/connect/latest/adminguide/default-security-profiles.html
"""

import argparse
import sys
import boto3
from botocore.exceptions import ClientError


def find_instance_id(connect, instance_id=None, instance_alias=None):
    if instance_id:
        return instance_id

    if not instance_alias:
        raise SystemExit("Provide --instance-id or --instance-alias")

    paginator = connect.get_paginator("list_instances")
    for page in paginator.paginate():
        for inst in page.get("InstanceSummaryList", []):
            if inst.get("InstanceAlias") == instance_alias:
                return inst["Id"]

    raise SystemExit(f"Connect instance with alias '{instance_alias}' not found")


def pick_security_profile_id(connect, instance_id, desired_name="Admin"):
    paginator = connect.get_paginator("list_security_profiles")
    first_id = None
    for page in paginator.paginate(InstanceId=instance_id):
        for sp in page.get("SecurityProfileSummaryList", []):
            if not first_id:
                first_id = sp["Id"]
            if sp.get("Name") == desired_name:
                return sp["Id"]

    if not first_id:
        raise SystemExit("No security profiles found on this instance")
    print(f"WARNING: Security profile '{desired_name}' not found. Falling back to first profile: {first_id}", file=sys.stderr)
    return first_id


def pick_routing_profile_id(connect, instance_id, desired_name="BasicRoutingProfile"):
    paginator = connect.get_paginator("list_routing_profiles")
    first_id = None
    for page in paginator.paginate(InstanceId=instance_id):
        for rp in page.get("RoutingProfileSummaryList", []):
            if not first_id:
                first_id = rp["Id"]
            if rp.get("Name") == desired_name:
                return rp["Id"]

    if not first_id:
        raise SystemExit("No routing profiles found on this instance")
    print(f"WARNING: Routing profile '{desired_name}' not found. Falling back to first profile: {first_id}", file=sys.stderr)
    return first_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--instance-id", help="Connect instance ID (not ARN)")
    ap.add_argument("--instance-alias", help="Connect instance alias (if you don't know ID)")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True, help="Must match policy: 8-64 chars, upper+lower+digit")
    ap.add_argument("--email", required=True)
    ap.add_argument("--first-name", required=True)
    ap.add_argument("--last-name", required=True)
    ap.add_argument("--phone-type", default="SOFT_PHONE", choices=["SOFT_PHONE", "DESK_PHONE"])
    ap.add_argument("--auto-accept", action="store_true", help="Auto-accept calls (optional)")
    ap.add_argument("--after-contact-work-seconds", type=int, default=0)
    args = ap.parse_args()

    connect = boto3.client("connect", region_name=args.region)

    instance_id = find_instance_id(connect, args.instance_id, args.instance_alias)
    security_profile_id = pick_security_profile_id(connect, instance_id, "Admin")
    routing_profile_id = pick_routing_profile_id(connect, instance_id, "BasicRoutingProfile")

    phone_config = {
        "PhoneType": args.phone_type,
        "AfterContactWorkTimeLimit": args.after_contact_work_seconds,
    }
    if args.auto_accept:
        phone_config["AutoAccept"] = True

    try:
        resp = connect.create_user(
            InstanceId=instance_id,
            Username=args.username,
            Password=args.password,  # required for CONNECT_MANAGED :contentReference[oaicite:1]{index=1}
            IdentityInfo={
                "FirstName": args.first_name,
                "LastName": args.last_name,
                "Email": args.email,
            },
            PhoneConfig=phone_config,
            SecurityProfileIds=[security_profile_id],
            RoutingProfileId=routing_profile_id,
        )
    except ClientError as e:
        raise SystemExit(f"CreateUser failed: {e}")

    user_id = resp["UserId"]
    # Fetch ARN for convenience
    user = connect.describe_user(InstanceId=instance_id, UserId=user_id)["User"]
    print("Created user:")
    print(f"  InstanceId: {instance_id}")
    print(f"  UserId:     {user_id}")
    print(f"  UserArn:    {user.get('Arn')}")
    print(f"  Username:   {user.get('Username')}")
    print(f"  SecurityProfileId(Admin): {security_profile_id}")
    print(f"  RoutingProfileId:         {routing_profile_id}")


if __name__ == "__main__":
    main()
