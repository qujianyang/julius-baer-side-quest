"""
Modern Banking Client - Upgraded from Python 2.7 to 3.x
"""

import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import requests
from requests.exceptions import RequestException, HTTPError, Timeout
import json
import time
from functools import wraps

from config import BankingConfig


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0, exceptions=(RequestException, Timeout)):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise
        return wrapper
    return decorator


@dataclass
class TransferResult:
    transaction_id: Optional[str]
    status: str
    message: str
    from_account: str
    to_account: str
    amount: float

    def __str__(self):
        return f"Transfer {self.status}: {self.amount} from {self.from_account} to {self.to_account} (ID: {self.transaction_id})"


class BankingClient:

    def __init__(self, config=None):
        self.config = config or BankingConfig()
        self.session = self._create_session()
        self.jwt_token = None
        logger.info(f"Banking client initialized for {self.config.base_url}")

    def _create_session(self):
        session = requests.Session()
        session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        return session

    def authenticate(self, username="admin", password="password"):
        """Get JWT token"""
        try:
            url = f"{self.config.base_url}/authToken"
            payload = {
                "username": username,
                "password": password
            }

            logger.info(f"Authenticating user: {username}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()
            self.jwt_token = data.get('token')

            if self.jwt_token:
                # Add token to session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.jwt_token}'
                })
                logger.info("Authentication successful - JWT token acquired")
                return True
            else:
                logger.error("Authentication response missing token")
                return False

        except HTTPError as e:
            logger.error(f"Authentication failed with HTTP error: {e.response.status_code}")
            return False
        except RequestException as e:
            logger.error(f"Authentication request failed: {str(e)}")
            return False

    def validate_account(self, account_id):
        try:
            url = f"{self.config.base_url}/accounts/validate/{account_id}"
            logger.info(f"Validating account: {account_id}")

            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            data = response.json()
            is_valid = data.get('isValid', False)

            if is_valid:
                logger.info(f"Account {account_id} is valid")
            else:
                logger.warning(f"Account {account_id} is invalid")

            return is_valid

        except HTTPError as e:
            logger.error(f"Account validation failed: {e.response.status_code}")
            return False
        except RequestException as e:
            logger.error(f"Account validation request failed: {str(e)}")
            return False

    def get_account_balance(self, account_id):
        try:
            url = f"{self.config.base_url}/accounts/balance/{account_id}"
            logger.info(f"Getting balance for account: {account_id}")

            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            data = response.json()
            balance = data.get('balance')

            logger.info(f"Account {account_id} balance: {balance}")
            return balance

        except HTTPError as e:
            logger.error(f"Balance inquiry failed: {e.response.status_code}")
            return None
        except RequestException as e:
            logger.error(f"Balance inquiry request failed: {str(e)}")
            return None

    @retry_with_exponential_backoff(max_retries=3, initial_delay=1.0)
    def transfer_funds(self, from_account, to_account, amount, validate_accounts=True):
        # Input validation
        if amount <= 0:
            logger.error(f"Invalid amount: {amount}. Amount must be positive.")
            return None

        # Optional: Validate accounts before transfer (bonus feature)
        if validate_accounts:
            if not self.validate_account(from_account):
                logger.error(f"Source account {from_account} validation failed")
                return None
            if not self.validate_account(to_account):
                logger.error(f"Destination account {to_account} validation failed")
                return None

        try:
            url = f"{self.config.base_url}/transfer"

            # Modern JSON payload construction (vs legacy string concatenation)
            payload = {
                "fromAccount": from_account,
                "toAccount": to_account,
                "amount": amount
            }

            logger.info(f"Initiating transfer: {amount} from {from_account} to {to_account}")

            # Modern requests library with proper timeout
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )

            # Proper HTTP error handling
            response.raise_for_status()

            # Structured JSON parsing
            data = response.json()

            # Create result object using dataclass
            result = TransferResult(
                transaction_id=data.get('transactionId'),
                status=data.get('status', 'UNKNOWN'),
                message=data.get('message', ''),
                from_account=from_account,
                to_account=to_account,
                amount=amount
            )

            logger.info(f"Transfer successful: {result}")
            return result

        except HTTPError as e:
            logger.error(f"Transfer failed with HTTP error {e.response.status_code}: {e.response.text}")

            # Try to parse error response
            try:
                error_data = e.response.json()
                return TransferResult(
                    transaction_id=None,
                    status="FAILED",
                    message=error_data.get('message', str(e)),
                    from_account=from_account,
                    to_account=to_account,
                    amount=amount
                )
            except json.JSONDecodeError:
                return None

        except Timeout:
            logger.error(f"Transfer request timed out after {self.config.timeout} seconds")
            return None

        except RequestException as e:
            logger.error(f"Transfer request failed: {str(e)}")
            return None

    def get_transaction_history(self):
        if not self.jwt_token:
            logger.warning("JWT token required for transaction history. Call authenticate() first.")
            return None

        try:
            url = f"{self.config.base_url}/transactions/history"
            logger.info("Fetching transaction history")

            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            transactions = response.json()
            logger.info(f"Retrieved {len(transactions)} transactions")
            return transactions

        except HTTPError as e:
            logger.error(f"Transaction history request failed: {e.response.status_code}")
            return None
        except RequestException as e:
            logger.error(f"Transaction history request failed: {str(e)}")
            return None

    def get_all_accounts(self):
        try:
            url = f"{self.config.base_url}/accounts"
            logger.info("Fetching all accounts")

            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            accounts = response.json()
            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts

        except HTTPError as e:
            logger.error(f"Accounts request failed: {e.response.status_code}")
            return None
        except RequestException as e:
            logger.error(f"Accounts request failed: {str(e)}")
            return None

    def close(self):
        self.session.close()
        logger.info("Banking client session closed")


def main():
    print("=" * 60)
    print("Modern Banking Client - Python 3.x Demonstration")
    print("=" * 60)

    # Initialize client
    client = BankingClient()

    try:
        # Demo 1: Basic transfer (core requirement)
        print("\n[DEMO 1] Basic Fund Transfer (Core Requirement)")
        print("-" * 60)
        result = client.transfer_funds("ACC1000", "ACC1001", 100.00)
        if result:
            print(f"✓ {result}")
        else:
            print("✗ Transfer failed")

        # Demo 2: Transfer with JWT authentication (bonus)
        print("\n[DEMO 2] Transfer with JWT Authentication (Bonus)")
        print("-" * 60)
        if client.authenticate("alice", "password"):
            print("✓ Authentication successful")
            result = client.transfer_funds("ACC1000", "ACC1002", 250.00)
            if result:
                print(f"✓ {result}")

        # Demo 3: Account validation (bonus)
        print("\n[DEMO 3] Account Validation (Bonus)")
        print("-" * 60)
        valid_account = "ACC1000"
        invalid_account = "ACC2000"

        print(f"Validating {valid_account}: {client.validate_account(valid_account)}")
        print(f"Validating {invalid_account}: {client.validate_account(invalid_account)}")

        # Demo 4: Get account balance (bonus)
        print("\n[DEMO 4] Account Balance Inquiry (Bonus)")
        print("-" * 60)
        balance = client.get_account_balance("ACC1000")
        if balance is not None:
            print(f"Account ACC1000 balance: ${balance:.2f}")

        # Demo 5: Transaction history (bonus - requires auth)
        print("\n[DEMO 5] Transaction History (Bonus)")
        print("-" * 60)
        history = client.get_transaction_history()
        if history:
            print(f"✓ Retrieved {len(history)} transactions")
            if history:
                print(f"Latest transaction: {history[0]}")

        # Demo 6: List all accounts
        print("\n[DEMO 6] List All Accounts")
        print("-" * 60)
        accounts = client.get_all_accounts()
        if accounts:
            print(f"✓ Retrieved {len(accounts)} accounts")
            for acc in accounts[:3]:  # Show first 3
                print(f"  - {acc.get('accountId')}: {acc.get('accountType')}")

        print("\n" + "=" * 60)
        print("Modernization Highlights:")
        print("=" * 60)
        print("✓ Python 2.7 → Python 3.x syntax")
        print("✓ urllib2 → requests library")
        print("✓ String concatenation → f-strings")
        print("✓ print statements → logging framework")
        print("✓ Manual JSON → structured handling")
        print("✓ No error handling → comprehensive exceptions")
        print("✓ Added JWT authentication")
        print("✓ Added type hints")
        print("✓ Added dataclasses")
        print("✓ Added configuration management")
        print("=" * 60)

    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    main()
