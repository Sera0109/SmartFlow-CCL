# SmartFlow architecture

The public EC2 instance runs Nginx, the FastAPI API, and an SQS worker. RDS MySQL remains in private subnets. New orders are committed to MySQL before their IDs enter SQS; the worker selects the lowest `distance_km + 2 * active_order_count` score and records the assignment. Delivery proof is private S3 in AWS (or `local_s3/` locally), and SNS notifies stakeholders. CloudWatch receives service logs and operational metrics.

The deployment uses no NAT Gateway, no Multi-AZ RDS, and no serverless compute to keep the college demonstration within its requested cost controls.
