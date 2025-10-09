"""
Python Client for SAP OData Connector API

Easy-to-use client for interacting with the API.
"""
import requests
import time
from typing import Dict, Any, Optional, List


class SAPODataAPIClient:
    """Python client for SAP OData Connector API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.config_id: Optional[str] = None
        self.session_id: Optional[str] = None
    
    def create_config(
        self,
        sap_server: str,
        sap_module: str,
        username: str,
        password: str,
        sap_port: int = 443,
        use_https: bool = True,
        output_directory: str = "./api_output",
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Step 1: Create configuration"""
        response = requests.post(
            f"{self.base_url}/api/v1/configs",
            json={
                "sap_server": sap_server,
                "sap_port": sap_port,
                "sap_module": sap_module,
                "use_https": use_https,
                "username": username,
                "password": password,
                "output_directory": output_directory,
                "timeout": timeout
            }
        )
        response.raise_for_status()
        
        result = response.json()
        self.config_id = result["config_id"]
        return result
    
    def create_session(self, config_id: Optional[str] = None) -> Dict[str, Any]:
        """Step 2: Initialize session"""
        if not config_id and not self.config_id:
            raise ValueError("No config_id provided. Call create_config() first or provide config_id.")
        
        config_id = config_id or self.config_id
        
        response = requests.post(
            f"{self.base_url}/api/v1/sessions",
            json={"config_id": config_id}
        )
        response.raise_for_status()
        
        result = response.json()
        self.session_id = result["session_id"]
        return result
    
    def list_entities(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """List entities in session"""
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session_id. Call create_session() first.")
        
        response = requests.get(
            f"{self.base_url}/api/v1/sessions/{session_id}/entities"
        )
        response.raise_for_status()
        return response.json()
    
    def query(
        self,
        entity_name: Optional[str] = None,
        selected_entities: Optional[List[str]] = None,
        filter_condition: Optional[str] = None,
        select_fields: Optional[str] = None,
        expand_relations: Optional[str] = None,
        order_by: Optional[str] = None,
        record_limit: Optional[int] = None,
        batch_size: int = 1000,
        max_workers: int = 5,
        session_id: Optional[str] = None,
        wait_for_completion: bool = True,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Step 3: Execute query"""
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session_id. Call create_session() first.")
        
        # Start query
        response = requests.post(
            f"{self.base_url}/api/v1/query",
            json={
                "session_id": session_id,
                "entity_name": entity_name,
                "selected_entities": selected_entities,
                "filter_condition": filter_condition,
                "select_fields": select_fields,
                "expand_relations": expand_relations,
                "order_by": order_by,
                "record_limit": record_limit,
                "batch_size": batch_size,
                "max_workers": max_workers
            }
        )
        response.raise_for_status()
        
        result = response.json()
        job_id = result["job_id"]
        
        if not wait_for_completion:
            return result
        
        # Wait for completion
        print(f"Job started: {job_id}")
        print("Waiting for completion", end="", flush=True)
        
        while True:
            status_response = requests.get(
                f"{self.base_url}/api/v1/jobs/{job_id}"
            )
            status_response.raise_for_status()
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                print(" ✓ Completed!")
                
                # Download results
                results_response = requests.get(
                    f"{self.base_url}/api/v1/jobs/{job_id}/download"
                )
                results_response.raise_for_status()
                return results_response.json()
            
            elif status_data["status"] == "failed":
                print(" ✗ Failed!")
                raise Exception(f"Query failed: {status_data.get('error')}")
            
            print(".", end="", flush=True)
            time.sleep(poll_interval)
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status"""
        response = requests.get(f"{self.base_url}/api/v1/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def download_results(self, job_id: str) -> Dict[str, Any]:
        """Download job results"""
        response = requests.get(f"{self.base_url}/api/v1/jobs/{job_id}/download")
        response.raise_for_status()
        return response.json()
    
    def list_configs(self) -> Dict[str, Any]:
        """List all configurations"""
        response = requests.get(f"{self.base_url}/api/v1/configs")
        response.raise_for_status()
        return response.json()
    
    def list_sessions(self, config_id: Optional[str] = None) -> Dict[str, Any]:
        """List all sessions"""
        params = {"config_id": config_id} if config_id else {}
        response = requests.get(f"{self.base_url}/api/v1/sessions", params=params)
        response.raise_for_status()
        return response.json()
    
    def list_jobs(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all jobs"""
        params = {}
        if session_id:
            params["session_id"] = session_id
        if status:
            params["status"] = status
        
        response = requests.get(f"{self.base_url}/api/v1/jobs", params=params)
        response.raise_for_status()
        return response.json()
    
    def delete_session(self, session_id: Optional[str] = None):
        """Delete session"""
        session_id = session_id or self.session_id
        if not session_id:
            return
        
        response = requests.delete(f"{self.base_url}/api/v1/sessions/{session_id}")
        response.raise_for_status()
        
        if session_id == self.session_id:
            self.session_id = None
        
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


# ============================================================================
# Example Usage
# ============================================================================

def main():
    """Example usage"""
    client = SAPODataAPIClient()
    
    try:
        # Health check
        print("\n" + "="*70)
        print("Health Check")
        print("="*70)
        health = client.health_check()
        print(f"Status: {health['status']}")
        print(f"Database stats: {health['database']}")
        
        # Step 1: Create config
        print("\n" + "="*70)
        print("Step 1: Create Configuration")
        print("="*70)
        config = client.create_config(
            sap_server="sapes5.sapdevcenter.com",
            sap_module="ES5",
            username="P2010682507",
            password="Bhuvan@2001"
        )
        print(f"✓ Config ID: {config['config_id']}")
        
        # Step 2: Create session
        print("\n" + "="*70)
        print("Step 2: Initialize Session")
        print("="*70)
        session = client.create_session()
        print(f"✓ Session ID: {session['session_id']}")
        print(f"  Total entities: {session['service_info']['total_entities']}")
        
        # List entities
        print("\n" + "="*70)
        print("List Entities")
        print("="*70)
        entities = client.list_entities()
        print(f"Total: {entities['total_entities']}")
        for entity in entities['entities'][:5]:
            print(f"  - {entity['name']}: {entity['properties']} properties")
        
        # Step 3: Query data
        print("\n" + "="*70)
        print("Step 3: Execute Query")
        print("="*70)
        result = client.query(
            entity_name="Products",
            filter_condition="Price gt 100",
            order_by="Price desc",
            record_limit=10
        )
        print(f"✓ Records: {result['execution_stats']['records_processed']}")
        print(f"  Duration: {result['execution_stats']['duration_seconds']:.2f}s")
        
        # Show sample data
        if result['data']['Products']['records']:
            print("\nSample records:")
            for record in result['data']['Products']['records'][:3]:
                data = record['data']
                print(f"  - {data.get('Name')}: ${data.get('Price')}")
        
    finally:
        # Cleanup
        print("\n" + "="*70)
        print("Cleanup")
        print("="*70)
        client.delete_session()
        print("✓ Session deleted")


if __name__ == "__main__":
    main()
