# Cost controls and teardown

Use only `t3.micro`/`db.t3.micro` where eligible, keep RDS Single-AZ, avoid NAT Gateway, set an S3 lifecycle expiration for old proof objects, and delete test uploads. CloudWatch alarms and dashboards should be scoped to this project.

When finished, stop or terminate EC2, delete the RDS instance after taking any required snapshot, empty and delete the S3 bucket, delete the SQS queue and SNS topic, remove CloudWatch log groups/dashboards/alarms, delete the SSM parameters and IAM instance profile/role, then remove the security groups, subnets, route tables, IGW, and VPC. Confirm billing has no remaining project resources.
