# AWS infrastructure runbook

Create resources manually or with an approved IaC tool in `ap-south-1`; this repository intentionally does not auto-provision billable infrastructure.

1. Create VPC `10.0.0.0/16`, two public subnets and two private subnets across two AZs, and an Internet Gateway. Public route tables point to the IGW. There is deliberately no NAT Gateway.
2. Create a public Amazon Linux 2023 EC2 `t3.micro` instance with the deployment IAM role, HTTP/80 open to the internet, and SSH/22 restricted to the operator's current IP.
3. Create a private Single-AZ RDS MySQL `db.t3.micro` with 20 GB where eligible. Its security group permits 3306 only from the EC2 security group.
4. Create an encrypted, private S3 bucket with public access blocked and a lifecycle rule for old proofs.
5. Create the Standard SQS queue `smartflow-orders` with 60-second visibility, 20-second long polling, and one-day retention, plus an SNS topic.
6. Put database and resource values in Parameter Store as `/smartflow/db_host`, `/smartflow/db_user`, `/smartflow/db_password` (SecureString), `/smartflow/db_name`, `/smartflow/sqs_url`, `/smartflow/sns_arn`, and `/smartflow/bucket`.
7. Replace placeholders in `deploy/iam-policy.json`, attach it to the EC2 instance profile, then deploy code, frontend, Nginx, and systemd services.
8. Configure a CloudWatch dashboard for EC2 CPU, RDS CPU/connections, SQS visible messages, and API/worker log groups. Alert on sustained EC2 CPU > 70%, RDS storage/CPU pressure, and SQS backlog.

Do not commit passwords, ARNs, account IDs, or private keys. Obtain actual identifiers from AWS during deployment.
