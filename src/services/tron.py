"""
خدمة TRON Blockchain
TRON Blockchain Service

تكامل حقيقي مع TRON لدعم USDT (TRC-20)
- توليد عناوين إيداع
- فحص المعاملات الواردة
- إرسال المدفوعات
- حساب الطاقة والرسوم
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import requests

from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.app.models.helpers import utc_now, mask_string
from src.app.models.logging_config import get_logger
from src.app.models.security import constant_time_compare, decrypt_data

logger = get_logger(__name__)


# ============================================
# الثوابت - Constants
# ============================================

class TronNetwork:
    MAINNET = "mainnet"
    SHASTA = "shasta"
    NILE = "nile"


# عناوين العقود
TOKEN_CONTRACTS = {
    TronNetwork.MAINNET: {
        "USDT": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "USDC": "TEkxiTehnzSmSe2XqrBjxwW2bRRxwR2XZ2",
        "TUSD": "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4",
    },
    TronNetwork.SHASTA: {
        "USDT": "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs",
    },
    TronNetwork.NILE: {
        "USDT": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
    }
}

# عقد API
TRON_API_NODES = {
    TronNetwork.MAINNET: [
        "https://api.trongrid.io",
        "https://api.tronstack.io",
    ],
    TronNetwork.SHASTA: [
        "https://api.shasta.trongrid.io",
    ],
    TronNetwork.NILE: [
        "https://nile.trongrid.io",
    ]
}

# ثوابت المعاملات
USDT_DECIMALS = 6
TRX_DECIMALS = 6
MIN_CONFIRMATIONS = 20
ENERGY_PER_USDT_TRANSFER = 13000
ENERGY_PER_NEW_ADDRESS = 30000
BANDWIDTH_PER_TRANSFER = 250
ENERGY_FEE_LIMIT = 100_000_000  # 100 TRX maximum fee


# ============================================
# Data Classes
# ============================================

@dataclass
class PaymentAddress:
    """عنوان دفع"""
    address: str
    memo: str
    qr_code: str
    network: str
    expires_at: str


@dataclass
class TransactionVerification:
    """نتيجة التحقق من معاملة"""
    tx_hash: str
    amount: Decimal
    from_address: str
    to_address: str
    confirmations: int
    is_confirmed: bool
    is_sufficient: bool
    expected_amount: Decimal
    block_number: int
    timestamp: str


@dataclass
class PayoutResult:
    """نتيجة إرسال دفعة"""
    success: bool
    tx_hash: Optional[str]
    amount: Decimal
    to_address: str
    fee_trx: Decimal
    idempotency_key: str
    error: Optional[str] = None
    block_explorer_url: Optional[str] = None


@dataclass
class HealthStatus:
    """حالة صحة الخدمة"""
    status: str  # healthy, degraded, unhealthy
    network: str
    api_connected: bool
    wallet_balance: float
    current_node: str
    circuit_breaker_state: str
    pending_transactions: int = 0


@dataclass
class EnergyEstimation:
    """تقدير الطاقة"""
    energy_needed: int
    energy_price_sun: int
    bandwidth_needed: int
    bandwidth_price_sun: int
    total_fee_sun: int
    total_fee_trx: Decimal
    is_new_address: bool


# ============================================
# Exceptions
# ============================================

class TronServiceError(Exception):
    """خطأ أساسي في خدمة TRON"""
    pass


class InsufficientFundsError(TronServiceError):
    """رصيد غير كاف"""
    pass


class TransactionNotFoundError(TronServiceError):
    """المعاملة غير موجودة"""
    pass


class InvalidAddressError(TronServiceError):
    """عنوان غير صالح"""
    pass


# ============================================
# TronService
# ============================================

class TronService:
    """
    خدمة TRON Blockchain
    TronService
    
    تتعامل مع USDT TRC-20 على شبكة TRON
    تدعم Circuit Breaker و Idempotency و Retry
    """
    
    def __init__(
        self,
        network: str = TronNetwork.MAINNET,
        api_key: Optional[str] = None,
        encrypted_private_key: Optional[str] = None,
        encryption_key: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        usdt_contract: Optional[str] = None,
        min_confirmations: int = MIN_CONFIRMATIONS
    ):
        """
        تهيئة خدمة TRON
        
        Args:
            network: mainnet, shasta, nile
            api_key: TronGrid API Key
            encrypted_private_key: مفتاح خاص مشفر (لإرسال المدفوعات)
            encryption_key: مفتاح فك التشفير
            circuit_breaker: CircuitBreaker للحماية
            usdt_contract: عنوان عقد USDT (اختياري)
            min_confirmations: عدد التأكيدات المطلوبة
        """
        self.network = network
        self.api_key = api_key
        self.min_confirmations = min_confirmations
        
        # Circuit Breaker
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name=f"tron_{network}",
            failure_threshold=5,
            timeout=60.0
        )
        
        # عنوان عقد USDT
        if usdt_contract:
            self.usdt_contract = usdt_contract
        else:
            self.usdt_contract = TOKEN_CONTRACTS[network]["USDT"]
        
        # فك تشفير المفتاح الخاص
        self._private_key: Optional[str] = None
        if encrypted_private_key and encryption_key:
            self._private_key = decrypt_data(encrypted_private_key, encryption_key)
        elif encrypted_private_key:
            self._private_key = decrypt_data(encrypted_private_key)
        
        # عقد API
        self._api_nodes = TRON_API_NODES[network]
        self._current_node_index = 0
        self._current_node = self._api_nodes[0]
        
        # تتبع المعاملات المعلقة
        self._pending_transactions: Dict[str, dict] = {}
        
        # جلسة HTTP
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        if api_key:
            self._session.headers["TRON-PRO-API-KEY"] = api_key
        
        logger.info(f"TronService initialized: network={network}, node={self._current_node}")
    
    # ============================================
    # إدارة العقد
    # ============================================
    
    def _switch_node(self) -> None:
        """التبديل إلى عقدة API أخرى"""
        self._current_node_index = (self._current_node_index + 1) % len(self._api_nodes)
        self._current_node = self._api_nodes[self._current_node_index]
        logger.warning(f"Switched to node: {self._current_node}")
    
    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """
        إجراء طلب API مع Circuit Breaker و Retry
        
        Args:
            endpoint: مسار API
            params: معاملات الطلب
            
        Returns:
            dict: استجابة API
        """
        def _do_request():
            url = f"{self._current_node}{endpoint}"
            try:
                response = self._session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
                self._switch_node()
                raise
        
        try:
            return self.circuit_breaker.call(_do_request)
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker is OPEN")
            raise TronServiceError("Service temporarily unavailable")
    
    def _make_post_request(self, endpoint: str, data: dict) -> dict:
        """إجراء طلب POST مع Circuit Breaker"""
        def _do_request():
            url = f"{self._current_node}{endpoint}"
            try:
                response = self._session.post(url, json=data, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"API POST request failed: {e}")
                self._switch_node()
                raise
        
        try:
            return self.circuit_breaker.call(_do_request)
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker is OPEN")
            raise TronServiceError("Service temporarily unavailable")
    
    # ============================================
    # دوال العناوين
    # ============================================
    
    def generate_payment_address(self, deal_id: str) -> PaymentAddress:
        """
        توليد عنوان دفع فريد للصفقة
        
        Args:
            deal_id: معرف الصفقة
            
        Returns:
            PaymentAddress: عنوان الدفع مع memo
        """
        if not self._private_key:
            # في حالة عدم وجود مفتاح خاص، نستخدم عنوان المحفظة الأساسي
            from tronpy import Tron
            client = Tron(network=self.network)
            address = client.generate_address()
            memo = hashlib.sha256(f"{deal_id}:{utc_now().timestamp()}".encode()).hexdigest()[:16]
        else:
            from tronpy import Tron
            from tronpy.keys import PrivateKey
            client = Tron(network=self.network)
            priv_key = PrivateKey(bytes.fromhex(self._private_key))
            address = priv_key.public_key.to_base58check_address()
            memo = deal_id[:16] if len(deal_id) >= 16 else deal_id
        
        # إنشاء QR Code
        qr_data = f"tron:{address}?memo={memo}"
        
        expires_at = (utc_now() + time.timedelta(hours=24)).isoformat()
        
        logger.info(f"Generated payment address for deal {deal_id}: {self._mask_address(address)}")
        
        return PaymentAddress(
            address=address,
            memo=memo,
            qr_code=qr_data,
            network=self.network,
            expires_at=expires_at
        )
    
    def _mask_address(self, address: str) -> str:
        """إخفاء العنوان للسجلات"""
        if len(address) < 10:
            return "***"
        return address[:6] + "..." + address[-4:]
    
    def validate_address(self, address: str) -> bool:
        """التحقق من صحة عنوان TRON"""
        try:
            from tronpy.keys import is_base58check_address
            return is_base58check_address(address)
        except ImportError:
            # تحقق بسيط
            return address.startswith('T') and len(address) == 34
    
    # ============================================
    # دوال الرصيد
    # ============================================
    
    def get_wallet_balance(self, address: Optional[str] = None) -> Decimal:
        """
        الحصول على رصيد USDT
        
        Args:
            address: العنوان (يستخدم عنوان المحفظة إذا لم يحدد)
            
        Returns:
            Decimal: الرصيد بـ USDT
        """
        if address is None:
            if not self._private_key:
                return Decimal(0)
            from tronpy.keys import PrivateKey
            priv_key = PrivateKey(bytes.fromhex(self._private_key))
            address = priv_key.public_key.to_base58check_address()
        
        # استدعاء عقد USDT
        endpoint = "/v1/accounts/" + address + "/transactions/trc20"
        try:
            response = self._make_request(endpoint)
            # البحث عن USDT
            for token in response.get("trc20token_balances", []):
                if token.get("tokenId") == self.usdt_contract:
                    balance_sun = int(token.get("balance", 0))
                    return Decimal(balance_sun) / Decimal(10 ** USDT_DECIMALS)
            return Decimal(0)
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return Decimal(0)
    
    def get_trx_balance(self, address: Optional[str] = None) -> Decimal:
        """الحصول على رصيد TRX"""
        if address is None:
            if not self._private_key:
                return Decimal(0)
            from tronpy.keys import PrivateKey
            priv_key = PrivateKey(bytes.fromhex(self._private_key))
            address = priv_key.public_key.to_base58check_address()
        
        endpoint = f"/v1/accounts/{address}"
        try:
            response = self._make_request(endpoint)
            balance_sun = response.get("balance", 0)
            return Decimal(balance_sun) / Decimal(10 ** TRX_DECIMALS)
        except Exception as e:
            logger.error(f"Failed to get TRX balance: {e}")
            return Decimal(0)
    
    # ============================================
    # دوال المعاملات الواردة
    # ============================================
    
    def check_incoming_transaction(
        self,
        expected_address: str,
        expected_amount: Decimal,
        memo: Optional[str] = None
    ) -> Optional[TransactionVerification]:
        """
        فحص وجود معاملة واردة
        
        Args:
            expected_address: العنوان المتوقع
            expected_amount: المبلغ المتوقع
            memo: المذكرة المتوقعة
            
        Returns:
            TransactionVerification أو None
        """
        endpoint = f"/v1/accounts/{expected_address}/transactions"
        params = {
            "limit": 50,
            "only_confirmed": "true",
            "min_timestamp": int((utc_now() - time.timedelta(hours=24)).timestamp() * 1000)
        }
        
        try:
            response = self._make_request(endpoint, params)
            
            for tx in response.get("data", []):
                # التحقق من USDT
                if tx.get("tokenId") != self.usdt_contract:
                    continue
                
                tx_amount = Decimal(tx.get("value", 0)) / Decimal(10 ** USDT_DECIMALS)
                
                # التحقق من المبلغ
                if tx_amount < expected_amount:
                    continue
                
                # التحقق من memo
                tx_memo = tx.get("memo", "")
                if memo and tx_memo != memo:
                    continue
                
                # عدد التأكيدات
                confirmations = self._get_transaction_confirmations(tx["transaction_id"])
                
                return TransactionVerification(
                    tx_hash=tx["transaction_id"],
                    amount=tx_amount,
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    confirmations=confirmations,
                    is_confirmed=confirmations >= self.min_confirmations,
                    is_sufficient=tx_amount >= expected_amount,
                    expected_amount=expected_amount,
                    block_number=tx.get("blockNumber", 0),
                    timestamp=tx.get("timestamp", "")
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check incoming transaction: {e}")
            return None
    
    def _get_transaction_confirmations(self, tx_hash: str) -> int:
        """الحصول على عدد تأكيدات المعاملة"""
        endpoint = f"/v1/transactions/{tx_hash}"
        try:
            response = self._make_request(endpoint)
            current_block = self._get_current_block()
            tx_block = response.get("blockNumber", 0)
            if tx_block > 0:
                return current_block - tx_block
            return 0
        except Exception:
            return 0
    
    def _get_current_block(self) -> int:
        """الحصول على رقم الكتلة الحالية"""
        endpoint = "/v1/blocks/latest/number"
        try:
            response = self._make_request(endpoint)
            return response.get("number", 0)
        except Exception:
            return 0
    
    # ============================================
    # دوال المعاملات الصادرة
    # ============================================
    
    def estimate_energy(self, to_address: str, amount: Decimal) -> EnergyEstimation:
        """
        تقدير الطاقة المطلوبة للمعاملة
        
        Args:
            to_address: العنوان المستلم
            amount: المبلغ
            
        Returns:
            EnergyEstimation: تقدير الطاقة والرسوم
        """
        # التحقق مما إذا كان العنوان جديداً
        is_new_address = not self._is_address_active(to_address)
        energy_needed = ENERGY_PER_NEW_ADDRESS if is_new_address else ENERGY_PER_USDT_TRANSFER
        
        # أسعار السوق (يمكن جلبها من API)
        energy_price_sun = self._get_energy_price()
        bandwidth_price_sun = self._get_bandwidth_price()
        bandwidth_needed = BANDWIDTH_PER_TRANSFER
        
        total_fee_sun = (energy_needed * energy_price_sun) + (bandwidth_needed * bandwidth_price_sun)
        total_fee_trx = Decimal(total_fee_sun) / Decimal(10 ** TRX_DECIMALS)
        
        return EnergyEstimation(
            energy_needed=energy_needed,
            energy_price_sun=energy_price_sun,
            bandwidth_needed=bandwidth_needed,
            bandwidth_price_sun=bandwidth_price_sun,
            total_fee_sun=total_fee_sun,
            total_fee_trx=total_fee_trx,
            is_new_address=is_new_address
        )
    
    def _is_address_active(self, address: str) -> bool:
        """التحقق مما إذا كان العنوان نشطاً"""
        endpoint = f"/v1/accounts/{address}"
        try:
            self._make_request(endpoint)
            return True
        except Exception:
            return False
    
    def _get_energy_price(self) -> int:
        """الحصول على سعر الطاقة (SUN)"""
        # سعر تقريبي - يمكن استخدام oracle
        return 420  # ~420 SUN per energy unit
    
    def _get_bandwidth_price(self) -> int:
        """الحصول على سعر bandwidth"""
        return 1000  # ~1000 SUN per bandwidth
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(TronServiceError)
    )
    def send_payout(
        self,
        to_address: str,
        amount: Decimal,
        idempotency_key: str,
        max_fee_trx: Decimal = Decimal("10")
    ) -> PayoutResult:
        """
        إرسال USDT
        
        Args:
            to_address: العنوان المستلم
            amount: المبلغ بـ USDT
            idempotency_key: مفتاح منع التكرار
            max_fee_trx: الحد الأقصى للرسوم
            
        Returns:
            PayoutResult: نتيجة الإرسال
        """
        if not self._private_key:
            return PayoutResult(
                success=False,
                tx_hash=None,
                amount=amount,
                to_address=to_address,
                fee_trx=Decimal(0),
                idempotency_key=idempotency_key,
                error="Private key not configured"
            )
        
        # التحقق من الرصيد
        balance = self.get_wallet_balance()
        if balance < amount:
            raise InsufficientFundsError(
                f"Insufficient USDT balance: {balance} < {amount}"
            )
        
        # التحقق من TRX للرسوم
        trx_balance = self.get_trx_balance()
        estimation = self.estimate_energy(to_address, amount)
        if trx_balance < estimation.total_fee_trx:
            raise InsufficientFundsError(
                f"Insufficient TRX for fees: {trx_balance} < {estimation.total_fee_trx}"
            )
        
        # التحقق من العنوان
        if not self.validate_address(to_address):
            raise InvalidAddressError(f"Invalid TRON address: {to_address}")
        
        try:
            from tronpy import Tron
            from tronpy.keys import PrivateKey
            from tronpy.providers import HTTPProvider
            
            client = Tron(
                provider=HTTPProvider(self._current_node, api_key=self.api_key),
                network=self.network
            )
            priv_key = PrivateKey(bytes.fromhex(self._private_key))
            
            # الحصول على عقد USDT
            contract = client.get_contract(self.usdt_contract)
            
            # تحويل المبلغ إلى SUN
            amount_sun = int(amount * Decimal(10 ** USDT_DECIMALS))
            
            # بناء المعاملة
            tx = (
                contract.functions.transfer(to_address, amount_sun)
                .with_owner(priv_key.public_key.to_base58check_address())
                .fee_limit(ENERGY_FEE_LIMIT)
                .build()
            )
            
            # توقيع وإرسال
            signed_tx = tx.sign(priv_key)
            result = signed_tx.broadcast()
            
            if result.get("result"):
                tx_hash = result.get("txid")
                
                # تسجيل المعاملة المعلقة
                self._pending_transactions[tx_hash] = {
                    "to_address": to_address,
                    "amount": amount,
                    "idempotency_key": idempotency_key,
                    "created_at": utc_now().isoformat()
                }
                
                logger.info(
                    f"Payout sent: {amount} USDT to {self._mask_address(to_address)}, "
                    f"tx={tx_hash}, idempotency={idempotency_key}"
                )
                
                return PayoutResult(
                    success=True,
                    tx_hash=tx_hash,
                    amount=amount,
                    to_address=to_address,
                    fee_trx=estimation.total_fee_trx,
                    idempotency_key=idempotency_key,
                    block_explorer_url=f"https://tronscan.org/#/transaction/{tx_hash}"
                )
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Payout failed: {error_msg}")
                return PayoutResult(
                    success=False,
                    tx_hash=None,
                    amount=amount,
                    to_address=to_address,
                    fee_trx=estimation.total_fee_trx,
                    idempotency_key=idempotency_key,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Payout exception: {e}")
            raise TronServiceError(f"Payout failed: {e}")
    
    def verify_transaction(self, tx_hash: str) -> Optional[TransactionVerification]:
        """
        التحقق من حالة معاملة
        
        Args:
            tx_hash: تجزئة المعاملة
            
        Returns:
            TransactionVerification أو None
        """
        endpoint = f"/v1/transactions/{tx_hash}"
        try:
            response = self._make_request(endpoint)
            
            # استخراج معلومات USDT
            amount = Decimal(0)
            for log in response.get("log", []):
                if log.get("address") == self.usdt_contract:
                    # فك تشفير البيانات
                    amount = Decimal(log.get("data", "0")) / Decimal(10 ** USDT_DECIMALS)
            
            confirmations = self._get_transaction_confirmations(tx_hash)
            
            return TransactionVerification(
                tx_hash=tx_hash,
                amount=amount,
                from_address=response.get("from", ""),
                to_address=response.get("to", ""),
                confirmations=confirmations,
                is_confirmed=confirmations >= self.min_confirmations,
                is_sufficient=True,
                expected_amount=amount,
                block_number=response.get("blockNumber", 0),
                timestamp=response.get("timestamp", "")
            )
            
        except Exception as e:
            logger.error(f"Failed to verify transaction {tx_hash}: {e}")
            return None
    
    # ============================================
    # دوال الصحة والمراقبة
    # ============================================
    
    def health_check(self) -> HealthStatus:
        """
        فحص صحة الخدمة
        
        Returns:
            HealthStatus: حالة الخدمة
        """
        api_connected = False
        wallet_balance = 0.0
        
        try:
            self._make_request("/v1/blocks/latest/number")
            api_connected = True
        except Exception:
            pass
        
        try:
            wallet_balance = float(self.get_wallet_balance())
        except Exception:
            pass
        
        # تحديد الحالة
        if not api_connected:
            status = "unhealthy"
        elif wallet_balance < 100:  # أقل من 100 USDT
            status = "degraded"
        elif self.circuit_breaker.state.value == "open":
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthStatus(
            status=status,
            network=self.network,
            api_connected=api_connected,
            wallet_balance=wallet_balance,
            current_node=self._current_node,
            circuit_breaker_state=self.circuit_breaker.state.value,
            pending_transactions=len(self._pending_transactions)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الخدمة
        
        Returns:
            Dict: إحصائيات Prometheus
        """
        return {
            "network": self.network,
            "current_node": self._current_node,
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "pending_transactions": len(self._pending_transactions),
            "wallet_balance": float(self.get_wallet_balance()),
            "trx_balance": float(self.get_trx_balance()),
            "usdt_contract": self.usdt_contract,
        }
    
    def test_connection(self) -> bool:
        """اختبار الاتصال بالشبكة"""
        try:
            self._make_request("/v1/blocks/latest/number")
            return True
        except Exception:
            return False
    
    def __repr__(self) -> str:
        return f"<TronService network={self.network} node={self._current_node}>"


__all__ = [
    "TronService",
    "TronNetwork",
    "PaymentAddress",
    "TransactionVerification",
    "PayoutResult",
    "HealthStatus",
    "EnergyEstimation",
    "TronServiceError",
    "InsufficientFundsError",
    "TransactionNotFoundError",
    "InvalidAddressError",
]
