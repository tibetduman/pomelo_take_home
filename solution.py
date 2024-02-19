"""Solution for Pomelo HackerRank question."""

from __future__ import annotations
import json
from enum import Enum
from typing import Optional


class CreditAccountRecord:
    """Stores credit card transactions for a user."""
    credit_limit: int
    txns: list[CreditCardTransaction]

    def __init__(self, credit_limit: int,
                 txns: list[CreditCardTransaction]) -> None:
        if credit_limit <= 0:
            raise ValueError(f'Invalid credit limit: {credit_limit}')
        txns.sort(key=lambda txn: txn.time)
        self.credit_limit = credit_limit
        self.txns = txns

    def process_account(self) -> CreditAccount:
        """Processes all txns to compute the current account state."""
        return CreditAccount(self)

    @staticmethod
    def from_json(json_dict: dict) -> CreditAccountRecord:
        """Deserializes this class from a JSON formatted dict."""
        return CreditAccountRecord(int(json_dict['creditLimit']), [
            CreditCardTransaction.from_json(txn_json_str)
            for txn_json_str in json_dict['events']
        ])


class TransactionClass(Enum):
    """The higher-level class of a transaction."""
    CREDIT = 1
    PAYMENT = 2


class TransactionType(Enum):
    """The type of transaction."""

    AUTHED = 1
    SETTLED = 2
    AUTH_CLEARED = 3
    PAYMENT_INIT = 4
    PAYMENT_POSTED = 5
    PAYMENT_CANCELED = 6

    def get_class(self) -> TransactionClass:
        """Gets the class of this transaction type."""
        if self in [
                TransactionType.AUTHED, TransactionType.SETTLED,
                TransactionType.AUTH_CLEARED
        ]:
            return TransactionClass.CREDIT
        return TransactionClass.PAYMENT

    @staticmethod
    def parse(json_str: str) -> TransactionType:
        """Parses the transaction type from the given json string."""
        if json_str == 'TXN_AUTHED':
            return TransactionType.AUTHED
        if json_str == 'TXN_SETTLED':
            return TransactionType.SETTLED
        if json_str == 'TXN_AUTH_CLEARED':
            return TransactionType.AUTH_CLEARED
        if json_str == 'PAYMENT_INITIATED':
            return TransactionType.PAYMENT_INIT
        if json_str == 'PAYMENT_POSTED':
            return TransactionType.PAYMENT_POSTED
        if json_str == 'PAYMENT_CANCELED':
            return TransactionType.PAYMENT_CANCELED
        raise ValueError(f'invalid transaction type: {json_str}')


class CreditCardTransaction:
    """Output data format."""
    txn_type: TransactionType
    txn_id: str
    time: int
    amount: Optional[int]
    initial_time: Optional[int]  # only set for settled txn

    def __init__(self, txn_type: TransactionType, txn_id: str, time: int,
                 amount: Optional[int]) -> None:
        self.txn_type = txn_type
        self.txn_id = txn_id
        self.time = time
        self.amount = amount
        self.initial_time = None

    def record_pending_txn(self, pending_txn: CreditCardTransaction):
        """Records the txn which was the precursor to this one."""
        if self.amount is None:
            self.amount = pending_txn.amount
        self.initial_time = pending_txn.time

    def __repr__(self) -> str:
        """A one-line summary for the state of this txn."""
        amount = f'${self.amount}' if self.amount >= 0 else f'-${-self.amount}'
        if self.initial_time is None:
            return f'{self.txn_id}: {amount} @ time {self.time}'
        return f'{self.txn_id}: {amount} @ time {self.initial_time} (finalized @ time {self.time})'

    @staticmethod
    def from_json(json_dict: dict) -> CreditCardTransaction:
        """Deserializes this class from a JSON formatted dict."""
        return CreditCardTransaction(
            TransactionType.parse(json_dict['eventType']), json_dict['txnId'],
            int(json_dict['eventTime']),
            int(json_dict['amount']) if 'amount' in json_dict else None)


class CreditAccount:
    """A live credit account."""
    credit_limit: int
    available_credit: int
    payable_balance: int
    pending_txns: list[CreditCardTransaction]
    settled_txns: list[CreditCardTransaction]

    unprocessed_txns: list[CreditCardTransaction]
    previos_txn_ids: set

    def __init__(self, record: CreditAccountRecord) -> None:
        self.credit_limit = record.credit_limit
        self.available_credit = self.credit_limit
        self.payable_balance = 0
        self.pending_txns = []
        self.settled_txns = []
        self.unprocessed_txns = record.txns
        self.previos_txn_ids = set()

        self._process_txns()

    def get_summary(self) -> CreditAccountSummary:
        """Returns credit account summary model."""
        self.settled_txns.sort(key=lambda txn: txn.time, reverse=True)
        return CreditAccountSummary(self.available_credit,
                                    self.payable_balance, self.pending_txns,
                                    self.settled_txns[0:3])

    def _process_txns(self) -> None:
        while self.unprocessed_txns:
            self._process_txn(self.unprocessed_txns.pop(0))

    def _process_txn(self, txn: CreditCardTransaction) -> None:
        """Processes a single transaction for a credit account."""
        if txn.txn_type == TransactionType.AUTHED:
            self._ensure_txn_id_unique(txn)
            if self.available_credit < txn.amount:
                raise ValueError(
                    f'Transaction cannot be authorized due to insufficient funds: {txn.txn_id}'
                )
            self.available_credit -= txn.amount
            self.pending_txns.append(txn)
        elif txn.txn_type == TransactionType.SETTLED:
            pending_txn = self._find_pending(txn)
            txn.record_pending_txn(pending_txn)
            self.available_credit += pending_txn.amount
            self.available_credit -= txn.amount
            self.payable_balance += txn.amount
            self.pending_txns.remove(pending_txn)
            self.settled_txns.append(txn)
        elif txn.txn_type == TransactionType.AUTH_CLEARED:
            pending_txn = self._find_pending(txn)
            self.available_credit += pending_txn.amount
            self.pending_txns.remove(pending_txn)
        elif txn.txn_type == TransactionType.PAYMENT_INIT:
            self._ensure_txn_id_unique(txn)
            if self.payable_balance < -txn.amount:
                raise ValueError(
                    'Payment transaction not allowed as it is greater '
                    f'than payable amount: {txn.txn_id}')
            self.payable_balance += txn.amount
            self.pending_txns.append(txn)
        elif txn.txn_type == TransactionType.PAYMENT_POSTED:
            pending_txn = self._find_pending(txn)
            txn.record_pending_txn(pending_txn)
            self.available_credit -= pending_txn.amount
            self.pending_txns.remove(pending_txn)
            self.settled_txns.append(txn)
        elif txn.txn_type == TransactionType.PAYMENT_CANCELED:
            pending_txn = self._find_pending(txn)
            self.payable_balance -= pending_txn.amount
            self.pending_txns.remove(pending_txn)

    def _ensure_txn_id_unique(self, txn: CreditCardTransaction) -> None:
        if txn.txn_id in self.previos_txn_ids:
            raise ValueError(f'Repeated transaction id: {txn.txn_id}')
        self.previos_txn_ids.add(txn.txn_id)

    def _find_pending(self,
                      txn: CreditCardTransaction) -> CreditCardTransaction:
        pending_txn = next(
            filter(lambda pending_txn: pending_txn.txn_id == txn.txn_id,
                   self.pending_txns), None)
        if pending_txn is None:
            raise ValueError(
                f'Could not find the pending txn for a settled txn: {txn.txn_id}'
            )
        if pending_txn.txn_type.get_class() != txn.txn_type.get_class():
            raise ValueError(
                f'Class mismatch between settled {pending_txn.txn_id} and pending txn {txn.txn_id}.'
            )
        return pending_txn


class CreditAccountSummary:
    """A summary for the credit account."""

    available_credit: int
    payable_balance: int
    pending_txns: list[CreditCardTransaction]
    recent_settled_txns: list[CreditCardTransaction]

    def __init__(self, available_credit: int, payable_balance: int,
                 pending_txns: list[CreditCardTransaction],
                 recent_settled_txns: list[CreditCardTransaction]) -> None:
        self.available_credit = available_credit
        self.payable_balance = payable_balance
        self.pending_txns = pending_txns
        self.recent_settled_txns = recent_settled_txns

    def __repr__(self) -> str:
        pending_txns = '\n'.join([str(txn) for txn in self.pending_txns])
        pending_txns += '\n' if self.pending_txns else ''
        settled_txns = '\n'.join(
            [str(txn) for txn in self.recent_settled_txns])
        return f'''Available credit: ${self.available_credit}
Payable balance: ${self.payable_balance}

Pending transactions:
{pending_txns}
Settled transactions:
{settled_txns}'''.rstrip('\n')


def summarize(inputJSON: str) -> str:  # pylint: disable=invalid-name
    """
    Get the summary for the current state of the credit account.

    Args:
      inputJSON: The input as a JSON formatted string.

    Returns:
      The account summary string.

    Raises:
        ValueError: If the input is malformed or invalid/illegal.
    """
    json_dict = json.loads(inputJSON)
    return str(
        CreditAccountRecord.from_json(
            json_dict).process_account().get_summary())
