"""Count service for SAP OData connector"""

import asyncio
from typing import Dict, List, Optional
import httpx
import structlog
from urllib.parse import urlencode

from ..config.models import ODataConfig

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
            # Try $count=true parameter first (OData v4 standard)
            return await self._get_count_with_odata_count(entity_set)
        except Exception as e:
            logger.warning(
                "Failed to get count with $count=true, trying /$count endpoint",
                entity_set=entity_set,
                error=str(e)
            )
            
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
                try:
                    count = int(response.text.strip())
                    logger.debug("Retrieved count for entity", entity_set=entity_set, count=count)
                    return count
                except ValueError:
                    # Response is not a simple number, might be JSON
                    logger.warning("/$count returned non-numeric response, trying fallback")
                    raise ValueError("Non-numeric count response")
            elif response.status_code in [404, 415]:
                # $count not supported, fallback to other methods
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
    
    async def _get_count_with_odata_count(self, entity_set: str) -> int:
        """Get count using $count=true parameter (OData v4 standard)"""
        try:
            # Use $count=true with $top=1 for efficiency
            params = {
                '$count': 'true',
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
            
            # Extract count from @odata.count
            if '@odata.count' in data:
                count = int(data['@odata.count'])
                logger.debug("Retrieved count via @odata.count", entity_set=entity_set, count=count)
                return count
            else:
                raise ValueError("No @odata.count in response")
                
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.warning(
                "Failed to get count with $count=true",
                entity_set=entity_set,
                error=str(e)
            )
            raise
    
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
                    "Could not find count in response, using pagination count",
                    entity_set=entity_set
                )
                # Last resort: count via pagination
                return await self._get_count_via_pagination(entity_set)
            
            logger.debug("Retrieved count via inlinecount", entity_set=entity_set, count=count)
            return count
            
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.warning(
                "Failed to get count with inlinecount, trying pagination count",
                entity_set=entity_set,
                error=str(e)
            )
            return await self._get_count_via_pagination(entity_set)
    
    async def _get_count_via_pagination(self, entity_set: str) -> int:
        """Last resort: count records by paginating through all data"""
        try:
            logger.info("Counting records via pagination", entity_set=entity_set)
            
            total_count = 0
            skip = 0
            batch_size = 1000  # Use reasonable batch size
            
            auth = None
            if self.odata_config.username and self.odata_config.password:
                auth = (self.odata_config.username, self.odata_config.password)
            
            while True:
                params = {
                    '$skip': str(skip),
                    '$top': str(batch_size)
                }
                
                url = f"{self.odata_config.entity_set_url(entity_set)}?{urlencode(params)}"
                
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
                
                records_in_batch = len(results)
                total_count += records_in_batch
                
                logger.debug("Pagination count batch", 
                           entity_set=entity_set, 
                           skip=skip, 
                           records_in_batch=records_in_batch,
                           total_so_far=total_count)
                
                # If we got fewer records than requested, we've reached the end
                if records_in_batch < batch_size:
                    break
                
                skip += batch_size
                
                # Safety limit to prevent infinite loops
                if skip > 100000:
                    logger.warning("Pagination count reached safety limit", 
                                 entity_set=entity_set, 
                                 total_count=total_count)
                    break
            
            logger.info("Completed pagination count", 
                       entity_set=entity_set, 
                       total_count=total_count)
            return total_count
            
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.error(
                "Failed to count via pagination",
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
