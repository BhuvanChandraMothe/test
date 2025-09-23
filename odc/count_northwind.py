import requests
import xml.etree.ElementTree as ET

def get_entity_counts():
    """
    Fetches and prints the record count for each entity set in the Northwind OData service.
    """
    base_url = "https://services.odata.org/V4/Northwind/Northwind.svc/"
    metadata_url = f"{base_url}$metadata"
    entity_counts = {}
    
    print("Fetching metadata to identify all entities...")

    try:
        # 1. Get the metadata XML to find all entity set names
        metadata_response = requests.get(metadata_url)
        metadata_response.raise_for_status() # Raise an exception for bad status codes

        root = ET.fromstring(metadata_response.content)
        
        # Define the XML namespace to properly find elements
        # The namespace is found in the <edmx:Edmx> tag's attributes
        namespaces = {'edmx': 'http://docs.oasis-open.org/odata/ns/edmx', 'edm': 'http://docs.oasis-open.org/odata/ns/edm'}
        
        # Find all <EntitySet> elements within the <EntityContainer>
        entity_sets = root.findall('.//edm:EntityContainer/edm:EntitySet', namespaces)
        entity_names = [entity.get('Name') for entity in entity_sets]

        if not entity_names:
            print("Could not find any entity sets in the metadata.")
            return

        print(f"Found {len(entity_names)} entities. Now fetching counts for each...\n")

        # 2. Loop through each entity name and get its count
        for name in sorted(entity_names):
            count_url = f"{base_url}{name}?$count=true"
            
            try:
                # Set headers to explicitly request a JSON response
                headers = {'Accept': 'application/json'}
                count_response = requests.get(count_url, headers=headers)
                count_response.raise_for_status()
                
                # The count is in the '@odata.count' field of the JSON response
                data = count_response.json()
                count = data.get('@odata.count')
                
                if count is not None:
                    entity_counts[name] = count
                    print(f" - {name}: {count}")
                else:
                    # Some entities might not support count, handle this gracefully
                    print(f"  {name}: Count not available.")
                    entity_counts[name] = "N/A"

            except requests.exceptions.RequestException as e:
                print(f"Could not fetch count for {name}. Error: {e}")
                entity_counts[name] = "Error"
    
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch metadata. Error: {e}")
    
    print("\n--- Consolidated List of Counts ---")
    for name, count in entity_counts.items():
        print(f"{name:<40} {count}")

if __name__ == "__main__":
    get_entity_counts()