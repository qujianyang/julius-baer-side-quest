#!/usr/bin/env python3

import argparse
import sys
import json
from typing import Optional
from banking_client import BankingClient, BankingConfig
import logging

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class BankingCLI:

    def __init__(self):
        self.parser = self._create_parser()
        self.client = None

    def _create_parser(self):
        parser = argparse.ArgumentParser(
            description='Banking CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument('--url', default='http://localhost:8123', help='API URL')
        parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds')
        parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        parser.add_argument('--json', action='store_true', help='JSON output')

        subparsers = parser.add_subparsers(dest='command')

        # Transfer command
        transfer_parser = subparsers.add_parser(
            'transfer',
            help='Transfer funds between accounts'
        )
        transfer_parser.add_argument(
            '--from', '-f',
            dest='from_account',
            required=True,
            help='Source account ID'
        )
        transfer_parser.add_argument(
            '--to', '-t',
            dest='to_account',
            required=True,
            help='Destination account ID'
        )
        transfer_parser.add_argument(
            '--amount', '-a',
            type=float,
            required=True,
            help='Amount to transfer'
        )
        transfer_parser.add_argument(
            '--auth',
            action='store_true',
            help='Use JWT authentication'
        )
        transfer_parser.add_argument(
            '--username', '-u',
            default='admin',
            help='Username for authentication (default: admin)'
        )
        transfer_parser.add_argument(
            '--password', '-p',
            default='password',
            help='Password for authentication (default: password)'
        )
        transfer_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate accounts before transfer'
        )

        # Validate command
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validate an account'
        )
        validate_parser.add_argument(
            '--account', '-a',
            required=True,
            help='Account ID to validate'
        )

        # Balance command
        balance_parser = subparsers.add_parser(
            'balance',
            help='Get account balance'
        )
        balance_parser.add_argument(
            '--account', '-a',
            required=True,
            help='Account ID to check'
        )

        # List accounts command
        subparsers.add_parser(
            'list-accounts',
            help='List all accounts'
        )

        # Transaction history command
        history_parser = subparsers.add_parser(
            'history',
            help='Get transaction history (requires authentication)'
        )
        history_parser.add_argument(
            '--username', '-u',
            default='admin',
            help='Username for authentication (default: admin)'
        )
        history_parser.add_argument(
            '--password', '-p',
            default='password',
            help='Password for authentication (default: password)'
        )

        # Demo command
        subparsers.add_parser(
            'demo',
            help='Run interactive demo of all features'
        )

        return parser

    def _init_client(self, args) -> BankingClient:
        """Initialize banking client with configuration"""
        if args.verbose:
            logging.getLogger().setLevel(logging.INFO)

        config = BankingConfig(
            base_url=args.url,
            timeout=args.timeout
        )
        return BankingClient(config)

    def _output(self, data: dict, args):
        """Output data in requested format"""
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            # Human-readable output
            for key, value in data.items():
                print(f"{key}: {value}")

    def cmd_transfer(self, args):
        """Handle transfer command"""
        client = self._init_client(args)

        try:
            # Authenticate if requested
            if args.auth:
                if not args.verbose:
                    print(f"Authenticating as {args.username}...")
                if not client.authenticate(args.username, args.password):
                    print("❌ Authentication failed")
                    return 1
                if not args.verbose:
                    print("✓ Authentication successful")

            # Perform transfer
            if not args.verbose:
                print(f"Transferring ${args.amount:.2f} from {args.from_account} to {args.to_account}...")

            result = client.transfer_funds(
                args.from_account,
                args.to_account,
                args.amount,
                validate_accounts=args.validate
            )

            if result and result.status == "SUCCESS":
                output_data = {
                    "status": "SUCCESS",
                    "transaction_id": result.transaction_id,
                    "from_account": result.from_account,
                    "to_account": result.to_account,
                    "amount": result.amount,
                    "message": result.message
                }

                if not args.json:
                    print(f"✓ Transfer successful!")
                    print(f"  Transaction ID: {result.transaction_id}")
                    print(f"  From: {result.from_account}")
                    print(f"  To: {result.to_account}")
                    print(f"  Amount: ${result.amount:.2f}")
                else:
                    self._output(output_data, args)
                return 0
            else:
                print("❌ Transfer failed")
                if result:
                    print(f"  Message: {result.message}")
                return 1

        finally:
            client.close()

    def cmd_validate(self, args):
        """Handle validate command"""
        client = self._init_client(args)

        try:
            is_valid = client.validate_account(args.account)

            output_data = {
                "account": args.account,
                "is_valid": is_valid,
                "status": "VALID" if is_valid else "INVALID"
            }

            if not args.json:
                status_icon = "✓" if is_valid else "❌"
                print(f"{status_icon} Account {args.account} is {'VALID' if is_valid else 'INVALID'}")
            else:
                self._output(output_data, args)

            return 0 if is_valid else 1

        finally:
            client.close()

    def cmd_balance(self, args):
        """Handle balance command"""
        client = self._init_client(args)

        try:
            balance = client.get_account_balance(args.account)

            if balance is not None:
                output_data = {
                    "account": args.account,
                    "balance": balance
                }

                if not args.json:
                    print(f"Account {args.account} balance: ${balance:.2f}")
                else:
                    self._output(output_data, args)
                return 0
            else:
                print(f"❌ Could not retrieve balance for {args.account}")
                return 1

        finally:
            client.close()

    def cmd_list_accounts(self, args):
        """Handle list-accounts command"""
        client = self._init_client(args)

        try:
            accounts = client.get_all_accounts()

            if accounts:
                if args.json:
                    print(json.dumps(accounts, indent=2))
                else:
                    print(f"Found {len(accounts)} accounts:")
                    print("-" * 60)
                    for acc in accounts:
                        print(f"  {acc.get('accountId')}: {acc.get('accountType')} - {acc.get('status')}")
                return 0
            else:
                print("❌ Could not retrieve accounts")
                return 1

        finally:
            client.close()

    def cmd_history(self, args):
        """Handle history command"""
        client = self._init_client(args)

        try:
            # Authenticate
            if not args.verbose:
                print(f"Authenticating as {args.username}...")

            if not client.authenticate(args.username, args.password):
                print("❌ Authentication failed")
                return 1

            # Get history
            history = client.get_transaction_history()

            if history:
                if args.json:
                    print(json.dumps(history, indent=2))
                else:
                    print(f"✓ Found {len(history)} transactions:")
                    print("-" * 60)
                    for txn in history[:10]:  # Show first 10
                        print(f"  {txn.get('transactionId')}: ${txn.get('amount', 0):.2f}")
                return 0
            else:
                print("❌ Could not retrieve transaction history")
                return 1

        finally:
            client.close()

    def cmd_demo(self, args):
        """Run interactive demo"""
        from banking_client import main as demo_main
        demo_main()
        return 0

    def run(self, argv=None):
        """Run the CLI"""
        args = self.parser.parse_args(argv)

        if not args.command:
            self.parser.print_help()
            return 0

        # Dispatch to command handler
        command_method = getattr(self, f'cmd_{args.command.replace("-", "_")}', None)
        if command_method:
            try:
                return command_method(args)
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user")
                return 130
            except Exception as e:
                logger.exception("Command failed")
                print(f"❌ Error: {str(e)}")
                return 1
        else:
            print(f"Unknown command: {args.command}")
            return 1


def main():
    """Main entry point"""
    cli = BankingCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
