import random
from datetime import timedelta

from django.utils import timezone

class PaymentResult:
    def __init__(self, success, message='', transaction_no=''):
        self.success = success
        self.message = message
        self.transaction_no = transaction_no

class BaseGateway:
    def create_atm(self, payment):
        raise NotImplementedError

    def create_cvs(self, payment):
        raise NotImplementedError

    def charge_credit_card(self, payment, card):
        raise NotImplementedError

    def confirm_offline(self, payment):
        raise NotImplementedError

class MockGateway(BaseGateway):

    def _trade_no(self, prefix):
        return f'{prefix}{timezone.now():%Y%m%d}{random.randint(100000, 999999)}'

    def create_atm(self, payment):
        payment.method = 'atm'
        payment.status = 'pending'
        payment.virtual_account = ''.join(random.choice('0123456789') for _ in range(14))
        payment.expire_at = timezone.now() + timedelta(days=3)
        payment.transaction_no = self._trade_no('ATM')
        payment.save()
        return payment

    def create_cvs(self, payment):
        payment.method = 'cvs'
        payment.status = 'pending'
        payment.payment_code = ''.join(random.choice('0123456789') for _ in range(14))
        payment.expire_at = timezone.now() + timedelta(days=7)
        payment.transaction_no = self._trade_no('CVS')
        payment.save()
        return payment

    def charge_credit_card(self, payment, card):
        number = (card.get('number') or '').replace(' ', '')
        if not (number.isdigit() and 13 <= len(number) <= 19):
            return PaymentResult(False, '卡號格式不正確（請輸入 13–19 位數字）')
        if not card.get('expiry') or not card.get('cvc'):
            return PaymentResult(False, '請完整填寫有效期限與安全碼')
        if number.endswith('0000'):
            return PaymentResult(False, '發卡行拒絕交易（模擬失敗，可換一張卡）')
        payment.method = 'credit_card'
        payment.transaction_no = self._trade_no('CARD')
        return PaymentResult(True, '信用卡付款成功', payment.transaction_no)

    def confirm_offline(self, payment):
        tno = payment.transaction_no or self._trade_no('OFF')
        return PaymentResult(True, '已收到款項（模擬）', tno)

gateway = MockGateway()
