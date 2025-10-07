"""
SAP Module to OData Service Name Mapping

This module provides mapping between SAP module names and their corresponding OData service names.
It supports various SAP modules including FI, CO, MM, SD, HR, ARIBA, CONCUR, and more.
"""

from typing import Dict, Optional, List
from enum import Enum


class SAPModuleCategory(str, Enum):
    """SAP Module Categories"""
    FINANCE = "finance"
    LOGISTICS = "logistics"
    HR = "hr"
    PROCUREMENT = "procurement"
    SALES = "sales"
    MANUFACTURING = "manufacturing"
    CLOUD = "cloud"
    DEMO = "demo"


class SAPModuleMapping:
    """
    SAP Module to OData Service Mapping
    
    Maps SAP module names to their corresponding OData service names.
    Supports both standard SAP modules and custom services.
    """
    
    # Standard SAP Module Mappings
    MODULE_TO_SERVICE: Dict[str, str] = {
        # Finance Modules
        "FI": "FINS_GENERALLEDGER_SRV",
        "FI-GL": "FINS_GENERALLEDGER_SRV",
        "FI-AP": "FINS_ACCOUNTSPAYABLE_SRV",
        "FI-AR": "FINS_ACCOUNTSRECEIVABLE_SRV",
        "FI-AA": "FINS_FIXEDASSETS_SRV",
        "FI-BL": "FINS_BANKLEDGER_SRV",
        "FI-CA": "FINS_CONTRACTACCOUNTS_SRV",
        
        # Controlling
        "CO": "FINS_CONTROLLING_SRV",
        "CO-PA": "FINS_PROFITABILITY_SRV",
        "CO-PC": "FINS_PRODUCTCOSTING_SRV",
        "CO-OM": "FINS_OVERHEADMGMT_SRV",
        
        # Materials Management
        "MM": "MM_PUR_PO_MAINT_V2_SRV",
        "MM-PUR": "MM_PUR_PO_MAINT_V2_SRV",
        "MM-IM": "MM_IM_STOCK_SRV",
        "MM-WM": "MM_WM_WAREHOUSE_SRV",
        "MM-IV": "MM_IV_INVENTORY_SRV",
        
        # Sales & Distribution
        "SD": "SD_F1814_SO_SALESORDER_SRV",
        "SD-SO": "SD_F1814_SO_SALESORDER_SRV",
        "SD-BIL": "SD_BILLING_SRV",
        "SD-SHP": "SD_SHIPPING_SRV",
        "SD-CAS": "SD_CUSTOMER_SRV",
        
        # Production Planning
        "PP": "PP_PRODUCTION_ORDER_SRV",
        "PP-PI": "PP_PROCESS_ORDER_SRV",
        "PP-MP": "PP_MRP_SRV",
        
        # Quality Management
        "QM": "QM_INSPECTION_SRV",
        
        # Plant Maintenance
        "PM": "PM_MAINTENANCE_ORDER_SRV",
        
        # Human Resources
        "HR": "HCM_EMPLOYEE_SRV",
        "HR-PA": "HCM_PERSONNEL_SRV",
        "HR-PY": "HCM_PAYROLL_SRV",
        "HR-TM": "HCM_TIME_SRV",
        "HR-OM": "HCM_ORG_SRV",
        
        # Project Systems
        "PS": "PS_PROJECT_SRV",
        
        # Customer Relationship Management
        "CRM": "CRM_OPPORTUNITY_SRV",
        
        # Supplier Relationship Management
        "SRM": "SRM_SUPPLIER_SRV",
        
        # Supply Chain Management
        "SCM": "SCM_PLANNING_SRV",
        "APO": "APO_PLANNING_SRV",
        
        # Ariba (Cloud Procurement)
        "ARIBA": "ARIBA_PROCUREMENT_SRV",
        "ARIBA-BUYER": "ARIBA_BUYER_SRV",
        "ARIBA-SUPPLIER": "ARIBA_SUPPLIER_SRV",
        "ARIBA-CONTRACT": "ARIBA_CONTRACT_SRV",
        "ARIBA-SOURCING": "ARIBA_SOURCING_SRV",
        
        # Concur (Travel & Expense)
        "CONCUR": "CONCUR_EXPENSE_SRV",
        "CONCUR-TRAVEL": "CONCUR_TRAVEL_SRV",
        "CONCUR-EXPENSE": "CONCUR_EXPENSE_SRV",
        "CONCUR-INVOICE": "CONCUR_INVOICE_SRV",
        
        # SuccessFactors (Cloud HR)
        "SF": "SUCCESSFACTORS_EMPLOYEE_SRV",
        "SUCCESSFACTORS": "SUCCESSFACTORS_EMPLOYEE_SRV",
        "SF-EC": "SUCCESSFACTORS_EMPCENTRAL_SRV",
        "SF-ONB": "SUCCESSFACTORS_ONBOARDING_SRV",
        "SF-REC": "SUCCESSFACTORS_RECRUITING_SRV",
        "SF-LMS": "SUCCESSFACTORS_LEARNING_SRV",
        
        # S/4HANA Specific
        "S4-FI": "API_FINANCIALSTATEMENT_SRV",
        "S4-MM": "API_MATERIAL_STOCK_SRV",
        "S4-SD": "API_SALES_ORDER_SRV",
        "S4-PP": "API_PRODUCTION_ORDER_SRV",
        
        # Business Warehouse
        "BW": "BW_QUERY_SRV",
        "BW-IP": "BW_PLANNING_SRV",
        
        # Master Data Governance
        "MDG": "MDG_MATERIAL_SRV",
        "MDG-M": "MDG_MATERIAL_SRV",
        "MDG-C": "MDG_CUSTOMER_SRV",
        "MDG-S": "MDG_SUPPLIER_SRV",
        
        # Gateway Demo Services (for testing)
        "DEMO": "ZGWSAMPLE_BASIC",
        "GWSAMPLE": "ZGWSAMPLE_BASIC",
        "NORTHWIND": "NORTHWIND_SRV",
        
        # ES5 Demo System Services
        "ES5": "EPM_REF_APPS_SHOP_SRV",
        "EPM": "EPM_REF_APPS_SHOP_SRV",
        "EPM-SHOP": "EPM_REF_APPS_SHOP_SRV",
        "EPM-PO": "EPM_REF_APPS_PO_APV_SRV",
        "EPM-PROD": "EPM_REF_APPS_PROD_MAN_SRV",
        
        # Common Gateway Services
        "GATEWAY": "ZGWSAMPLE_BASIC",
        "GW-SAMPLE": "ZGWSAMPLE_BASIC",
        
        # Business Partner
        "BP": "API_BUSINESS_PARTNER",
        "BUSINESS-PARTNER": "API_BUSINESS_PARTNER",
    }
    
    # Service Category Mapping
    SERVICE_CATEGORIES: Dict[str, SAPModuleCategory] = {
        "FINS_GENERALLEDGER_SRV": SAPModuleCategory.FINANCE,
        "FINS_ACCOUNTSPAYABLE_SRV": SAPModuleCategory.FINANCE,
        "FINS_ACCOUNTSRECEIVABLE_SRV": SAPModuleCategory.FINANCE,
        "MM_PUR_PO_MAINT_V2_SRV": SAPModuleCategory.LOGISTICS,
        "SD_F1814_SO_SALESORDER_SRV": SAPModuleCategory.SALES,
        "HCM_EMPLOYEE_SRV": SAPModuleCategory.HR,
        "ARIBA_PROCUREMENT_SRV": SAPModuleCategory.PROCUREMENT,
        "CONCUR_EXPENSE_SRV": SAPModuleCategory.CLOUD,
        "EPM_REF_APPS_SHOP_SRV": SAPModuleCategory.DEMO,
    }
    
    @classmethod
    def get_service_name(cls, module_name: str) -> Optional[str]:
        """
        Get OData service name for a given SAP module name.
        
        Args:
            module_name: SAP module name (e.g., 'FI', 'MM', 'ARIBA', 'ES5')
            
        Returns:
            OData service name or None if not found
        """
        # Normalize module name (uppercase, strip whitespace)
        normalized_module = module_name.upper().strip()
        
        return cls.MODULE_TO_SERVICE.get(normalized_module)
    
    @classmethod
    def get_category(cls, service_name: str) -> Optional[SAPModuleCategory]:
        """
        Get category for a given service name.
        
        Args:
            service_name: OData service name
            
        Returns:
            Service category or None if not found
        """
        return cls.SERVICE_CATEGORIES.get(service_name)
    
    @classmethod
    def get_all_modules(cls) -> List[str]:
        """Get list of all supported module names."""
        return list(cls.MODULE_TO_SERVICE.keys())
    
    @classmethod
    def get_modules_by_category(cls, category: SAPModuleCategory) -> List[str]:
        """
        Get all modules belonging to a specific category.
        
        Args:
            category: SAP module category
            
        Returns:
            List of module names in that category
        """
        modules = []
        for module_name, service_name in cls.MODULE_TO_SERVICE.items():
            if cls.SERVICE_CATEGORIES.get(service_name) == category:
                modules.append(module_name)
        return modules
    
    @classmethod
    def is_valid_module(cls, module_name: str) -> bool:
        """
        Check if a module name is valid/supported.
        
        Args:
            module_name: SAP module name to validate
            
        Returns:
            True if module is supported, False otherwise
        """
        normalized_module = module_name.upper().strip()
        return normalized_module in cls.MODULE_TO_SERVICE
    
    @classmethod
    def get_module_info(cls, module_name: str) -> Optional[Dict[str, any]]:
        """
        Get comprehensive information about a module.
        
        Args:
            module_name: SAP module name
            
        Returns:
            Dictionary with module information or None if not found
        """
        service_name = cls.get_service_name(module_name)
        if not service_name:
            return None
        
        category = cls.get_category(service_name)
        
        return {
            "module_name": module_name.upper(),
            "service_name": service_name,
            "category": category.value if category else "unknown",
            "is_cloud": category in [SAPModuleCategory.CLOUD, SAPModuleCategory.PROCUREMENT] if category else False,
            "is_demo": category == SAPModuleCategory.DEMO if category else False
        }
    
    @classmethod
    def search_modules(cls, search_term: str) -> List[str]:
        """
        Search for modules matching a search term.
        
        Args:
            search_term: Search string (case-insensitive)
            
        Returns:
            List of matching module names
        """
        search_term = search_term.upper()
        return [
            module for module in cls.MODULE_TO_SERVICE.keys()
            if search_term in module
        ]


def build_sap_odata_url(
    server: str,
    port: int,
    service_name: str,
    use_https: bool = True,
    sap_client: Optional[str] = None
) -> str:
    """
    Build a complete SAP OData service URL.
    
    Args:
        server: SAP server hostname or IP
        port: SAP server port
        service_name: OData service name
        use_https: Use HTTPS protocol (default: True)
        sap_client: SAP client number (optional, e.g., '100')
        
    Returns:
        Complete SAP OData service URL
        
    Example:
        >>> build_sap_odata_url('myserver.com', 8000, 'EPM_REF_APPS_SHOP_SRV')
        'https://myserver.com:8000/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV'
    """
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{server}:{port}/sap/opu/odata/sap/{service_name}"
    
    # Add SAP client parameter if provided
    if sap_client:
        base_url += f"?sap-client={sap_client}"
    
    return base_url


def parse_sap_odata_url(url: str) -> Dict[str, any]:
    """
    Parse a SAP OData URL and extract components.
    
    Args:
        url: SAP OData service URL
        
    Returns:
        Dictionary with parsed components
        
    Example:
        >>> parse_sap_odata_url('https://myserver:8000/sap/opu/odata/sap/EPM_REF_APPS_SHOP_SRV')
        {
            'protocol': 'https',
            'server': 'myserver',
            'port': 8000,
            'service_name': 'EPM_REF_APPS_SHOP_SRV',
            'is_sap_standard': True
        }
    """
    import re
    
    # Pattern for SAP OData URL
    pattern = r'(https?)://([^:]+):(\d+)/sap/opu/odata/(?:sap|SAP)/([^/?]+)'
    match = re.match(pattern, url)
    
    if not match:
        raise ValueError(f"Invalid SAP OData URL format: {url}")
    
    protocol, server, port, service_name = match.groups()
    
    return {
        'protocol': protocol,
        'server': server,
        'port': int(port),
        'service_name': service_name,
        'is_sap_standard': '/sap/opu/odata/' in url.lower(),
        'use_https': protocol == 'https'
    }
