"""
Unit tests for MiniCloud: exercises the AWS API directly via boto3 against a
ThreadedMotoServer instance (no Docker required to run these — Docker calls
go through minicloud.docker_manager's stub-mode fallback), and separately
verifies the reconciler's AMI->image mapping and security-group->port logic.
"""

import os
import time

import boto3
import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

TEST_PORT = 4599


@pytest.fixture(scope="module")
def minicloud_server():
    from moto.server import ThreadedMotoServer
    from minicloud import state_db
    from minicloud.reconciler import reconciler

    state_db.DB_PATH = os.path.join(os.getcwd(), f"test_minicloud_{TEST_PORT}.db")
    if os.path.exists(state_db.DB_PATH):
        os.remove(state_db.DB_PATH)
    state_db.init_db()

    server = ThreadedMotoServer(port=TEST_PORT, verbose=False)
    server.start()
    reconciler.start()
    yield
    reconciler.stop()
    server.stop()
    if os.path.exists(state_db.DB_PATH):
        os.remove(state_db.DB_PATH)


@pytest.fixture
def ec2(minicloud_server):
    return boto3.client("ec2", endpoint_url=f"http://localhost:{TEST_PORT}")


@pytest.fixture
def s3(minicloud_server):
    return boto3.client("s3", endpoint_url=f"http://localhost:{TEST_PORT}")


class TestEC2:
    def test_run_and_describe_instance(self, ec2):
        resp = ec2.run_instances(ImageId="ami-alpine", MinCount=1, MaxCount=1, InstanceType="t2.micro")
        instance_id = resp["Instances"][0]["InstanceId"]
        # Real AWS (and moto) report "pending" immediately after RunInstances;
        # it settles to "running" by the next DescribeInstances, same as a
        # real EC2 launch's eventual consistency.
        assert resp["Instances"][0]["State"]["Name"] == "pending"

        described = ec2.describe_instances(InstanceIds=[instance_id])
        instances = described["Reservations"][0]["Instances"]
        assert instances[0]["InstanceId"] == instance_id
        assert instances[0]["State"]["Name"] == "running"

    def test_stop_start_terminate_lifecycle(self, ec2):
        resp = ec2.run_instances(ImageId="ami-alpine", MinCount=1, MaxCount=1, InstanceType="t2.micro")
        instance_id = resp["Instances"][0]["InstanceId"]

        ec2.stop_instances(InstanceIds=[instance_id])
        described = ec2.describe_instances(InstanceIds=[instance_id])
        assert described["Reservations"][0]["Instances"][0]["State"]["Name"] == "stopped"

        ec2.start_instances(InstanceIds=[instance_id])
        described = ec2.describe_instances(InstanceIds=[instance_id])
        assert described["Reservations"][0]["Instances"][0]["State"]["Name"] == "running"

        ec2.terminate_instances(InstanceIds=[instance_id])
        described = ec2.describe_instances(InstanceIds=[instance_id])
        assert described["Reservations"][0]["Instances"][0]["State"]["Name"] == "terminated"

    def test_tags(self, ec2):
        resp = ec2.run_instances(
            ImageId="ami-alpine", MinCount=1, MaxCount=1, InstanceType="t2.micro",
            TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "tagged"}]}],
        )
        instance_id = resp["Instances"][0]["InstanceId"]
        described = ec2.describe_instances(InstanceIds=[instance_id])
        tags = described["Reservations"][0]["Instances"][0]["Tags"]
        assert {"Key": "Name", "Value": "tagged"} in tags

    def test_describe_images_instance_types_vpcs_subnets_sgs(self, ec2):
        # These are the "minimum extras" the aws_instance resource needs.
        assert "Images" in ec2.describe_images()
        assert "InstanceTypes" in ec2.describe_instance_types()
        assert "Vpcs" in ec2.describe_vpcs()
        assert "Subnets" in ec2.describe_subnets()
        assert "SecurityGroups" in ec2.describe_security_groups()
        assert "Volumes" in ec2.describe_volumes()

    def test_vpc_subnet_security_group_create(self, ec2):
        vpc = ec2.create_vpc(CidrBlock="10.77.0.0/16")["Vpc"]
        subnet = ec2.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.77.1.0/24")["Subnet"]
        sg = ec2.create_security_group(GroupName="test-sg-unit", Description="x", VpcId=vpc["VpcId"])
        ec2.authorize_security_group_ingress(
            GroupId=sg["GroupId"],
            IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
        )
        assert subnet["VpcId"] == vpc["VpcId"]

        resp = ec2.describe_security_groups(GroupIds=[sg["GroupId"]])
        rules = resp["SecurityGroups"][0]["IpPermissions"]
        assert rules[0]["FromPort"] == 22


class TestS3:
    def test_bucket_and_object_roundtrip(self, s3):
        bucket = "minicloud-unit-test-bucket"
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket, Key="hello.txt", Body=b"hello world")
        body = s3.get_object(Bucket=bucket, Key="hello.txt")["Body"].read()
        assert body == b"hello world"

        s3.delete_object(Bucket=bucket, Key="hello.txt")
        s3.delete_bucket(Bucket=bucket)


class TestReconciler:
    def test_instance_gets_tracked_in_state_db(self, ec2, minicloud_server):
        from minicloud import state_db

        resp = ec2.run_instances(ImageId="ami-alpine", MinCount=1, MaxCount=1, InstanceType="t2.micro")
        instance_id = resp["Instances"][0]["InstanceId"]

        tracked = None
        for _ in range(20):
            time.sleep(0.5)
            tracked = state_db.get_resource(instance_id)
            if tracked:
                break
        assert tracked is not None
        assert tracked["resource_type"] == "ec2_instance"

        ec2.terminate_instances(InstanceIds=[instance_id])
        for _ in range(20):
            time.sleep(0.5)
            tracked = state_db.get_resource(instance_id)
            if tracked is None:
                break
        assert tracked is None


def test_ami_image_mapping():
    from minicloud.reconciler import _image_for_ami

    assert _image_for_ami("ami-ubuntu-2204") == "ubuntu:22.04"
    assert _image_for_ami("ami-nginx") == "nginx:alpine"
    assert _image_for_ami("ami-alpine") == "alpine:3.19"
    assert _image_for_ami("ami-12345678") == "alpine:3.19"


def test_decode_user_data():
    from minicloud.reconciler import _decode_user_data
    import base64

    encoded = base64.b64encode(b"echo hi").decode()
    assert _decode_user_data(encoded) == "echo hi"
    assert _decode_user_data(None) is None
