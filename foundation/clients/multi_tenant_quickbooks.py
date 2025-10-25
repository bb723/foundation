from typing import Dict, List, Optional
import os
from foundation.clients.quickbooks import QuickBooksClient, QuickBooksAuthError

class Companies:
    """Constants for company names to ensure consistency"""
    DJANGO = "DJANGO"
    STANDARD_MGMT = "STANDARD_MANAGEMENT_COMPANY"
    STANDARD_PROPS = "STANDARD_PROPERTIES"
    CMR = "CMR"

    @classmethod
    def all(cls) -> List[str]:
        """Get list of all company prefixes"""
        return [
            cls.DJANGO,
            cls.STANDARD_MGMT,
            cls.STANDARD_PROPS,
            cls.CMR
        ]

class MultiTenantQB:
    """Simplified multi-tenant QuickBooks client"""
    
    def __init__(self, companies: Optional[List[str]] = None):
        """Initialize with specific companies or all companies"""
        self.companies = companies or Companies.all()
        self.clients: Dict[str, QuickBooksClient] = {}
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize QuickBooks clients for each company"""
        for company in self.companies:
            try:
                self.clients[company] = QuickBooksClient(company_prefix=company)
            except ValueError as e:
                print(f"Could not initialize client for {company}: {str(e)}")

    def get_client(self, company: str) -> Optional[QuickBooksClient]:
        """Get QuickBooks client for a specific company"""
        return self.clients.get(company)

    def get_ar_aging(self, companies: Optional[List[str]] = None) -> Dict[str, Dict]:
        """Get AR aging reports for specified companies"""
        companies = companies or self.companies
        reports = {}
        auth_errors = {}
        
        for company in companies:
            client = self.get_client(company)
            if not client:
                print(f"No client available for {company}")
                continue
                
            try:
                raw_report = client.get_ar_aging()
                formatted_report = self.format_ar_report(raw_report)
                reports[company] = formatted_report
            except QuickBooksAuthError as e:
                auth_errors[company] = str(e)
                print(f"Authentication error for {company}: {str(e)}")
                continue
            except Exception as e:
                print(f"Error getting AR aging for {company}: {str(e)}")
                continue
                
        return {
            "reports": reports,
            "auth_errors": auth_errors
        }

    def format_ar_report(self, report: Dict) -> List[List[str]]:
        """Format AR aging report for display"""
        if not report or 'Rows' not in report:
            return []

        formatted = []
        headers = ["Customer", "Current", "1-30 Days", "31-60 Days", "61-90 Days", "91+ Days", "Total"]
        formatted.append(headers)

        rows = report['Rows'].get('Row', [])
        
        for row in rows:
            col_data = row.get('ColData')
            if not col_data or row.get('type') == 'Section':
                continue
            
            row_data = []
            for i, col in enumerate(col_data):
                value = col.get('value', '')
                if i == 0:
                    row_data.append(value)
                else:
                    if value == '':
                        value = '0.00'
                    try:
                        clean_value = value.replace('$', '').replace(',', '')
                        amount = float(clean_value)
                        row_data.append(f"${amount:,.2f}")
                    except ValueError:
                        row_data.append(value)
            formatted.append(row_data)

        # Add totals
        for row in rows:
            if row.get('type') == 'Section' and row.get('group') == 'GrandTotal':
                total_row = ['TOTAL']
                col_data = row.get('Summary', {}).get('ColData', [])
                for col in col_data[1:]:
                    value = col.get('value', '0.00')
                    try:
                        amount = float(value.replace('$', '').replace(',', ''))
                        total_row.append(f"${amount:,.2f}")
                    except ValueError:
                        total_row.append(value)
                formatted.append(total_row)
                break

        return formatted