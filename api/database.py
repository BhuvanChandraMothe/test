"""
Database models and operations for SAP OData Connector API

Uses SQLite for lightweight persistent storage.
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid


class Database:
    """SQLite database manager for API"""
    
    def __init__(self, db_path: str = "./api_data/connector.db"):
        self.db_path = db_path
        
        # Create directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table 1: Configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                config_id TEXT PRIMARY KEY,
                service_url TEXT,
                sap_server TEXT,
                sap_port INTEGER,
                sap_module TEXT,
                use_https BOOLEAN,
                username TEXT,
                password TEXT,
                output_directory TEXT,
                timeout INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Table 2: Sessions (initialized connectors)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                config_id TEXT,
                status TEXT,
                service_info TEXT,
                created_at TEXT,
                last_used_at TEXT,
                FOREIGN KEY (config_id) REFERENCES configurations (config_id)
            )
        """)
        
        # Table 3: Query Jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_jobs (
                job_id TEXT PRIMARY KEY,
                session_id TEXT,
                query_params TEXT,
                status TEXT,
                result_path TEXT,
                error TEXT,
                created_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ========================================================================
    # Configuration Operations
    # ========================================================================
    
    def create_config(
        self,
        service_url: Optional[str] = None,
        sap_server: Optional[str] = None,
        sap_port: int = 443,
        sap_module: Optional[str] = None,
        use_https: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        output_directory: str = "./api_output",
        timeout: int = 60
    ) -> str:
        """Create a new configuration and return config_id"""
        config_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO configurations (
                config_id, service_url, sap_server, sap_port, sap_module,
                use_https, username, password, output_directory, timeout,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config_id, service_url, sap_server, sap_port, sap_module,
            use_https, username, password, output_directory, timeout,
            now, now
        ))
        
        conn.commit()
        conn.close()
        
        return config_id
    
    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM configurations WHERE config_id = ?
        """, (config_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """List all configurations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM configurations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_config(self, config_id: str) -> bool:
        """Delete a configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM configurations WHERE config_id = ?", (config_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    # ========================================================================
    # Session Operations
    # ========================================================================
    
    def create_session(
        self,
        config_id: str,
        service_info: Dict[str, Any]
    ) -> str:
        """Create a new session (initialized connector)"""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (
                session_id, config_id, status, service_info,
                created_at, last_used_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id, config_id, "active", json.dumps(service_info),
            now, now
        ))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sessions WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            session = dict(row)
            session['service_info'] = json.loads(session['service_info'])
            return session
        return None
    
    def update_session_last_used(self, session_id: str):
        """Update session last_used_at timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions SET last_used_at = ? WHERE session_id = ?
        """, (datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def list_sessions(self, config_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by config_id"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if config_id:
            cursor.execute("""
                SELECT * FROM sessions WHERE config_id = ? ORDER BY created_at DESC
            """, (config_id,))
        else:
            cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            session = dict(row)
            session['service_info'] = json.loads(session['service_info'])
            sessions.append(session)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    # ========================================================================
    # Query Job Operations
    # ========================================================================
    
    def create_job(
        self,
        session_id: str,
        query_params: Dict[str, Any]
    ) -> str:
        """Create a new query job"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO query_jobs (
                job_id, session_id, query_params, status, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            job_id, session_id, json.dumps(query_params), "pending", now
        ))
        
        conn.commit()
        conn.close()
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM query_jobs WHERE job_id = ?
        """, (job_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            job = dict(row)
            job['query_params'] = json.loads(job['query_params'])
            return job
        return None
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        result_path: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update job status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status in ["completed", "failed"]:
            cursor.execute("""
                UPDATE query_jobs 
                SET status = ?, result_path = ?, error = ?, completed_at = ?
                WHERE job_id = ?
            """, (status, result_path, error, datetime.now().isoformat(), job_id))
        else:
            cursor.execute("""
                UPDATE query_jobs SET status = ? WHERE job_id = ?
            """, (status, job_id))
        
        conn.commit()
        conn.close()
    
    def list_jobs(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM query_jobs WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            job = dict(row)
            job['query_params'] = json.loads(job['query_params'])
            jobs.append(job)
        
        return jobs
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM query_jobs WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    # ========================================================================
    # Cleanup Operations
    # ========================================================================
    
    def cleanup_old_sessions(self, hours: int = 24):
        """Delete sessions older than specified hours"""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sessions WHERE last_used_at < ?
        """, (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM configurations")
        total_configs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM query_jobs")
        total_jobs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM query_jobs WHERE status = 'completed'")
        completed_jobs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM query_jobs WHERE status = 'running'")
        running_jobs = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_configs": total_configs,
            "total_sessions": total_sessions,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "running_jobs": running_jobs
        }
