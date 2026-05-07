import boto3
import pandas as pd

REGION = 'us-east-1'

RELEVANT_RESOURCE_TYPES = [
    'ec2:instance',
    'ec2:volume',          
    'ec2:vpc',
    'ec2:subnet',
    'ec2:elastic-ip',      
    'ec2:natgateway',
    'ec2:internet-gateway',
    'ec2:route-table',
    'ecr:repository',
    'eks:cluster',
    'eks:nodegroup',
    'ssm:parameter',       
    'secretsmanager:secret',
    'elasticloadbalancing:loadbalancer',
    'elasticloadbalancing:targetgroup',
    'rds:db',
    's3:bucket',
    'lambda:function',
    'logs:log-group'       
]

def get_tagged_resources():
    client = boto3.client('resourcegroupstaggingapi', region_name=REGION)
    tagged_resources = []
    paginator = client.get_paginator('get_resources')
    
    for page in paginator.paginate():
        for resource in page['ResourceTagMappingList']:
            tags = resource.get('Tags', [])
            if tags:
                arn = resource['ResourceARN']
                service = arn.split(':')[2] if len(arn.split(':')) > 2 else 'unknown'
                tags_dict = {tag['Key']: tag['Value'] for tag in tags}
                
                tagged_resources.append({
                    'Resource ARN': arn,
                    'Service Type': service,
                    'Tags': str(tags_dict)
                })
                
    return tagged_resources

def get_untagged_resources():
    client = boto3.client('resource-explorer-2', region_name=REGION)
    untagged = []
    
    try:
        paginator = client.get_paginator('search')
        
        query = f"region:{REGION} tag:none -tag.key:aws*"
        
        for page in paginator.paginate(QueryString=query):
            for res in page['Resources']:
                res_type = res['ResourceType']
                
                if res_type in RELEVANT_RESOURCE_TYPES:
                    untagged.append({
                        'Resource ARN': res['Arn'],
                        'Service Type': res_type
                    })
                
    except Exception as e:
        print(f"Failed to query Resource Explorer. Error: {e}")
        
    return untagged

def main():
    print("Scanning for Tagged Resources...")
    tagged = get_tagged_resources()
    if tagged:
        df_tagged = pd.DataFrame(tagged)
        df_tagged.to_csv('tagged_resources.csv', index=False)
        print(f"Saved {len(tagged)} tagged resources to 'tagged_resources.csv'")

    print("\nScanning for Untagged CORE Resources using AWS Resource Explorer...")
    untagged = get_untagged_resources()
    if untagged:
        df_untagged = pd.DataFrame(untagged)
        df_untagged.to_csv('untagged_resources.csv', index=False)
        print(f"Saved {len(untagged)} Actionable untagged resources to 'untagged_resources.csv'")
        
        print("\nUntagged Resources found:")
        for idx, item in enumerate(untagged, 1):
            print(f"  {idx}. [{item['Service Type']}] {item['Resource ARN'].split(':')[-1]}")
    else:
        print("Awesome! 0 untagged core resources found. Your infrastructure is perfectly compliant.")

if __name__ == "__main__":
    main()