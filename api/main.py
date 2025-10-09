"""
FastAPI REST API for SAP OData Connector

Architecture:
1. POST /configs → Get config_id (stored in DB)
2. POST /sessions → Initialize connector with config_id → Get session_id
3. POST /query → Execute query with session_id → Get job_id
4. GET /jobs/{job_id} → Check status and get results

Run with: uvicorn api.main:app --reload
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from .database import Database
from covasant_odata.connector import SAPODataConnector
from covasant_odata.config.models import ClientConfig

# Initialize FastAPI app
app = FastAPI(
    title="SAP OData Connector API",
    description="REST API with persistent storage for SAP OData data extraction",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize database
db = Database()

# Store active connector instances (in-memory for performance)
active_connectors: Dict[str, SAPODataConnector] = {}


# ============================================================================
# Pydantic Models
# ============================================================================

class ConfigCreate(BaseModel):
    """Model for creating a configuration"""
    service_url: Optional[str] = Field(None, description="Full OData service URL")
    sap_server: Optional[str] = Field(None, description="SAP server hostname")
    sap_port: int = Field(443, description="SAP server port")
    sap_module: Optional[str] = Field(None, description="SAP module (e.g., ES5)")
    use_https: bool = Field(True, description="Use HTTPS")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    output_directory: str = Field("./api_output", description="Output directory")
    timeout: int = Field(60, description="Timeout in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sap_server": "sapes5.sapdevcenter.com",
                "sap_port": 443,
                "sap_module": "ES5",
                "username": "P2010682507",
                "password": "Bhuvan@2001"
            }
        }


class SessionCreate(BaseModel):
    """Model for creating a session"""
    config_id: str = Field(..., description="Configuration ID to use")


class QueryRequest(BaseModel):
    """Model for query request"""
    session_id: str = Field(..., description="Session ID to use")
    entity_name: Optional[str] = Field(None, description="Single entity")
    selected_entities: Optional[List[str]] = Field(None, description="Multiple entities")
    filter_condition: Optional[str] = Field(None, description="$filter condition")
    select_fields: Optional[str] = Field(None, description="$select fields")
    expand_relations: Optional[str] = Field(None, description="$expand relations")
    order_by: Optional[str] = Field(None, description="$orderby clause")
    record_limit: Optional[int] = Field(None, description="Max records")
    batch_size: int = Field(1000, description="Batch size")
    max_workers: int = Field(5, description="Max workers")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API information"""
    stats = db.get_stats()
    return {
        "name": "SAP OData Connector API",
        "version": "2.0.0",
        "status": "running",
        "stats": stats,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "configs": "/api/v1/configs",
            "sessions": "/api/v1/sessions",
            "query": "/api/v1/query",
            "jobs": "/api/v1/jobs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check"""
    stats = db.get_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": stats,
        "active_connectors": len(active_connectors)
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@app.post("/api/v1/configs")
async def create_config(config: ConfigCreate):
    """
    Step 1: Create a configuration
    
    Returns a config_id that can be used to initialize sessions.
    """
    try:
        config_id = db.create_config(
            service_url=config.service_url,
            sap_server=config.sap_server,
            sap_port=config.sap_port,
            sap_module=config.sap_module,
            use_https=config.use_https,
            username=config.username,
            password=config.password,
            output_directory=config.output_directory,
            timeout=config.timeout
        )
        
        return {
            "config_id": config_id,
            "status": "created",
            "message": "Configuration saved successfully",
            "next_step": f"POST /api/v1/sessions with config_id={config_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create config: {str(e)}")


@app.get("/api/v1/configs")
async def list_configs():
    """List all configurations"""
    configs = db.list_configs()
    
    # Remove sensitive data
    for config in configs:
        config.pop('password', None)
    
    return {
        "total": len(configs),
        "configs": configs
    }


@app.get("/api/v1/configs/{config_id}")
async def get_config(config_id: str):
    """Get a specific configuration"""
    config = db.get_config(config_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Remove sensitive data
    config.pop('password', None)
    
    return config


@app.delete("/api/v1/configs/{config_id}")
async def delete_config(config_id: str):
    """Delete a configuration"""
    deleted = db.delete_config(config_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {
        "config_id": config_id,
        "status": "deleted",
        "message": "Configuration deleted successfully"
    }


# ============================================================================
# Session Endpoints
# ============================================================================

@app.post("/api/v1/sessions")
async def create_session(session_req: SessionCreate):
    """
    Step 2: Initialize a connector session
    
    Uses a config_id to initialize the connector and returns a session_id.
    """
    # Get configuration
    config = db.get_config(session_req.config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    try:
        # Create ClientConfig
        client_config = ClientConfig(
            service_url=config['service_url'],
            sap_server=config['sap_server'],
            sap_port=config['sap_port'],
            sap_module=config['sap_module'],
            use_https=bool(config['use_https']),
            username=config['username'],
            password=config['password'],
            output_directory=f"{config['output_directory']}/{session_req.config_id}",
            timeout=config['timeout']
        )
        
        # Initialize connector
        connector = SAPODataConnector(client_config)
        service_info = await connector.initialize()
        
        # Create session in database
        session_id = db.create_session(session_req.config_id, service_info)
        
        # Store connector in memory
        active_connectors[session_id] = connector
        
        return {
            "session_id": session_id,
            "config_id": session_req.config_id,
            "status": "initialized",
            "message": "Connector initialized successfully",
            "service_info": service_info,
            "next_step": f"POST /api/v1/query with session_id={session_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")


@app.get("/api/v1/sessions")
async def list_sessions(config_id: Optional[str] = None):
    """List all sessions"""
    sessions = db.list_sessions(config_id=config_id)
    
    return {
        "total": len(sessions),
        "sessions": sessions
    }


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session"""
    session = db.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@app.get("/api/v1/sessions/{session_id}/entities")
async def list_session_entities(session_id: str):
    """List entities available in a session"""
    # Check if session exists
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get connector
    if session_id not in active_connectors:
        raise HTTPException(status_code=400, detail="Session not active. Please reinitialize.")
    
    connector = active_connectors[session_id]
    
    # Update last used
    db.update_session_last_used(session_id)
    
    # Get entities
    entities = []
    for entity_name, schema in connector.metadata_service.schemas.items():
        entities.append({
            "name": entity_name,
            "properties": len(schema.properties),
            "keys": schema.keys,
            "navigation_properties": len(schema.navigation_properties)
        })
    
    return {
        "session_id": session_id,
        "total_entities": len(entities),
        "entities": entities
    }


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    # Cleanup connector if active
    if session_id in active_connectors:
        try:
            await active_connectors[session_id].cleanup()
        except:
            pass
        del active_connectors[session_id]
    
    # Delete from database
    deleted = db.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "status": "deleted",
        "message": "Session deleted successfully"
    }


# ============================================================================
# Query Endpoints
# ============================================================================

@app.post("/api/v1/query")
async def execute_query(query: QueryRequest, background_tasks: BackgroundTasks):
    """
    Step 3: Execute a query
    
    Uses a session_id to execute a query and returns a job_id.
    """
    # Check if session exists
    session = db.get_session(query.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if connector is active
    if query.session_id not in active_connectors:
        raise HTTPException(
            status_code=400,
            detail="Session not active. Please create a new session with POST /api/v1/sessions"
        )
    
    try:
        # Create job in database
        job_id = db.create_job(
            session_id=query.session_id,
            query_params=query.dict(exclude={'session_id'})
        )
        
        # Update session last used
        db.update_session_last_used(query.session_id)
        
        # Start background task
        background_tasks.add_task(
            execute_query_task,
            job_id,
            query.session_id,
            query
        )
        
        return {
            "job_id": job_id,
            "session_id": query.session_id,
            "status": "pending",
            "message": "Query job created successfully",
            "next_step": f"GET /api/v1/jobs/{job_id} to check status"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create query job: {str(e)}")


# ============================================================================
# Job Endpoints
# ============================================================================

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    job = db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        "job_id": job_id,
        "session_id": job['session_id'],
        "status": job['status'],
        "query_params": job['query_params'],
        "created_at": job['created_at']
    }
    
    if job['status'] == 'completed':
        response['completed_at'] = job['completed_at']
        response['result_path'] = job['result_path']
        response['download_url'] = f"/api/v1/jobs/{job_id}/download"
    elif job['status'] == 'failed':
        response['error'] = job['error']
        response['completed_at'] = job['completed_at']
    
    return response


@app.get("/api/v1/jobs/{job_id}/download")
async def download_job_results(job_id: str):
    """Download job results"""
    job = db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job['status']}, not completed"
        )
    
    # Load results from file
    import json
    try:
        with open(job['result_path'], 'r') as f:
            results = json.load(f)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load results: {str(e)}")


@app.get("/api/v1/jobs")
async def list_jobs(
    session_id: Optional[str] = None,
    status: Optional[str] = None
):
    """List all jobs"""
    jobs = db.list_jobs(session_id=session_id, status=status)
    
    return {
        "total": len(jobs),
        "jobs": jobs
    }


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job"""
    deleted = db.delete_job(job_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": "deleted",
        "message": "Job deleted successfully"
    }


# ============================================================================
# Background Task
# ============================================================================

async def execute_query_task(job_id: str, session_id: str, query: QueryRequest):
    """Background task to execute query"""
    try:
        # Update status to running
        db.update_job_status(job_id, "running")
        
        # Get connector
        connector = active_connectors[session_id]
        
        # Execute query
        result = await connector.get_data(
            entity_name=query.entity_name,
            selected_entities=query.selected_entities,
            filter_condition=query.filter_condition,
            select_fields=query.select_fields,
            expand_relations=query.expand_relations,
            order_by=query.order_by,
            record_limit=query.record_limit,
            batch_size=query.batch_size,
            max_workers=query.max_workers
        )
        
        # Save results to file
        import json
        from pathlib import Path
        
        result_dir = Path(f"./api_data/results/{session_id}")
        result_dir.mkdir(parents=True, exist_ok=True)
        
        result_path = result_dir / f"{job_id}.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Update job status
        db.update_job_status(job_id, "completed", result_path=str(result_path))
        
    except Exception as e:
        db.update_job_status(job_id, "failed", error=str(e))


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    print("=" * 70)
    print("SAP OData Connector API v2.0 Starting...")
    print("=" * 70)
    print("Architecture:")
    print("  1. POST /api/v1/configs → config_id")
    print("  2. POST /api/v1/sessions → session_id")
    print("  3. POST /api/v1/query → job_id")
    print("  4. GET /api/v1/jobs/{job_id} → results")
    print("=" * 70)
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\nShutting down...")
    
    for session_id, connector in active_connectors.items():
        try:
            await connector.cleanup()
        except:
            pass
    
    active_connectors.clear()
    print("Shutdown complete.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
