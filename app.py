< # Perfect! 😄 Here's the fully merged, ready-to-run Python script that includes everything:

EC2 management across all regions with optional tag filtering

S3 bucket listing globally

S3 deletion by exact filename, wildcard/pattern, or object tag 
this is the new line added
this is newly added for git cherrypick #>






import boto3
import fnmatch

def parse_selection(choice, instance_info):
    """Parse user input like 1,5-10,20 into selected instances."""
    if choice.lower() == "all":
        return instance_info

    selected = []
    parts = choice.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                for i in range(start, end + 1):
                    if 1 <= i <= len(instance_info):
                        selected.append(instance_info[i - 1])
            except ValueError:
                continue
        else:
            try:
                idx = int(part)
                if 1 <= idx <= len(instance_info):
                    selected.append(instance_info[idx - 1])
            except ValueError:
                continue
    return selected

def get_all_regions():
    """Get all available AWS regions for EC2."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    response = ec2.describe_regions(AllRegions=True)
    return [region["RegionName"] for region in response["Regions"] if region["OptInStatus"] in ["opt-in-not-required", "opted-in"]]

def manage_ec2_instances(tag_key=None, tag_value=None):
    """List and manage EC2 instances across all regions."""
    all_regions = get_all_regions()
    instance_info = []

    for region in all_regions:
        ec2 = boto3.client("ec2", region_name=region)
        filters = []
        if tag_key and tag_value:
            filters.append({"Name": f"tag:{tag_key}", "Values": [tag_value]})

        response = ec2.describe_instances(Filters=filters)
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                instance_type = instance["InstanceType"]
                state = instance["State"]["Name"]
                name = None
                if "Tags" in instance:
                    for tag in instance["Tags"]:
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                instance_info.append({
                    "InstanceId": instance_id,
                    "Type": instance_type,
                    "State": state,
                    "Name": name if name else "Unnamed",
                    "Region": region
                })

    if not instance_info:
        print("No EC2 instances found across any region.")
        return

    print("\nEC2 Instances (All Regions):")
    for i, inst in enumerate(instance_info, start=1):
        print(f"{i}. {inst['InstanceId']} ({inst['Name']}) - {inst['Type']} - {inst['State']} [{inst['Region']}]")

    choice = input("\nEnter instance numbers (e.g., 1-200, 5,10) or 'all': ")
    selected = parse_selection(choice, instance_info)

    if not selected:
        print("No valid instances selected.")
        return

    print("\nSelected instances:")
    for inst in selected:
        print(f"- {inst['InstanceId']} ({inst['Name']}) - {inst['State']} [{inst['Region']}]")

    action = input("\nDo you want to 'start' or 'stop' these instances? ").lower()
    region_map = {}
    for inst in selected:
        region_map.setdefault(inst["Region"], []).append(inst["InstanceId"])

    for region, ids in region_map.items():
        ec2 = boto3.client("ec2", region_name=region)
        if action == "stop":
            print(f"Stopping in {region}: {ids}")
            ec2.stop_instances(InstanceIds=ids)
        elif action == "start":
            print(f"Starting in {region}: {ids}")
            ec2.start_instances(InstanceIds=ids)
        else:
            print("Invalid action. No changes made.")

def list_and_manage_s3():
    """List all S3 buckets globally and optionally delete objects by filename, wildcard, or tag."""
    s3 = boto3.client("s3")
    response = s3.list_buckets()
    buckets = response["Buckets"]

    if not buckets:
        print("No S3 buckets found.")
        return

    print("\nS3 Buckets and Contents (Global):")
    bucket_objects = {}
    s3_resource = boto3.resource("s3")

    for bucket in buckets:
        bucket_name = bucket["Name"]
        print(f"\nBucket: {bucket_name}")
        bucket_obj = s3_resource.Bucket(bucket_name)
        bucket_objects[bucket_name] = []
        found = False
        try:
            for obj in bucket_obj.objects.all():
                print(f"  {obj.key}")
                bucket_objects[bucket_name].append(obj.key)
                found = True
        except Exception as e:
            print(f"  (Access Denied or Error: {e})")
        if not found:
            print("  (Empty bucket)")

    delete_choice = input("\nDo you want to delete any files from S3? (y/n): ").strip().lower()
    if delete_choice != "y":
        return

    method = input("Delete by (1) filename/pattern or (2) tag? Enter 1 or 2: ").strip()
    deleted_files = []

    if method == "1":
        pattern_to_delete = input("Enter filename or pattern to delete (e.g., '*.log' or 'report-*'): ").strip()
        for bucket, objects in bucket_objects.items():
            for obj_key in objects:
                if fnmatch.fnmatch(obj_key, pattern_to_delete):
                    print(f"Deleting {obj_key} from bucket: {bucket}")
                    try:
                        s3.delete_object(Bucket=bucket, Key=obj_key)
                        deleted_files.append((bucket, obj_key))
                    except Exception as e:
                        print(f"  Error deleting {obj_key} from {bucket}: {e}")

    elif method == "2":
        tag_key = input("Enter tag key (e.g., Project, Owner): ").strip()
        tag_value = input("Enter tag value to match (e.g., myproject): ").strip()
        for bucket in buckets:
            bucket_name = bucket["Name"]
            bucket_obj = s3_resource.Bucket(bucket_name)
            try:
                for obj in bucket_obj.objects.all():
                    try:
                        obj_tagging = s3.get_object_tagging(Bucket=bucket_name, Key=obj.key)
                        tags = {t['Key']: t['Value'] for t in obj_tagging.get('TagSet', [])}
                        if tags.get(tag_key) == tag_value:
                            print(f"Deleting {obj.key} from bucket: {bucket_name} (matched tag {tag_key}={tag_value})")
                            s3.delete_object(Bucket=bucket_name, Key=obj.key)
                            deleted_files.append((bucket_name, obj.key))
                    except Exception:
                        continue
            except Exception:
                continue
    else:
        print("Invalid choice. No files deleted.")
        return

    if deleted_files:
        print("\n✅ Deleted files:")
        for b, f in deleted_files:
            print(f"- {f} from {b}")
    else:
        print("\n⚠️ No matching files found to delete.")

if __name__ == "__main__":
    # EC2 Tag filter
    use_tag = input("Filter EC2 by tag? (y/n): ").strip().lower()
    tag_key = None
    tag_value = None
    if use_tag == "y":
        tag_key = input("Enter tag key (e.g., Name, Environment): ").strip()
        tag_value = input("Enter tag value (e.g., server, dev): ").strip()

    # Manage EC2 across all regions
    manage_ec2_instances(tag_key=tag_key, tag_value=tag_value)

    # List S3 and optionally delete files by filename/pattern or tag
    list_and_manage_s3()
