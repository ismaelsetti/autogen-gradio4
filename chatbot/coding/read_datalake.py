# filename: read_datalake.py
# Import required packages
import pandas as pd
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import DefaultAzureCredential

# Set up your Azure AD credentials
client_id = "your_client_id"
tenant_id = "your_tenant_id"
client_secret = "your_client_secret"

# Create a Service Principal credential object
credential = DefaultAzureCredential(client_id=client_id, tenant_id=tenant_id, client_secret_key=client_secret)

# Create a DataLakeServiceClient object using the service principal credential
service_client = DataLakeServiceClient(account_url=f"https://{account_name}.dfs.core.windows.net", credential=credential)

# Set your ADLSG2 path and file name
path = "/path/to/your/file.csv"
file_name = "your_file.csv"

try:
    # Use the DataLakeServiceClient object to read the file
    data_lake_client = service_client.get_file_client(path)
    with open(file_name, 'wb') as file:
        file_data = data_lake_client.download_blob().read()
        file.write(file_data)

    # Convert the file contents to a pandas DataFrame
    df = pd.read_csv(file_name)
except Exception as e:
    print(f"Error reading file: {str(e)}")
finally:
    # Clean up by deleting the temporary file
    import os
    os.remove(file_name)