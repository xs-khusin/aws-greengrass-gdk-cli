import json
from pathlib import Path

import boto3


def update_config(config_file, component_name, region, bucket, author, version="NEXT_PATCH"):
    # Update gdk-config file mandatory field like region.
    with open(str(config_file), "r") as f:
        config = json.loads(f.read())
        config["component"][component_name]["author"] = author
        config["component"][component_name]["publish"]["region"] = region
        config["component"][component_name]["publish"]["bucket"] = bucket
        config["component"][component_name]["version"] = version
    with open(str(config_file), "w") as f:
        f.write(json.dumps(config))


def clean_up_aws_resources(component_name, component_version, region):
    account_num = get_acc_num(region)
    delete_component(component_name, component_version, region, account_num)
    delete_s3_artifact(region, account_num, component_name, component_version)


def delete_s3_artifact(region, account, component_name, component_version):
    s3_client = create_s3_client(region)
    try:
        bucket = f"gdk-cli-uat-{region}-{account}"
        res = s3_client.list_objects(Bucket=bucket)
        if "Contents" not in res:
            return
        for f in res["Contents"]:
            if f"{component_name}/{component_version}" in f["Key"]:
                s3_client.delete_object(Bucket=bucket, Key=f["Key"])
    except Exception as e:
        print(f"Failed to delete s3 objects from bucket - {bucket}")
        print(e)


def delete_component(name, version, region, account_num):
    try:
        gg_client = boto3.client("greengrassv2", region_name=region)
        arn = f"arn:aws:greengrass:{region}:{account_num}:components:{name}:versions:{version}"
        gg_client.delete_component(arn=arn)
        print(f"Deleted component {name}-{version} in {region}")
    except Exception as e:
        print(f"Failed to delete the component {name}-{version} in {region}")
        print(e)


def get_version_created(recipes_path, component_name):
    for f in Path(recipes_path).iterdir():
        if component_name in str(f.resolve()):
            file_name = f.name
            split_file_name = file_name.split(f"{component_name}-")
            split_for_version = split_file_name[1].split(".yaml")[0]
            return split_for_version


def create_s3_client(region):
    return boto3.client("s3", region_name=region)


def get_acc_num(region):
    sts_client = boto3.client("sts", region_name=region)
    caller_identity_response = sts_client.get_caller_identity()
    return caller_identity_response["Account"]
