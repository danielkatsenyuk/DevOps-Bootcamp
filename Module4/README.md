# Module 4 – Python: Map & Analyze Your AWS Environment

## Overview
Two Python scripts that use **Boto3** to map all AWS resources, analyze costs via **Cost Explorer**, and tag untagged resources for compliance.

## Scripts

### `map_env.py` – Task 1: Map Your Environment

Scans the AWS account and produces two CSV files:

| Output | Description |
|--------|-------------|
| `tagged_resources.csv` | All resources with at least one tag |
| `untagged_resources.csv` | Core resources with zero tags (via Resource Explorer) |

**Resource types monitored:** EC2, EKS, ECR, SSM, Secrets Manager, ELB, RDS, S3, Lambda, CloudWatch Logs

```bash
python map_env.py
```

> ⚠️ `untagged_resources.csv` requires **AWS Resource Explorer** to be enabled in your account.

---

### `cost_analysis.py` – Task 2: Know Your Environment

Reads the CSVs produced by `map_env.py`, enriches them with Cost Explorer data, and prints a FinOps report.

| Output | Description |
|--------|-------------|
| `my_tagged_costs.csv` | Tagged resources with ARN, name, type, daily cost, region |
| `my_untagged_costs.csv` | Untagged resources with same schema |

**Report includes:**
- Total daily cost (all services)
- Top 5 most expensive resources
- Percentage of cost from untagged resources
- Average daily cost per service type
- Auto-tags all untagged resources with `Account-level-resource=True`, `Module-Number=4`, `Owner=<name>`

```bash
# Run map_env.py first, then:
python cost_analysis.py
```

## Cost Calculation Logic

- Fetches **14 days** of daily-granularity cost data from Cost Explorer
- Calculates **average daily cost** per resource ID
- Falls back to 2 days if 14-day data is insufficient
- Matches resources by ARN or by the resource ID portion of the ARN

## Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install boto3 pandas

# Run
python map_env.py
python cost_analysis.py
```

## IAM Permissions Required

The executing IAM role/user needs:
- `tag:GetResources`
- `resource-explorer-2:Search`
- `ce:GetCostAndUsage`
- `ce:GetCostAndUsageWithResources`
- `tag:TagResources`

## Notes
- CSV output files are excluded from git (`.gitignore`)
- The `venv/` directory is excluded from git
- `OWNER_NAME` in `cost_analysis.py` must match the `CreatedBy` tag value used in Terraform
