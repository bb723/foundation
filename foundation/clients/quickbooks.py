import os
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests
import urllib.parse
from intuitlib.client import AuthClient

# Set logging level to capture more information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuickBooksAuthError(Exception):
    """Custom exception for QuickBooks authentication errors"""
    pass

class QuickBooksClient:
    """Simplified QuickBooks Online API client focused on Standard Management Company."""
    
    BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
    PLAYGROUND_URL = "https://developer.intuit.com/app/developer/playground"
    
    def __init__(self, company_prefix: str = "STANDARD_MANAGEMENT_COMPANY"):
        """Initialize QuickBooks client using company-specific credentials."""
        self.company_prefix = company_prefix
        self.client_id = os.getenv("QUICKBOOKS_CLIENT_ID")
        self.client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET")
        self.refresh_token = os.getenv(f"{company_prefix}_QB_REFRESH_TOKEN")
        self.realm_id = os.getenv(f"{company_prefix}_QB_REALM_ID")
        
        print(f"\nInitializing {company_prefix} QuickBooks client")
        
        if not all([self.client_id, self.client_secret, self.refresh_token, self.realm_id]):
            raise ValueError(
                f"Missing required QuickBooks credentials for {company_prefix}"
            )
        
        self.auth_client = AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self.refresh_token,
            environment="production",
            redirect_uri="https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl"
        )
        
        # Get initial access token
        self.refresh_access_token()

    def _handle_auth_error(self, error: Exception) -> None:
        """Handle authentication errors with clear instructions"""
        error_msg = str(error)
        if "invalid_grant" in error_msg.lower():
            # This indicates the refresh token has expired (after 101 days)
            raise QuickBooksAuthError(
                f"\nQuickBooks refresh token has expired for {self.company_prefix}!\n"
                f"Please follow these steps:\n"
                f"1. Go to {self.PLAYGROUND_URL}\n"
                f"2. Enter these credentials:\n"
                f"   Client ID: {self.client_id}\n"
                f"   Client Secret: {self.client_secret}\n"
                f"3. Click 'Get authorization code' and sign in with {self.company_prefix} credentials\n"
                f"4. Click 'Get tokens'\n"
                f"5. Update the {self.company_prefix}_QB_REFRESH_TOKEN in your .env file\n"
                f"6. Update Heroku: heroku config:set {self.company_prefix}_QB_REFRESH_TOKEN='new_token' --app propertyops\n"
            )
        else:
            # This is some other authentication error
            raise QuickBooksAuthError(
                f"Failed to authenticate with QuickBooks for {self.company_prefix}: {error_msg}"
            )

    def refresh_access_token(self) -> None:
        """Refresh the OAuth access token."""
        try:
            print(f"Refreshing access token for {self.company_prefix}...")
            self.auth_client.refresh(refresh_token=self.refresh_token)
            print(f"Successfully refreshed access token")
        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            self._handle_auth_error(e)

    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None, json: Dict = None) -> Dict:
        """Make a request to the QuickBooks API with automatic token refresh on 401."""
        try:
            url = f"{self.BASE_URL}/{self.realm_id}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.auth_client.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            
            # Always include minorversion=75 in params
            if params is None:
                params = {}
            params['minorversion'] = '75'
            
            print(f"Making {method} request to {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json
            )
            
            if response.status_code >= 400:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
            
            if response.status_code == 401:
                # Access token might be expired, try refreshing it
                print("Received 401, attempting to refresh access token...")
                self.refresh_access_token()
                
                # Retry the request with new access token
                headers["Authorization"] = f"Bearer {self.auth_client.access_token}"
                print("Retrying request with new access token...")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json
                )
                
                if response.status_code == 401:
                    print("Still getting 401 after token refresh")
                    raise QuickBooksAuthError("Authentication failed even after token refresh")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: QuickBooks API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"ERROR DETAILS: {error_details}")
                    if 'Fault' in error_details:
                        error_msg = error_details['Fault'].get('Error', [{}])[0].get('Message', str(e))
                        error_detail = error_details['Fault'].get('Error', [{}])[0].get('Detail', '')
                        raise Exception(f"QuickBooks API error: {error_msg}. {error_detail}")
                except ValueError:
                    print(f"Raw error response: {e.response.text}")
                    raise Exception(f"QuickBooks API error: {e.response.text}")
            raise Exception(f"QuickBooks API request failed: {str(e)}")

    def _query_direct(self, query_string: str) -> Dict:
        """
        Make a direct query to QuickBooks API using GET method with URL encoding.
        This is a more reliable approach for complex queries.
        """
        try:
            # URL encode the query properly
            encoded_query = urllib.parse.quote(query_string)
            
            # Construct the full URL
            url = f"{self.BASE_URL}/{self.realm_id}/query?query={encoded_query}&minorversion=75"
            
            # Set up the headers
            headers = {
                "Authorization": f"Bearer {self.auth_client.access_token}",
                "Accept": "application/json"
            }
            
            print(f"Making query: {query_string}")
            
            # Make the request directly with GET method
            response = requests.get(url, headers=headers)
            
            # Only log errors
            if response.status_code >= 400:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
            
            if response.status_code == 401:
                # Token expired, refresh and retry
                print("Received 401, refreshing token and retrying...")
                self.refresh_access_token()
                
                # Update headers with new token
                headers["Authorization"] = f"Bearer {self.auth_client.access_token}"
                
                # Retry the request
                response = requests.get(url, headers=headers)
                
                if response.status_code == 401:
                    print("Still getting 401 after token refresh")
                    raise QuickBooksAuthError("Authentication failed even after token refresh")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"ERROR in direct query: {str(e)}")
            raise

    def get_transactions(self, start_date=None, end_date=None):
        """
        Get transactions from QuickBooks in the last 100 days.
        Returns simplified format that works with receipt processing.
        """
        if not start_date:
            # Look back 100 days
            start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            logger.info(f"Querying transactions from {start_date} to {end_date}...")
            
            # Look for multiple transaction types
            transaction_types = [
                ('Purchase', None),  # All purchases
                ('Bill', None),  # Bills
                ('Expense', None),  # Expenses
                ('JournalEntry', None)  # Journal entries
            ]
            all_transactions = []
            filtered_transactions = []
            
            for txn_type, _ in transaction_types:
                # Build the query to get all transactions
                query = f"""
                    SELECT * FROM {txn_type} 
                    WHERE TxnDate >= '{start_date}' 
                    AND TxnDate <= '{end_date}'
                """
                    
                logger.info(f"Querying {txn_type} transactions with query: {query}")
                
                try:
                    response = self._query_direct(query)
                    logger.debug(f"Raw response for {txn_type}: {response}")
                    
                    if 'QueryResponse' in response and txn_type in response['QueryResponse']:
                        transactions = response['QueryResponse'][txn_type]
                        logger.info(f"Found {len(transactions)} {txn_type} transactions")
                        
                        # Format transactions
                        for txn in transactions:
                            try:
                                formatted = self._format_transaction(txn, txn_type)
                                all_transactions.append(formatted)
                                
                                # Check if any line item has the account we're looking for
                                has_matching_account = False
                                for line_item in formatted.get('line_items', []):
                                    if line_item.get('account_name') == '6300 Reimbursable Expenses':
                                        has_matching_account = True
                                        break
                                
                                if has_matching_account:
                                    filtered_transactions.append(formatted)
                                    logger.info(f"Added transaction {formatted['id']} ({formatted['type']}) with account '6300 Reimbursable Expenses'")
                                else:
                                    logger.debug(f"Skipped transaction {formatted['id']} ({formatted['type']}) with account: {formatted.get('account_name', '')}")
                                    
                            except Exception as format_error:
                                logger.error(f"Error formatting {txn_type} transaction {txn.get('Id')}: {str(format_error)}")
                                logger.error(f"Transaction data: {txn}")
                                continue
                    else:
                        logger.warning(f"No {txn_type} transactions found")
                        logger.debug(f"Response structure: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
                except Exception as e:
                    logger.error(f"Error querying {txn_type} transactions: {str(e)}")
                    logger.exception("Full traceback:")
                    continue
            
            # Sort transactions by date (newest first)
            filtered_transactions.sort(key=lambda x: x['date'], reverse=True)
            
            logger.info(f"Found {len(all_transactions)} total transactions")
            logger.info(f"Found {len(filtered_transactions)} transactions with account '6300 Reimbursable Expenses'")
            
            if len(filtered_transactions) == 0:
                logger.warning("No transactions found with account '6300 Reimbursable Expenses'")
                # Return all transactions for debugging
                return all_transactions
            
            return filtered_transactions
                
        except Exception as e:
            logger.error(f"ERROR in get_transactions: {str(e)}")
            logger.error(f"ERROR TYPE: {type(e).__name__}")
            
            if hasattr(e, "__traceback__"):
                import traceback
                logger.error("TRACEBACK:")
                logger.error(traceback.format_tb(e.__traceback__))
            
            # Create a dummy transaction for testing
            logger.warning("Returning dummy transaction for testing")
            return [{
                'id': 'test123',
                'type': 'Purchase',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'amount': 100.0,
                'memo': 'Test transaction',
                'entity_name': 'Test Vendor',
                'account_name': '6300 Reimbursable Expenses'
            }]

    def _format_transaction(self, txn, txn_type):
        """Format a transaction into a simplified structure"""
        try:
            # Get basic transaction info
            formatted = {
                'id': txn.get('Id'),
                'type': txn_type,
                'date': txn.get('TxnDate', ''),
                'amount': float(txn.get('TotalAmt', 0)),
                'memo': txn.get('PrivateNote', '') or txn.get('DocNumber', '') or '',
                'entity_name': txn.get('VendorRef', {}).get('name', '') or txn.get('CustomerRef', {}).get('name', ''),
                'entity_id': txn.get('VendorRef', {}).get('value', '') or txn.get('CustomerRef', {}).get('value', ''),
                'payment_type': txn.get('PaymentType', ''),
                'doc_number': txn.get('DocNumber', ''),
                'private_note': txn.get('PrivateNote', ''),
                'sync_token': txn.get('SyncToken', ''),
                'meta_data': {
                    'create_time': txn.get('MetaData', {}).get('CreateTime', ''),
                    'last_updated_time': txn.get('MetaData', {}).get('LastUpdatedTime', ''),
                }
            }
            
            # Get line items and their accounts
            line_items = []
            if 'Line' in txn:
                lines = txn['Line'] if isinstance(txn['Line'], list) else [txn['Line']]
                for line in lines:
                    if 'DetailType' in line:
                        # Extract account information based on the detail type
                        account_ref = None
                        if line['DetailType'] == 'AccountBasedExpenseLineDetail':
                            account_ref = line.get('AccountBasedExpenseLineDetail', {}).get('AccountRef', {})
                        elif line['DetailType'] == 'SalesItemLineDetail':
                            account_ref = line.get('SalesItemLineDetail', {}).get('AccountRef', {})
                        elif line['DetailType'] == 'JournalEntryLineDetail':
                            account_ref = line.get('JournalEntryLineDetail', {}).get('AccountRef', {})
                        
                        line_item = {
                            'amount': float(line.get('Amount', 0)),
                            'description': line.get('Description', ''),
                            'account_id': account_ref.get('value', '') if account_ref else '',
                            'account_name': account_ref.get('name', '') if account_ref else '',
                            'detail_type': line.get('DetailType', ''),
                            'line_num': line.get('LineNum', '')
                        }
                        line_items.append(line_item)
            
            formatted['line_items'] = line_items
            
            # Get account info from the first line item if available
            if line_items:
                formatted['account_id'] = line_items[0]['account_id']
                formatted['account_name'] = line_items[0]['account_name']
            else:
                formatted['account_id'] = ''
                formatted['account_name'] = ''
            
            # Add any additional fields based on transaction type
            if txn_type == 'Purchase':
                formatted.update({
                    'payment_method': txn.get('PaymentMethodRef', {}).get('name', ''),
                    'credit': txn.get('Credit', False),
                    'currency': txn.get('CurrencyRef', {}).get('name', 'USD'),
                })
            elif txn_type == 'Bill':
                formatted.update({
                    'due_date': txn.get('DueDate', ''),
                    'balance': float(txn.get('Balance', 0)),
                    'status': txn.get('Status', ''),
                })
            elif txn_type == 'Expense':
                formatted.update({
                    'payment_method': txn.get('PaymentMethodRef', {}).get('name', ''),
                    'check_number': txn.get('CheckNum', ''),
                })
            elif txn_type == 'JournalEntry':
                formatted.update({
                    'adjustment': txn.get('Adjustment', False),
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {str(e)}")
            logger.error(f"Transaction data: {txn}")
            raise

    def get_ar_aging(self, as_of_date: Optional[datetime] = None) -> Dict:
        """Get the AR Aging report."""
        try:
            params = {
                "report_date": (as_of_date or datetime.now()).strftime("%Y-%m-%d"),
                "aging_period": 30,
                "num_periods": 4
            }
            return self._make_request("reports/AgedReceivables", params=params)
        except Exception as e:
            print(f"Error in get_ar_aging: {str(e)}")
            return {"error": str(e)}

    def get_customer_id(self, customer_name: str) -> Optional[str]:
        """Get the QuickBooks customer ID for a given customer name."""
        try:
            query = f"SELECT Id FROM Customer WHERE DisplayName = '{customer_name}'"
            response = self._query_direct(query)
            if 'QueryResponse' in response and 'Customer' in response['QueryResponse']:
                customers = response['QueryResponse']['Customer']
                if customers:
                    return customers[0]['Id']
            return None
        except Exception as e:
            print(f"Error getting customer ID: {str(e)}")
            return None

    def _map_item_name(self, original_name: str) -> str:
        """Map item names from our system to QuickBooks item names"""
        item_mapping = {
            "Management Fees": "Management Fee",
            "4100 - Rent Income": "Sales",
            "4440 - Application Fee Income": "Application Fee",
            "General Labor: General Labor": "General Labor",
            "Placement Fees": "Commission",
            "Commissions/Placement Fees": "Commission",
            "4460 - Late Fee": "Late Fee",
            "Supplies": "Sales",
            "6175 - Garbage and Recycling":"Sales",
            "6040 - Pest Management":"Pest Control Contractors",
            "6101 - Legal Fees":"Legal Services",
            "6141 - Painting":"Painting supplies",
            "2120 - Clearing Account":"Sales"
        }
        return item_mapping.get(original_name, original_name)

    def get_item_id(self, item_name: str) -> Optional[str]:
        """Get the QuickBooks item ID for a given item name."""
        try:
            # First try with the mapped name
            mapped_name = self._map_item_name(item_name)
            query = f"SELECT Id, Type FROM Item WHERE Name = '{mapped_name}'"
            response = self._query_direct(query)
            
            if 'QueryResponse' in response and 'Item' in response['QueryResponse']:
                items = response['QueryResponse']['Item']
                if items:
                    item = items[0]
                    if item.get('Type') not in ['Service', 'Inventory', 'NonInventory']:
                        # If the item is a category, try to find a similar item that is a service
                        query = f"SELECT Id, Name, Type FROM Item WHERE Type IN ('Service', 'Inventory', 'NonInventory') AND Name LIKE '%{mapped_name}%'"
                        response = self._query_direct(query)
                        if 'QueryResponse' in response and 'Item' in response['QueryResponse']:
                            items = response['QueryResponse']['Item']
                            if items:
                                # Use the first matching service item
                                return items[0]['Id']
                        raise Exception(
                            f"Item '{mapped_name}' is set up as a category in QuickBooks. "
                            f"Please create it as a Service, Inventory, or NonInventory item."
                        )
                    return item['Id']
            
            # If not found, try to get a list of available items
            query = "SELECT Name, Type FROM Item WHERE Type IN ('Service', 'Inventory', 'NonInventory')"
            response = self._query_direct(query)
            if 'QueryResponse' in response and 'Item' in response['QueryResponse']:
                available_items = [
                    f"{item['Name']} ({item.get('Type', 'Unknown')})" 
                    for item in response['QueryResponse']['Item']
                ]
                raise Exception(
                    f"Item '{mapped_name}' not found in QuickBooks. "
                    f"Available items are: {', '.join(available_items)}"
                )
            
            return None
        except Exception as e:
            logger.error(f"Error getting item ID: {str(e)}")
            raise

    def create_invoice(self, items):
        """
        Create an invoice in QuickBooks.
        
        Args:
            items: List of invoice items with the following structure:
                {
                    'Customer': str,
                    'InvoiceDate': str,  # YYYY-MM-DD format
                    'DueDate': str,      # YYYY-MM-DD format
                    'Item': str,
                    'Description': str,
                    'Quantity': float,
                    'Rate': float,
                    'Amount': float,
                    'ServiceDate': str    # YYYY-MM-DD format
                }
        """
        if not items:
            raise ValueError("No items provided for invoice creation")

        # Extract property address from description and sort by that, then by date
        def get_property_address(item):
            desc = item.get('Description', '')
            # Extract the property address part (everything before "Management Fees" or "-")
            parts = desc.split('Management Fees') if 'Management Fees' in desc else desc.split('-', 1)
            return parts[0].strip()

        # Sort items by property address first, then by date
        invoice_items = items.copy()  # Create a copy to avoid modifying original
        invoice_items.sort(
            key=lambda x: (
                get_property_address(x),  # Sort by property address first
                x.get('ServiceDate') or x.get('InvoiceDate', '')  # Then by date
            )
        )

        try:
            # First, group items by Customer
            customer_invoices = {}
            for item in invoice_items:
                customer = item['Customer']
                if customer not in customer_invoices:
                    customer_invoices[customer] = []
                customer_invoices[customer].append(item)
            
            results = []
            for customer, customer_items in customer_invoices.items():
                # Find the customer ID in QuickBooks
                customer_id = self.get_customer_id(customer)
                if not customer_id:
                    raise Exception(f"Customer '{customer}' not found in QuickBooks")
                
                # Format the invoice lines
                invoice_lines = []
                for item in customer_items:
                    # Map the item name to its QuickBooks equivalent
                    mapped_item_name = self._map_item_name(item['Item'])
                    
                    # Look up the Item ID in QuickBooks
                    item_id = self.get_item_id(item['Item'])
                    if not item_id:
                        raise Exception(f"Item '{mapped_item_name}' (originally '{item['Item']}') not found in QuickBooks")
                    
                    # For management fees, we'll use a quantity of 1 and the amount as the unit price
                    if "Management Fee" in mapped_item_name:
                        qty = "1"
                        unit_price = str(item['Amount'])
                    else:
                        qty = str(item['Quantity']) if item['Quantity'] is not None else "1"
                        unit_price = str(item['Rate']) if item['Rate'] is not None else str(item['Amount'])
                    
                    # Format service date
                    service_date = item.get('ServiceDate') or item.get('InvoiceDate')
                    
                    # Add the line to the invoice
                    invoice_lines.append({
                        "DetailType": "SalesItemLineDetail",
                        "Amount": str(item['Amount']),
                        "Description": item['Description'],
                        "SalesItemLineDetail": {
                            "ItemRef": {
                                "value": item_id,
                                "name": mapped_item_name
                            },
                            "Qty": qty,
                            "UnitPrice": unit_price,
                            "ServiceDate": service_date
                        }
                    })
                
                # Format the invoice data according to QuickBooks API requirements
                invoice_data = {
                    "Line": invoice_lines,
                    "CustomerRef": {
                        "value": customer_id,
                        "name": customer
                    },
                    "TxnDate": datetime.now().strftime('%Y-%m-%d'),  # Use current date for invoice creation
                    "DueDate": customer_items[0]['DueDate'],
                    "PrivateNote": f"Created via BuildingBlocks on {datetime.now().strftime('%Y-%m-%d')} for service period {customer_items[0]['InvoiceDate']}",
                    "DocNumber": f"BB-{datetime.now().strftime('%Y%m%d-%H%M%S')}",  # Use current date in doc number
                    "GlobalTaxCalculation": "NotApplicable",
                    "CurrencyRef": {
                        "value": "USD",
                        "name": "United States Dollar"
                    }
                }
                
                # Log the request data for debugging
                print(f"Creating invoice with data: {json.dumps(invoice_data, indent=2)}")
                
                # Make the API request to create the invoice
                response = self._make_request("invoice", method="POST", json=invoice_data)
                
                if 'Invoice' in response:
                    invoice = response['Invoice']
                    invoice['QuickBooksUrl'] = f"https://qbo.intuit.com/app/invoice?txnId={invoice['Id']}"
                    invoice['Customer'] = customer
                    results.append(invoice)
                else:
                    raise Exception("Invalid response from QuickBooks API")
            
            return results[0] if len(results) == 1 else results
                
        except Exception as e:
            print(f"Error creating invoice in QuickBooks: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test the QuickBooks connection by making a simple API call.
        Returns True if successful, raises an exception if not."""
        try:
            logger.info("Testing QuickBooks connection...")
            
            # Check if credentials are set
            if not all([self.client_id, self.client_secret, self.refresh_token, self.realm_id]):
                missing = []
                if not self.client_id:
                    missing.append("QUICKBOOKS_CLIENT_ID")
                if not self.client_secret:
                    missing.append("QUICKBOOKS_CLIENT_SECRET")
                if not self.refresh_token:
                    missing.append(f"{self.company_prefix}_QB_REFRESH_TOKEN")
                if not self.realm_id:
                    missing.append(f"{self.company_prefix}_QB_REALM_ID")
                raise ValueError(f"Missing required QuickBooks credentials: {', '.join(missing)}")
            
            logger.info("Credentials present, attempting to refresh access token...")
            self.refresh_access_token()
            
            # Try to get company info - a lightweight call
            logger.info("Making test API call to get company info...")
            response = self._make_request("companyinfo/" + self.realm_id)
            
            if 'CompanyInfo' in response:
                company_name = response['CompanyInfo'].get('CompanyName', 'Unknown')
                logger.info(f"Successfully connected to QuickBooks! Company: {company_name}")
                return True
            else:
                logger.error(f"Unexpected response format: {response}")
                raise Exception("Invalid response format from QuickBooks API")
                
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            logger.exception("Full traceback:")
            raise

    def update_transaction_categorization(self, transaction_id: str, transaction_type: str, line_items: List[Dict]) -> Dict:
        """
        Update a transaction's categorization in QuickBooks.
        
        Args:
            transaction_id: The ID of the transaction to update
            transaction_type: The type of transaction (e.g., 'Purchase', 'Bill')
            line_items: List of line items with categories and amounts
        """
        try:
            # First, get the current transaction
            query = f"SELECT * FROM {transaction_type} WHERE Id = '{transaction_id}'"
            response = self._query_direct(query)
            
            if 'QueryResponse' not in response or transaction_type not in response['QueryResponse']:
                raise Exception(f"Transaction {transaction_id} not found")
            
            transaction = response['QueryResponse'][transaction_type][0]
            
            # Prepare the update payload
            update_data = {
                "Id": transaction_id,
                "SyncToken": transaction.get('SyncToken', '0'),
                "Line": []
            }
            
            # Add each line item with its category
            for item in line_items:
                # Get the account ID for the category
                account_query = f"SELECT Id FROM Account WHERE Name = '{item['category']}'"
                account_response = self._query_direct(account_query)
                
                if 'QueryResponse' not in account_response or 'Account' not in account_response['QueryResponse']:
                    raise Exception(f"Account for category {item['category']} not found")
                
                account_id = account_response['QueryResponse']['Account'][0]['Id']
                
                # Add the line item
                update_data["Line"].append({
                    "Amount": str(item['amount']),
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {
                            "value": account_id
                        }
                    }
                })
            
            # Make the update request
            endpoint = f"{transaction_type.lower()}/{transaction_id}"
            response = self._make_request(endpoint, method="POST", json=update_data)
            
            if transaction_type in response:
                return {
                    "success": True,
                    "message": f"Successfully updated {transaction_type} {transaction_id}",
                    "transaction": response[transaction_type]
                }
            else:
                raise Exception("Invalid response from QuickBooks API")
                
        except Exception as e:
            print(f"Error updating transaction categorization: {str(e)}")
            raise

# Add alias for backward compatibility
QuickBooks = QuickBooksClient

# Example usage
if __name__ == "__main__":
    qb = QuickBooksClient()
    try:
        qb.test_connection()
        print("✓ QuickBooks connection test passed!")
    except Exception as e:
        print(f"✗ QuickBooks connection test failed: {str(e)}")
    
    # Get last 30 days of transactions
    transactions = qb.get_transactions()
    print(f"Found {len(transactions)} total transactions")
    
    # Get AR aging report
    aging = qb.get_ar_aging()
    print("Retrieved AR aging report")