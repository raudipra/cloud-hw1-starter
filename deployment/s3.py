import os
import json
import logging
import mimetypes

import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()  # take environment variables from .env

def create_bucket(bucket_name, region=None):
    """Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        if region is None:
            s3_client = boto3.client('s3')
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client('s3', region_name=region)
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name,
                                    CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload(bucket_name, path, region=None, key=None):
    """Upload file or directory to an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param path: String file or directory path on local filesystem
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :param key: String key for the file in S3 bucket
    :return: True if file is uploaded, else False
    """

    if os.path.isfile(path):
        return upload_file(bucket_name, path, region, key)
    elif os.path.isdir(path):
        return upload_dir(bucket_name, path, region, key)
    else:
        logging.error("Error: unsupported special file (socket, FIFO, device file)")
        return False

def set_bucket_web_config(bucket_name, region=None, index_doc=None, error_doc=None,
                         cors=True, public=True):
    try:
        # Get bucket
        s3_client = None
        if region is None:
            s3_client = boto3.client('s3')
        else:
            s3_client = boto3.client('s3', region_name=region)

        if cors:
            # Create the CORS configuration
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['Authorization'],
                    'AllowedMethods': ['GET', 'PUT'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['GET', 'PUT'],
                    'MaxAgeSeconds': 3000
                }]
            }
            
            # Set the new CORS configuration on the selected bucket
            s3_client.put_bucket_cors(
                Bucket=bucket_name, 
                CORSConfiguration=cors_configuration,
            )

        if public:
            # Create the bucket policy
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": [
                            "s3:GetObject"
                        ],
                        "Resource": [
                            "arn:aws:s3:::{}/*".format(bucket_name)
                        ]
                    }
                ]
            }

            # Convert the policy to a JSON string
            bucket_policy = json.dumps(bucket_policy)

            # Set the new policy on the given bucket
            s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)

            # Create the configuration for the website
            if index_doc is None:
                index_doc = "index.html"
            
            if error_doc is None:
                error_doc = "error.html"

            website_configuration = {
                'ErrorDocument': {'Key': error_doc},
                'IndexDocument': {'Suffix': index_doc},
            }

            # Set the new policy on the selected bucket
            s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration=website_configuration
            )
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_file(bucket_name, filepath, region=None, key=None):
    try:
        # Get bucket
        s3_client = None
        if region is None:
            s3_client = boto3.client('s3')
        else:
            s3_client = boto3.client('s3', region_name=region)

        # Set the right content type
        extra_args = {}
        content_type = mimetypes.guess_type(filepath)[0]
        if content_type:
            extra_args = {'ContentType': content_type}

        # Upload file
        if key is None:
            # Key follows filepath
            s3_client.upload_file(filepath, bucket_name, filepath,
                                  ExtraArgs=extra_args)
        else:
            s3_client.upload_file(filepath, bucket_name, key,
                                  ExtraArgs=extra_args)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_dir(bucket_name, dirpath, region=None, key=None):
    try:
        # Get bucket
        s3_client = None
        if region is None:
            s3_client = boto3.client('s3')
        else:
            s3_client = boto3.client('s3', region_name=region)

        # Upload file
        if key is None:
            key = dirpath
        
        # Add working dir to relative path, makes it an abs path
        if dirpath[0] != "/":
            dirpath = os.path.join(os.getcwd(), dirpath)

        for root, _, files in os.walk(dirpath):
            for name in files:
                # Set the file key based on key
                path = os.path.join(root, name)
                file_key = path.replace(dirpath, key, 1)

                # Set the right content type
                extra_args = {}
                content_type = mimetypes.guess_type(path)[0]
                if content_type:
                    extra_args = {'ContentType': content_type}
                
                s3_client.upload_file(path, bucket_name, file_key, 
                                      ExtraArgs=extra_args)
    except ClientError as e:
        logging.error(e)
        return False
    return True

bucket_name = "raudipra-coms6998-test"
create_bucket(bucket_name)
upload(bucket_name, "../src/", key="")
set_bucket_web_config(bucket_name, region=None, index_doc="chat.html", 
                      error_doc=None, cors=True, public=True)

