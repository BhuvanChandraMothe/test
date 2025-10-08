# OData Version Support

## Summary

| OData Version | Support Level | Status | Notes |
|---------------|---------------|--------|-------|
| **OData V2** | ✅ **Full Support** | **Primary** | Designed for SAP services |
| **OData V4** | ⚠️ **Partial Support** | **Limited** | Basic functionality, some limitations |

---

## Detailed Support Matrix

### ✅ OData V2 - Full Support

#### What Works
- ✅ **SAP Services** (Primary target)
  - EPM services
  - Custom SAP OData services
  - SAP Gateway services
- ✅ **Metadata parsing** (EDMX V2 format)
- ✅ **Data fetching** with pagination
- ✅ **Query options**: $filter, $select, $expand, $orderby, $top, $skip
- ✅ **Response format**: `{ "d": { "results": [...] } }`
- ✅ **Count**: `__count` field
- ✅ **Pagination**: `__next` links
- ✅ **Authentication**: Basic, OAuth
- ✅ **Batch processing**
- ✅ **Parallel workers**

#### Tested Services
```python
# ✅ WORKING - SAP EPM Service
service_url="https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/"
# Result: 1,942 records from 9 entities

# ⚠️ ISSUES - Northwind V2
service_url="https://services.odata.org/V2/Northwind/Northwind.svc/"
# Result: Metadata parsing issues, 0 records
```

---

### ⚠️ OData V4 - Partial Support

#### What Works (Limited)
- ⚠️ **Basic data fetching** (with limitations)
- ⚠️ **Metadata parsing** (V4 EDMX format)
- ⚠️ **Response format**: `{ "value": [...] }`
- ⚠️ **Count**: `@odata.count` field
- ⚠️ **Pagination**: `@odata.nextLink`

#### Known Limitations
- ❌ **Incomplete pagination** - May not fetch all records
- ❌ **Record limits** - Some entities return fewer records than available
- ❌ **Metadata issues** - Some V4 services don't parse correctly
- ❌ **Query options** - Limited V4-specific features
- ❌ **Not fully tested** - Primary focus is V2

#### Tested Services
```python
# ⚠️ PARTIAL - Northwind V4
service_url="https://services.odata.org/V4/Northwind/Northwind.svc/"
# Expected: ~10,000 records
# Actual: 3,916 records (incomplete)
# Issues: 
#   - Orders: 200/830 (24%)
#   - Products: 20/77 (26%)
#   - Pagination stops early
```

---

## Code Evidence

### V2 Support (Primary)
```python
# From connector.py
if 'd' in data:
    # OData V2 format
    page_records = data['d'].get('results', [])
    if total_count is None and '__count' in data['d']:
        total_count = data['d']['__count']
```

### V4 Support (Secondary)
```python
# From connector.py
else:
    # OData V4 format
    page_records = data.get('value', [])
    if total_count is None and '@odata.count' in data:
        total_count = data['@odata.count']
```

### Metadata Parsing
```python
# From services/metadata.py
# Try different namespace versions (V2 and V4)
namespaces_v4 = {
    'edmx': 'http://docs.oasis-open.org/odata/ns/edmx',
    'edm': 'http://docs.oasis-open.org/odata/ns/edm'
}

namespaces_v2 = {
    'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
    'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'
}

# Auto-detect version
if root.findall('.//edm:EntitySet', namespaces_v2):
    namespaces = namespaces_v2
    logger.info("Using OData V2 namespaces for metadata parsing")
else:
    logger.info("Using OData V4 namespaces for metadata parsing")
```

---

## Test Results

### Test 1: OData V2 - SAP EPM ✅
```
Service: https://sapes5.sapdevcenter.com/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV/
Metadata: 9 entities loaded
Records: 1,942 fetched successfully
Status: ✅ WORKING
```

### Test 2: OData V2 - Northwind ❌
```
Service: https://services.odata.org/V2/Northwind/Northwind.svc/
Metadata: 0 entities loaded
Records: 0 fetched
Status: ❌ METADATA PARSING FAILED
Issue: Non-SAP V2 metadata format not fully supported
```

### Test 3: OData V4 - Northwind ⚠️
```
Service: https://services.odata.org/V4/Northwind/Northwind.svc/
Metadata: 26 entities loaded
Records: 3,916 fetched (expected ~10,000)
Status: ⚠️ PARTIAL SUPPORT
Issues:
  - Incomplete pagination
  - Some entities limited to 20-200 records
  - Not all records fetched
```

---

## Recommendations

### ✅ Recommended: Use OData V2 SAP Services

```python
# Best compatibility
config = ClientConfig(
    service_url="https://your-sap-server.com/sap/opu/odata/sap/YOUR_SERVICE/",
    username="your_username",
    password="your_password"
)
```

**Why?**
- ✅ Fully tested and supported
- ✅ All features work correctly
- ✅ Complete pagination
- ✅ Reliable metadata parsing
- ✅ Designed specifically for SAP

### ⚠️ Use with Caution: OData V4 Services

```python
# May have limitations
config = ClientConfig(
    service_url="https://your-v4-service.com/odata/"
)
```

**Limitations:**
- ⚠️ May not fetch all records
- ⚠️ Pagination might stop early
- ⚠️ Some query options may not work
- ⚠️ Test thoroughly before production use

### ❌ Not Recommended: Non-SAP OData V2

```python
# May have metadata parsing issues
config = ClientConfig(
    service_url="https://non-sap-v2-service.com/odata/"
)
```

**Issues:**
- ❌ Metadata format differences
- ❌ May not load entities
- ❌ Not the primary use case

---

## Feature Comparison

| Feature | V2 (SAP) | V2 (Non-SAP) | V4 |
|---------|----------|--------------|-----|
| Metadata Parsing | ✅ Full | ❌ Limited | ⚠️ Partial |
| Data Fetching | ✅ Full | ❌ Issues | ⚠️ Partial |
| Pagination | ✅ Complete | ❌ Issues | ⚠️ Incomplete |
| $filter | ✅ Yes | ❓ Untested | ⚠️ Basic |
| $select | ✅ Yes | ❓ Untested | ⚠️ Basic |
| $expand | ✅ Yes | ❓ Untested | ⚠️ Basic |
| $orderby | ✅ Yes | ❓ Untested | ⚠️ Basic |
| Authentication | ✅ Full | ❓ Untested | ⚠️ Basic |
| Batch Processing | ✅ Yes | ❓ Untested | ⚠️ Limited |
| Record Count | ✅ Accurate | ❌ Issues | ⚠️ Inaccurate |

---

## Why V4 Support is Limited

### Design Focus
The connector was **designed primarily for SAP OData V2 services**:
- SAP Gateway services
- SAP Business Suite
- SAP S/4HANA
- SAP Cloud Platform

### V4 Differences
OData V4 has significant changes:
1. **Different metadata format** (CSDL vs EDMX)
2. **Different response structure** (`value` vs `d.results`)
3. **Different pagination** (`@odata.nextLink` vs `__next`)
4. **Different count** (`@odata.count` vs `__count`)
5. **New query options** (not all implemented)

### Current V4 Implementation
The V4 support is **basic compatibility layer**:
- Handles response format differences
- Parses V4 metadata (partially)
- Supports basic queries
- **Not fully tested or optimized**

---

## Future Enhancements

To fully support OData V4, the following would be needed:

### High Priority
- [ ] Fix pagination logic for V4
- [ ] Improve V4 metadata parsing
- [ ] Handle V4-specific response formats
- [ ] Test with more V4 services
- [ ] Fix record count detection

### Medium Priority
- [ ] Support V4 query options ($apply, $compute, etc.)
- [ ] Handle V4 error responses
- [ ] Support V4 batch requests
- [ ] Implement V4 delta queries

### Low Priority
- [ ] Support V4 actions and functions
- [ ] Handle V4 annotations
- [ ] Support V4 containment
- [ ] Implement V4 async requests

---

## Workarounds for V4

If you must use a V4 service:

### 1. Use Single Entity Queries
```python
# Instead of fetching all entities
result = await connector.get_data()

# Fetch one entity at a time
result = await connector.get_data(entity_name="Products")
```

### 2. Use Record Limits
```python
# Limit records to avoid pagination issues
result = await connector.get_data(
    entity_name="Products",
    record_limit=100
)
```

### 3. Test Thoroughly
```python
# Always verify record counts
expected_count = 830  # From service metadata
actual_count = result['execution_stats']['records_processed']

if actual_count < expected_count:
    print(f"Warning: Only got {actual_count}/{expected_count} records")
```

---

## Conclusion

### ✅ **Primary Use Case: OData V2 SAP Services**
The connector is **production-ready** for:
- SAP OData V2 services
- SAP Gateway
- SAP Business Suite
- Custom SAP services

### ⚠️ **Secondary Use Case: OData V4 Services**
The connector has **basic V4 support** but:
- Not fully tested
- May have limitations
- Use with caution
- Test thoroughly

### ❌ **Not Supported: Non-SAP OData V2**
Non-SAP V2 services may have:
- Metadata parsing issues
- Different conventions
- Compatibility problems

---

## Recommendation

**For Production Use:**
```python
# ✅ Use SAP OData V2 services
service_url = "https://your-sap-server.com/sap/opu/odata/sap/SERVICE/"
```

**For Development/Testing:**
```python
# ⚠️ V4 services - test thoroughly
service_url = "https://your-v4-service.com/odata/"
# Set record_limit and verify results
```

---

**Package**: `covasant_sap_odata_connector` | **Version**: 1.0.1  
**Primary Support**: OData V2 (SAP Services)  
**Secondary Support**: OData V4 (Basic/Limited)
