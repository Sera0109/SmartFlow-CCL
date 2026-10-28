# SmartFlow

SmartFlow is a delivery-management mini project for the workflow **Place Order -> Assign Best Available Agent -> Deliver -> Upload Proof -> Notify -> Analyze**. It uses FastAPI on EC2, private MySQL on RDS, S3, SQS, SNS, SSM Parameter Store, IAM, and CloudWatch in AWS. Local mode provides file-backed SQS/S3 and console notifications so the complete flow can be demonstrated without AWS credentials.

## Stack and architecture

- Python 3.11+, FastAPI, Pydantic, PyMySQL, boto3, pytest
- React 18 and Vite with ordinary responsive CSS
- EC2 `t3.micro` / Amazon Linux 2023, Nginx, systemd
- Custom VPC `10.0.0.0/16`, public and private subnets in two AZs, no NAT Gateway
- Private Single-AZ RDS MySQL `db.t3.micro` where eligible
- Standard SQS queue for asynchronous assignment and SNS notifications
- Private encrypted S3 bucket for delivery proof

See [docs/architecture.md](docs/architecture.md) and [infrastructure/README.md](infrastructure/README.md) for deployment design. AWS resources are never provisioned automatically.

## Local setup (Windows PowerShell)

Install Python 3.11+, Node.js 18+, and MySQL. From the repository root:

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local MySQL database and user, set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in `.env`, then load the schema:

```powershell
python -m scripts.load_schema
uvicorn app.main:app --reload --port 8000
```

In another PowerShell terminal, run the assignment worker:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

In a third terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). With `SMARTFLOW_LOCAL=1`, no AWS credentials are needed. SQS messages are stored in `local_queue.txt`, proof files in `local_s3/`, and SNS messages are printed. Those paths are excluded by `.gitignore`.

## API

- `GET /health`
- `POST /orders`
- `GET /orders/{id}`
- `GET /agents`
- `POST /agents/{id}/status`
- `GET /agents/{id}/orders`
- `POST /orders/{id}/out-for-delivery`
- `POST /orders/{id}/proof`
- `GET /orders/{id}/proof-url`
- `GET /analytics`

FastAPI Swagger is available at `http://localhost:8000/docs`. The frontend's four sections use real API responses: Place Order, Track Order, Agent Dashboard, and Admin Analytics.

## Tests and workflow verification

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

For the full demonstration, place an order, wait for the worker to assign an agent, confirm assignment in Track Order, move it out for delivery, upload an image proof, open its proof URL, and refresh Admin Analytics. Details are in [docs/testing.md](docs/testing.md).

## AWS deployment

1. Build the frontend with `npm run build` and copy it to the EC2 Nginx root.
2. Create VPC, subnets, route tables, EC2, private RDS, S3, SQS, SNS, IAM, and CloudWatch resources according to [infrastructure/README.md](infrastructure/README.md).
3. Store the listed `/smartflow/*` values in SSM Parameter Store; use SecureString for the database password.
4. Replace only the explicitly marked placeholders in [deploy/iam-policy.json](deploy/iam-policy.json), install the systemd units and [deploy/nginx.conf](deploy/nginx.conf), and set production environment variables.
5. Run the schema loader against RDS, enable API and worker services, and verify `/health`, logs, the SQS flow, and the dashboard.

Do not commit passwords, AWS keys, account IDs, ARNs, or private keys. The IAM policy is a template because actual ARNs are obtained from AWS during deployment.

## Cost and security

The design avoids NAT Gateway and Multi-AZ RDS, uses micro instances, blocks public S3 access, uses parameterized SQL, validates request data, keeps proofs private, and uses an EC2 instance role instead of access keys. Follow [docs/cost-and-teardown.md](docs/cost-and-teardown.md) to remove all resources after a demonstration.

## Submission evidence checklist

- Architecture diagram showing VPC, EC2, RDS, S3, SQS, SNS, SSM, IAM, and CloudWatch
- Swagger `/docs` and `/health` screenshots
- Successful order, assignment, proof URL, and analytics screenshots
- SQS message/worker log and SNS notification evidence
- CloudWatch dashboard and alarm screenshots
- AWS security groups, private RDS, blocked-public-access S3, and Parameter Store screenshots
