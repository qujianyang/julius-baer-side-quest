"""
Unit Tests for Modern Banking Client
Demonstrates modern testing practices (bonus points)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from banking_client import BankingClient, TransferResult, BankingConfig
import requests


@pytest.fixture
def mock_config():
    """Fixture for test configuration"""
    return BankingConfig(
        base_url="http://localhost:8123",
        timeout=10
    )


@pytest.fixture
def client(mock_config):
    """Fixture for banking client"""
    return BankingClient(mock_config)


class TestBankingClientInitialization:
    """Test client initialization"""

    def test_client_creation_with_default_config(self):
        """Test creating client with default configuration"""
        client = BankingClient()
        assert client.config is not None
        assert client.session is not None
        assert client.jwt_token is None

    def test_client_creation_with_custom_config(self, mock_config):
        """Test creating client with custom configuration"""
        client = BankingClient(mock_config)
        assert client.config == mock_config
        assert client.config.timeout == 10


class TestAuthentication:
    """Test JWT authentication"""

    @patch('banking_client.requests.Session.post')
    def test_successful_authentication(self, mock_post, client):
        """Test successful JWT authentication"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': 'test-jwt-token'}
        mock_post.return_value = mock_response

        result = client.authenticate("alice", "password")

        assert result is True
        assert client.jwt_token == 'test-jwt-token'
        assert 'Authorization' in client.session.headers
        assert client.session.headers['Authorization'] == 'Bearer test-jwt-token'

    @patch('banking_client.requests.Session.post')
    def test_failed_authentication(self, mock_post, client):
        """Test failed authentication"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_post.return_value = mock_response

        result = client.authenticate("wrong", "credentials")

        assert result is False
        assert client.jwt_token is None


class TestAccountValidation:
    """Test account validation"""

    @patch('banking_client.requests.Session.get')
    def test_valid_account(self, mock_get, client):
        """Test validating a valid account"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accountId': 'ACC1000',
            'isValid': True,
            'status': 'ACTIVE'
        }
        mock_get.return_value = mock_response

        result = client.validate_account('ACC1000')

        assert result is True
        mock_get.assert_called_once()

    @patch('banking_client.requests.Session.get')
    def test_invalid_account(self, mock_get, client):
        """Test validating an invalid account"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accountId': 'ACC2000',
            'isValid': False,
            'status': 'INVALID'
        }
        mock_get.return_value = mock_response

        result = client.validate_account('ACC2000')

        assert result is False


class TestFundTransfer:
    """Test fund transfer functionality (core requirement)"""

    @patch('banking_client.requests.Session.post')
    def test_successful_transfer(self, mock_post, client):
        """Test successful fund transfer"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'transactionId': 'txn-123',
            'status': 'SUCCESS',
            'message': 'Transfer completed successfully',
            'fromAccount': 'ACC1000',
            'toAccount': 'ACC1001',
            'amount': 100.0
        }
        mock_post.return_value = mock_response

        result = client.transfer_funds('ACC1000', 'ACC1001', 100.0, validate_accounts=False)

        assert result is not None
        assert isinstance(result, TransferResult)
        assert result.transaction_id == 'txn-123'
        assert result.status == 'SUCCESS'
        assert result.amount == 100.0

    @patch('banking_client.requests.Session.post')
    def test_failed_transfer_http_error(self, mock_post, client):
        """Test failed transfer due to HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Insufficient funds'
        mock_response.json.return_value = {
            'message': 'Insufficient funds'
        }
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        result = client.transfer_funds('ACC1000', 'ACC1001', 1000000.0, validate_accounts=False)

        assert result is not None
        assert result.status == 'FAILED'

    def test_invalid_amount(self, client):
        """Test transfer with invalid amount"""
        result = client.transfer_funds('ACC1000', 'ACC1001', -100.0)

        assert result is None

    @patch('banking_client.BankingClient.validate_account')
    @patch('banking_client.requests.Session.post')
    def test_transfer_with_validation(self, mock_post, mock_validate, client):
        """Test transfer with account validation"""
        # Mock validation
        mock_validate.return_value = True

        # Mock successful transfer
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'transactionId': 'txn-456',
            'status': 'SUCCESS',
            'message': 'Transfer completed',
            'fromAccount': 'ACC1000',
            'toAccount': 'ACC1001',
            'amount': 50.0
        }
        mock_post.return_value = mock_response

        result = client.transfer_funds('ACC1000', 'ACC1001', 50.0, validate_accounts=True)

        assert result is not None
        assert result.status == 'SUCCESS'
        assert mock_validate.call_count == 2  # Called for both accounts


class TestAccountBalance:
    """Test account balance inquiry"""

    @patch('banking_client.requests.Session.get')
    def test_get_balance_success(self, mock_get, client):
        """Test getting account balance"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accountId': 'ACC1000',
            'balance': 5000.0
        }
        mock_get.return_value = mock_response

        balance = client.get_account_balance('ACC1000')

        assert balance == 5000.0


class TestTransactionHistory:
    """Test transaction history (bonus feature)"""

    @patch('banking_client.requests.Session.get')
    def test_get_history_with_token(self, mock_get, client):
        """Test getting transaction history with JWT token"""
        # Set JWT token
        client.jwt_token = 'test-token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'transactionId': 'txn-1', 'amount': 100.0},
            {'transactionId': 'txn-2', 'amount': 200.0}
        ]
        mock_get.return_value = mock_response

        history = client.get_transaction_history()

        assert history is not None
        assert len(history) == 2

    def test_get_history_without_token(self, client):
        """Test getting history without authentication"""
        history = client.get_transaction_history()

        assert history is None


class TestSessionManagement:
    """Test session management"""

    def test_session_close(self, client):
        """Test closing the client session"""
        mock_session = Mock()
        client.session = mock_session

        client.close()

        mock_session.close.assert_called_once()


class TestTransferResult:
    """Test TransferResult dataclass"""

    def test_transfer_result_creation(self):
        """Test creating a TransferResult"""
        result = TransferResult(
            transaction_id='txn-789',
            status='SUCCESS',
            message='Completed',
            from_account='ACC1000',
            to_account='ACC1001',
            amount=150.0
        )

        assert result.transaction_id == 'txn-789'
        assert result.status == 'SUCCESS'
        assert result.amount == 150.0

    def test_transfer_result_string_representation(self):
        """Test TransferResult string representation"""
        result = TransferResult(
            transaction_id='txn-789',
            status='SUCCESS',
            message='Completed',
            from_account='ACC1000',
            to_account='ACC1001',
            amount=150.0
        )

        str_repr = str(result)
        assert 'SUCCESS' in str_repr
        assert '150.0' in str_repr
        assert 'ACC1000' in str_repr


class TestConfiguration:
    """Test configuration management"""

    def test_default_config(self):
        """Test default configuration values"""
        config = BankingConfig()

        assert config.base_url == "http://localhost:8123"
        assert config.timeout == 30
        assert config.validate() is True

    def test_config_validation(self):
        """Test configuration validation"""
        valid_config = BankingConfig(base_url="http://test.com", timeout=10)
        assert valid_config.validate() is True

        invalid_config = BankingConfig(base_url="", timeout=-1)
        assert invalid_config.validate() is False


# Integration test marker (skip if API not available)
@pytest.mark.integration
class TestIntegration:
    """Integration tests (requires running API server)"""

    @pytest.mark.skip(reason="Requires live API server")
    def test_real_transfer(self):
        """Test real transfer against live API"""
        client = BankingClient()
        result = client.transfer_funds('ACC1000', 'ACC1001', 10.0)

        assert result is not None
        assert result.status == 'SUCCESS'

    @pytest.mark.skip(reason="Requires live API server")
    def test_real_authentication(self):
        """Test real authentication against live API"""
        client = BankingClient()
        result = client.authenticate('alice', 'password')

        assert result is True
        assert client.jwt_token is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=banking_client', '--cov-report=term-missing'])
