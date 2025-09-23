"""Count service for SAP OData connector"""

import asyncio
from typing import Dict, List, Optional
import httpx
import structlog
from urllib.parse import urlencode

from config.models import ODataConfig

logger = structlog.get_logger(__name__)


class CountService:
    """Service to query entity set record counts from SAP OData"""
    
    def __init__(self, odata_config: ODataConfig):
        self.odata_config = odata_config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.odata_config.timeout,
            verify=self.odata_config.verify_ssl
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get_entity_counts(self, entity_sets: List[str]) -> Dict[str, int]:
        """Get record counts for all specified entity sets"""
        logger.info("Fetching entity counts", entity_count=len(entity_sets))
        
        # Create tasks for concurrent count queries
        tasks = []
        for entity_set in entity_sets:
            task = asyncio.create_task(
                self._get_single_entity_count(entity_set),
                name=f"count_{entity_set}"
            )
            tasks.append(task)
        
        # Execute all count queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        entity_counts = {}
        for entity_set, result in zip(entity_sets, results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to get count for entity",
                    entity_set=entity_set,
                    error=str(result)
                )
                entity_counts[entity_set] = 0  # Default to 0 on error
            else:
                entity_counts[entity_set] = result
        
        logger.info("Successfully retrieved entity counts", counts=entity_counts)
        return entity_counts
    
    async def _get_single_entity_count(self, entity_set: str) -> int:
        """Get record count for a single entity set"""
        try:
            # Use $count endpoint for efficient counting
            count_url = f"{self.odata_config.entity_set_url(entity_set)}/$count"
            
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            response = await self._client.get(
                count_url,
                auth=auth,
                headers={'Accept': 'text/plain'}
            )
            
            if response.status_code == 200:
                count = int(response.text.strip())
                logger.debug("Retrieved count for entity", entity_set=entity_set, count=count)
                return count
            elif response.status_code == 404:
                # $count not supported, fallback to $inlinecount
                return await self._get_count_with_inlinecount(entity_set)
            else:
                response.raise_for_status()
                
        except (httpx.HTTPError, ValueError) as e:
            logger.warning(
                "Failed to get count, trying fallback method",
                entity_set=entity_set,
                error=str(e)
            )
            return await self._get_count_with_inlinecount(entity_set)
    
    async def _get_count_with_inlinecount(self, entity_set: str) -> int:
        """Fallback method using $inlinecount for older SAP systems"""
        try:
            # Use $inlinecount=allpages with $top=1 for efficiency
            params = {
                '$inlinecount': 'allpages',
                '$top': '1'
            }
            
            url = f"{self.odata_config.entity_set_url(entity_set)}?{urlencode(params)}"
            
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            response = await self._client.get(
                url,
                auth=auth,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract count from response
            if 'd' in data and '__count' in data['d']:
                count = int(data['d']['__count'])
            elif '__count' in data:
                count = int(data['__count'])
            else:
                logger.warning(
                    "Could not find count in response, estimating from results",
                    entity_set=entity_set
                )
                # Last resort: estimate based on results array
                results = data.get('d', {}).get('results', data.get('value', []))
                count = len(results) if isinstance(results, list) else 0
            
            logger.debug("Retrieved count via inlinecount", entity_set=entity_set, count=count)
            return count
            
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.error(
                "Failed to get count with fallback method",
                entity_set=entity_set,
                error=str(e)
            )
            return 0
    
    async def get_entity_sample(self, entity_set: str, sample_size: int = 5) -> List[Dict]:
        """Get a sample of records from an entity set for schema validation"""
        try:
            params = {'$top': str(sample_size)}
            url = f"{self.odata_config.entity_set_url(entity_set)}?{urlencode(params)}"
            
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            response = await self._client.get(
                url,
                auth=auth,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract results from OData response
            if 'd' in data and 'results' in data['d']:
                results = data['d']['results']
            elif 'value' in data:
                results = data['value']
            else:
                results = []
            
            logger.debug(
                "Retrieved sample records",
                entity_set=entity_set,
                sample_count=len(results)
            )
            return results
            
        except (httpx.HTTPError, ValueError) as e:
            logger.error(
                "Failed to get sample records",
                entity_set=entity_set,
                error=str(e)
            )
            return []
