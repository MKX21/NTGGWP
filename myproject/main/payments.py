"""
金流閘道抽象層（Payment Gateway Abstraction）
------------------------------------------------
目前為「模擬金流」實作，不連任何外部服務。
未來要串接真正金流（綠界 ECPay / TapPay / Stripe 等）時，
只需新增一個實作 BaseGateway 介面的類別，並替換最底下的 `gateway`，
views 與 templates 幾乎不需改動。

介面約定：
- create_atm(payment)          建立 ATM 虛擬帳號（回傳已填欄位的 payment）
- create_cvs(payment)          建立超商繳費代碼
- charge_credit_card(payment)  信用卡即時請款 → 回傳 PaymentResult
- confirm_offline(payment)     使用者回報已完成 ATM/超商繳費 → 回傳 PaymentResult
"""
import random
from datetime import timedelta

from django.utils import timezone


class PaymentResult:
    def __init__(self, success, message='', transaction_no=''):
        self.success = success
        self.message = message
        self.transaction_no = transaction_no


class BaseGateway:
    """所有金流閘道的共同介面（未來真金流實作它即可）。"""
    def create_atm(self, payment):
        raise NotImplementedError

    def create_cvs(self, payment):
        raise NotImplementedError

    def charge_credit_card(self, payment, card):
        raise NotImplementedError

    def confirm_offline(self, payment):
        raise NotImplementedError


class MockGateway(BaseGateway):
    """模擬金流：本地產生假帳號／代碼並模擬付款結果，供開發與展示使用。"""

    def _trade_no(self, prefix):
        return f'{prefix}{timezone.now():%Y%m%d}{random.randint(100000, 999999)}'

    def create_atm(self, payment):
        # 真金流：改為呼叫 gateway API 建立虛擬帳號，將回傳值填入下列欄位
        payment.method = 'atm'
        payment.status = 'pending'
        payment.virtual_account = ''.join(random.choice('0123456789') for _ in range(14))
        payment.expire_at = timezone.now() + timedelta(days=3)
        payment.transaction_no = self._trade_no('ATM')
        payment.save()
        return payment

    def create_cvs(self, payment):
        # 真金流：改為呼叫 gateway API 取得超商繳費代碼
        payment.method = 'cvs'
        payment.status = 'pending'
        payment.payment_code = ''.join(random.choice('0123456789') for _ in range(14))
        payment.expire_at = timezone.now() + timedelta(days=7)
        payment.transaction_no = self._trade_no('CVS')
        payment.save()
        return payment

    def charge_credit_card(self, payment, card):
        # 真金流：改為把前端取得的 card token 送至 gateway 請款
        number = (card.get('number') or '').replace(' ', '')
        if not (number.isdigit() and 13 <= len(number) <= 19):
            return PaymentResult(False, '卡號格式不正確（請輸入 13–19 位數字）')
        if not card.get('expiry') or not card.get('cvc'):
            return PaymentResult(False, '請完整填寫有效期限與安全碼')
        # 模擬：卡號結尾為 0000 → 模擬「發卡行拒絕」，方便測試失敗流程
        if number.endswith('0000'):
            return PaymentResult(False, '發卡行拒絕交易（模擬失敗，可換一張卡）')
        payment.method = 'credit_card'
        payment.transaction_no = self._trade_no('CARD')
        return PaymentResult(True, '信用卡付款成功', payment.transaction_no)

    def confirm_offline(self, payment):
        # 模擬：使用者按下「我已完成轉帳／繳費」→ 視同銀行/超商回拋付款成功
        tno = payment.transaction_no or self._trade_no('OFF')
        return PaymentResult(True, '已收到款項（模擬）', tno)


# 目前啟用的金流閘道；未來換成真金流只需改這一行，例如：gateway = EcpayGateway()
gateway = MockGateway()
