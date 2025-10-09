# 🛡️ OData Version Validation Feature

## Overview

The connector now includes **proactive validation** that detects the OData version and warns/errors when you try to use unsupported features.

---

## ✨ What It Does

### For OData V2 Services (like SAP EPM)

**❌ ERRORS** when you try to use:
- `group_by`
- `aggregate_functions`

**Example Error:**
```
======================================================================
❌ UNSUPPORTED FEATURE DETECTED
======================================================================
Feature: group_by
Value: HasReviewOfCurrentUser
OData Version: V2

The '$apply' system query option (required for grouping and
aggregation) is NOT supported in OData V2 services.

This feature requires OData V4 with the Data Aggregation Extension.

Solutions:
  1. Fetch data and group in Python (recommended)
  2. Use a V4 service with aggregation support
  3. Create a CDS view with pre-aggregated data in SAP

Example - Group in Python:
  result = await connector.get_data(entity_name='Products')
  records = [r.data for r in result['data']['Products']['records']]
  from collections import Counter
  grouped = Counter(r.get('Category') for r in records)
======================================================================
```

### For OData V4 Services

**⚠️ WARNS** that not all V4 services support `$apply`:

```
======================================================================
⚠️  WARNING: Using V4-only feature
======================================================================
Feature: group_by
OData Version: V4

Note: Not all OData V4 services support the $apply system query option.
The Data Aggregation Extension is OPTIONAL in OData V4.

If this query fails with a 400 error mentioning '$apply', the service
does not support aggregation. In that case, fetch data and group in Python.
======================================================================
```

---

## 🔧 Implementation

### The Validation Method

Added to `connector.py` at line 903:

```python
def _validate_query_options(self, query_options: Dict[str, Any]):
    """
    Validate query options against OData version capabilities
    
    Raises warnings/errors for unsupported features based on OData version.
    """
    # Check if we have metadata service initialized
    if not hasattr(self, 'metadata_service') or not self.metadata_service:
        logger.warning("Metadata service not initialized - skipping query validation")
        return
    
    # Get OData version
    odata_version = getattr(self.metadata_service, 'odata_version', 'Unknown')
    
    # Check for V4-only features
    group_by = query_options.get('group_by')
    aggregate_functions = query_options.get('aggregate_functions')
    
    if group_by or aggregate_functions:
        if odata_version == 'V2':
            # ERROR - not supported
            raise ValueError(...)
        elif odata_version == 'V4':
            # WARNING - may not be supported
            logger.warning(...)
```

### How to Enable

Run the PowerShell script to add the validation call:

```powershell
.\add_validation.ps1
```

This adds the validation call in `get_data()` method before query execution.

---

## 🧪 Testing

### Test the Validation

```bash
python test_validation.py
```

This runs 3 tests:
1. **V2 + group_by** → Should error ❌
2. **V2 + normal query** → Should work ✅
3. **V4 + group_by** → Should warn ⚠️

---

## 📊 Behavior Matrix

| OData Version | Feature | Behavior |
|---------------|---------|----------|
| V2 | `group_by` | ❌ **ERROR** - Stops execution |
| V2 | `aggregate_functions` | ❌ **ERROR** - Stops execution |
| V2 | `filter`, `order_by`, `select` | ✅ Works |
| V4 | `group_by` | ⚠️ **WARNING** - Continues (may fail) |
| V4 | `aggregate_functions` | ⚠️ **WARNING** - Continues (may fail) |
| V4 | All other features | ✅ Works |

---

## 💡 Benefits

### 1. **Early Detection**
Catches unsupported features BEFORE making API calls.

### 2. **Clear Error Messages**
Provides detailed explanations and solutions.

### 3. **Helpful Guidance**
Shows Python alternatives for grouping/aggregation.

### 4. **Prevents Confusion**
Users know immediately why something won't work.

---

## 🎯 Example Usage

### Before Validation (Confusing Error)

```python
result = await connector.get_data(
    entity_name="Products",
    group_by="Category"
)
# Error: Client error '400 Bad Request'
# User confused: "Why doesn't this work?"
```

### After Validation (Clear Error)

```python
result = await connector.get_data(
    entity_name="Products",
    group_by="Category"
)
# ❌ UNSUPPORTED FEATURE DETECTED
# Feature: group_by
# OData Version: V2
# 
# The '$apply' system query option is NOT supported in OData V2.
# 
# Solutions:
#   1. Fetch data and group in Python (recommended)
#   ...
```

---

## 🔄 Alternative: Group in Python

The validation error message includes this example:

```python
# Fetch data
result = await connector.get_data(entity_name='Products')
records = [r.data for r in result['data']['Products']['records']]

# Group in Python
from collections import Counter
grouped = Counter(r.get('Category') for r in records)

# Or use pandas
import pandas as pd
df = pd.DataFrame(records)
grouped = df.groupby('Category').size()
```

---

## 📝 Summary

✅ **Validation method created** (`_validate_query_options`)  
✅ **Test file created** (`test_validation.py`)  
✅ **PowerShell script created** (`add_validation.ps1`)  
⏳ **Need to run**: `.\add_validation.ps1` to enable validation  

---

## 🚀 Next Steps

1. **Enable validation**:
   ```powershell
   .\add_validation.ps1
   ```

2. **Test it**:
   ```bash
   python test_validation.py
   ```

3. **Try it yourself**:
   ```python
   # This will now show a helpful error
   result = await connector.get_data(
       entity_name="Products",
       group_by="Category"
   )
   ```

---

**Your connector now provides helpful validation for unsupported features! 🎉**
