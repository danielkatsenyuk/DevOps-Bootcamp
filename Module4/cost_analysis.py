import boto3
import pandas as pd
from datetime import datetime, timedelta
import re

# Settings
REGION = 'us-east-1'
OWNER_NAME = 'Daniel Katsenyuk'
DAYS_TO_CHECK = 14

def get_costs_from_aws():
    """Fetches cost data from AWS Cost Explorer grouped by resource"""
    ce_client = boto3.client('ce', region_name=REGION)
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=DAYS_TO_CHECK)).strftime('%Y-%m-%d')
    
    costs = {}
    try:
        response = ce_client.get_cost_and_usage_with_resources(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='DAILY',
            Filter={'Dimensions': {'Key': 'REGION', 'Values': [REGION]}},
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'RESOURCE_ID'}]
        )
        
        resource_totals = {}
        days_counted = len(response['ResultsByTime'])
        
        for day in response['ResultsByTime']:
            for group in day['Groups']:
                res_id = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                resource_totals[res_id] = resource_totals.get(res_id, 0) + amount
                
        for res_id, total in resource_totals.items():
            costs[res_id] = total / days_counted
            
    except Exception as e:
        print(f"Warning: Could not fetch Cost Explorer data. You might need to enable it in AWS Console. Error: {e}")
    
    return costs

def get_tag_value(tags_str, key):
    """Extracts a specific tag value from the string using regex, completely avoiding 'ast'"""
    if pd.isna(tags_str):
        return None
    match = re.search(f"'{key}':\s*'([^']*)'", str(tags_str))
    return match.group(1) if match else None

def get_resource_name(arn, tags_str):
    """Attempts to extract the Name tag, otherwise cuts from the ARN"""
    name = get_tag_value(tags_str, 'Name')
    if name:
        return name
    return arn.split(':')[-1].split('/')[-1]

def tag_untagged_resources(untagged_arns):
    if not untagged_arns:
        return
        
    print(f"\nTagging {len(untagged_arns)} untagged resources...")
    client = boto3.client('resourcegroupstaggingapi', region_name=REGION)
    tags_to_add = {'Account-level-resource': 'True', 'Module-Number': '4', 'Owner': OWNER_NAME}
    
    for i in range(0, len(untagged_arns), 20):
        batch = untagged_arns[i:i+20]
        try:
            client.tag_resources(ResourceARNList=batch, Tags=tags_to_add)
        except Exception as e:
            print(f"Failed to tag batch. Error: {e}")
    print("Tagging completed.")

def main():
    print("Starting Cost Analysis and Environment Review...\n")
    
    # 1. Reading the files from task 1
    try:
        df_tagged = pd.read_csv('tagged_resources.csv')
    except FileNotFoundError:
        print("Could not find 'tagged_resources.csv'. Run map_env.py first!")
        return

    # 2. Reading the untagged file 
    try:
        df_untagged = pd.read_csv('untagged_resources.csv')
    except FileNotFoundError:
        print("Awesome! No untagged resources file found. Assuming 100% tagging compliance.")
        df_untagged = pd.DataFrame(columns=['Resource ARN', 'Service Type'])

    
    # Scans the entire 'Tags' column and searches for the OWNER_NAME anywhere inside it
    my_resources = df_tagged[df_tagged['Tags'].str.contains(OWNER_NAME, case=False, na=False)].copy()
    
    print(f"Found {len(my_resources)} resources associated with '{OWNER_NAME}'.")

    # 4. Fetching costs
    print("Fetching cost data from AWS Cost Explorer...")
    aws_costs = get_costs_from_aws()
    
    def match_cost(arn):
        res_id = arn.split(':')[-1].split('/')[-1]
        return aws_costs.get(arn, aws_costs.get(res_id, 0.0))

    # 5. Processing tagged resources
    my_resources['Resource Name'] = my_resources.apply(lambda row: get_resource_name(row['Resource ARN'], row['Tags']), axis=1)
    my_resources['Daily Cost ($)'] = my_resources['Resource ARN'].apply(match_cost)
    my_resources['Region'] = REGION
    
    final_tagged = my_resources[['Resource ARN', 'Resource Name', 'Service Type', 'Daily Cost ($)', 'Region']]
    final_tagged.to_csv('my_tagged_costs.csv', index=False)
    
    total_untagged_cost = 0.0
    untagged_arns = []
    
    # 6. Processing untagged resources (only if they exist)
    if not df_untagged.empty:
        df_untagged['Resource Name'] = df_untagged['Resource ARN'].apply(lambda arn: arn.split(':')[-1].split('/')[-1])
        df_untagged['Daily Cost ($)'] = df_untagged['Resource ARN'].apply(match_cost)
        df_untagged['Region'] = REGION
        final_untagged = df_untagged[['Resource ARN', 'Resource Name', 'Service Type', 'Daily Cost ($)', 'Region']]
        final_untagged.to_csv('my_untagged_costs.csv', index=False)
        total_untagged_cost = final_untagged['Daily Cost ($)'].sum()
        untagged_arns = df_untagged['Resource ARN'].tolist()

    # 7. Printing the report
    total_tagged_cost = final_tagged['Daily Cost ($)'].sum()
    total_cost = total_tagged_cost + total_untagged_cost
    
    print("\n" + "="*40)
    print("FINOPS REPORT")
    print("="*40)
    print(f"Total Daily Cost (All Services): ${total_cost:.4f}")
    
    print("\nTop 5 Most Expensive Resources:")
    top_5 = final_tagged.nlargest(5, 'Daily Cost ($)')
    for idx, row in top_5.iterrows():
        print(f" - {row['Resource Name']} ({row['Service Type']}): ${row['Daily Cost ($)']:.4f}/day")
        
    if total_cost > 0:
        untagged_pct = (total_untagged_cost / total_cost) * 100
        print(f"\nPercentage of Untagged Costs: {untagged_pct:.2f}%")
    else:
        print("\nPercentage of Untagged Costs: 0.00% (Total cost is $0)")
        
    avg_service_cost = final_tagged.groupby('Service Type')['Daily Cost ($)'].mean()
    print("\nAverage Cost per Service Type:")
    for service, avg in avg_service_cost.items():
        print(f" - {service}: ${avg:.4f}/day")
        
    # 8. Tagging (if needed)
    if untagged_arns:
        tag_untagged_resources(untagged_arns)

if __name__ == "__main__":
    main()