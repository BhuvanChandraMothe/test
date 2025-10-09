"""
Start SAP OData Connector API

Run this to start the API server with SQLite persistence.
"""
import uvicorn

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SAP OData Connector API v2.0")
    print("="*70)
    print("\nArchitecture:")
    print("  1. POST /api/v1/configs → config_id (stored in SQLite)")
    print("  2. POST /api/v1/sessions → session_id (initialized connector)")
    print("  3. POST /api/v1/query → job_id (background job)")
    print("  4. GET /api/v1/jobs/{job_id} → results")
    print("\nAPI will be available at:")
    print("  • Main: http://localhost:8000")
    print("  • Docs: http://localhost:8000/docs")
    print("  • Health: http://localhost:8000/health")
    print("\nDatabase: ./api_data/connector.db")
    print("\nPress CTRL+C to stop")
    print("="*70 + "\n")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
