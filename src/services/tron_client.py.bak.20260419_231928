"""
عميل TronGrid متقدم
Advanced TronGrid Client

خفيف، مع Redis Cache، ودعم Async (اختياري)
يعمل بدون tronpy على Termux
"""

import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any, List

import requests

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

from src.app.models.helpers import utc_now
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


class TronNetwork:
    MAINNET = "mainnet"
    SHASTA = "shasta"
    NILE = "nile"


@dataclass
class TransactionVerification:
    """نتيجة التحقق من معاملة - متوافق مع EscrowEngine"""
    tx_hash: Optional[str] = None
    amount: Decimal = Decimal("0")
    expected_amount: Decimal = Decimal("0")
    confirmations: int = 0
    is_confirmed: bool = False
    is_sufficient: bool = False
    verified: bool = False
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    error: Optional[str] = None
    
    def get(self, key: str, default=None):
        """للتوافق مع dict"""
        return getattr(self, key, default)
    
    def __getitem__(self, key: str):
        """للتوافق مع dict"""
        return getattr(self, key)


class TronClient:
    """
    عميل TronGrid متقدم
    يدعم Redis Cache و Async (اختياري)
    """
    
    API_URLS = {
        TronNetwork.MAINNET: "https://api.trongrid.io",
        TronNetwork.SHASTA: "https://api.shasta.trongrid.io",
        TronNetwork.NILE: "https://nile.trongrid.io",
    }
    
    USDT_CONTRACT = {
        TronNetwork.MAINNET: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        TronNetwork.SHASTA: "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs",
        TronNetwork.NILE: "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
    }
    
    DECIMALS = 10 ** 6
    CACHE_TTL = 60
    
    def __init__(self, network: str = TronNetwork.SHASTA, api_key: str = None, circuit_breaker = None, redis_client = None):
        self.network = network
        self.api_key = api_key
        self.base_url = self.API_URLS[network]
        self.usdt_contract = self.USDT_CONTRACT[network]
        self.redis = redis_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name=f"tron_client_{network}", failure_threshold=3, timeout=30.0)
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        if api_key:
            self.session.headers["TRON-PRO-API-KEY"] = api_key
        logger.info(f"TronClient initialized: network={network}")
    
    def _cache_get(self, key: str):
        if self.redis:
            return self.redis.get(key)
        return None
    
    def _cache_set(self, key: str, value: str, ttl: int = CACHE_TTL):
        if self.redis:
            self.redis.setex(key, ttl, value)
    
    def _cache_key(self, prefix: str, identifier: str) -> str:
        return f"tron:{self.network}:{prefix}:{identifier}"
    
    def _request(self, endpoint: str, params: dict = None) -> dict:
        def _do():
            resp = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        try:
            return self.circuit_breaker.call(_do)
        except:
            return {}
    
    def get_account_info(self, address: str) -> dict:
        return self._request(f"/v1/accounts/{address}")
    
    def get_usdt_balance(self, address: str, use_cache: bool = True) -> Decimal:
        if use_cache:
            cached = self._cache_get(self._cache_key("balance", address))
            if cached:
                return Decimal(cached)
        data = self._request(f"/v1/accounts/{address}/transactions/trc20")
        balance = Decimal(0)
        for token in data.get("data", []):
            if token.get("token_info", {}).get("address") == self.usdt_contract:
                balance = Decimal(int(token.get("balance", 0))) / Decimal(self.DECIMALS)
                break
        if use_cache:
            self._cache_set(self._cache_key("balance", address), str(balance))
        return balance
    
    def get_trx_balance(self, address: str) -> Decimal:
        data = self.get_account_info(address)
        return Decimal(data.get("balance", 0)) / Decimal(10 ** 6)
    
    def get_transactions(self, address: str, limit: int = 50) -> List[dict]:
        data = self._request(f"/v1/accounts/{address}/transactions", {"limit": limit})
        return data.get("data", [])
    
    def check_usdt_transaction(self, address: str, expected_amount: Decimal, memo: str = None) -> Optional[TransactionVerification]:
        """فحص معاملة USDT - يرجع TransactionVerification"""
        txs = self.get_transactions(address, 50)
        expected_sun = int(expected_amount * Decimal(self.DECIMALS))
        
        for tx in txs:
            contract = tx.get("raw_data", {}).get("contract", [{}])[0]
            if contract.get("type") != "TriggerSmartContract":
                continue
            param = contract.get("parameter", {}).get("value", {})
            amount_sun = param.get("amount", 0)
            
            if amount_sun < expected_sun:
                continue
            
            confirmations = tx.get("confirmations", 0)
            amount = Decimal(amount_sun) / Decimal(self.DECIMALS)
            is_confirmed = confirmations >= 20
            is_sufficient = amount >= expected_amount
            
            return TransactionVerification(
                tx_hash=tx["txID"],
                amount=amount,
                expected_amount=expected_amount,
                confirmations=confirmations,
                is_confirmed=is_confirmed,
                is_sufficient=is_sufficient,
                verified=is_confirmed and is_sufficient,
                from_address=param.get("owner_address"),
                to_address=param.get("to_address"),
            )
        
        return None
    
    def check_incoming_transaction(self, expected_address: str = None, address: str = None, expected_amount: Decimal = None, memo: str = None) -> Optional[TransactionVerification]:
        """متوافق مع EscrowEngine"""
        addr = expected_address or address
        return self.check_usdt_transaction(addr, expected_amount, memo)
    
    def get_latest_block(self) -> int:
        data = self._request("/v1/blocks/latest")
        return data.get("block_header", {}).get("raw_data", {}).get("number", 0)
    
    def health_check(self) -> dict:
        try:
            block = self.get_latest_block()
            status = "healthy" if block >= 0 else "degraded"
        except:
            status = "unhealthy"
            block = 0
        return {
            "status": status,
            "network": self.network,
            "latest_block": block,
            "circuit_breaker": self.circuit_breaker.state.value,
            "cache_enabled": self.redis is not None,
            "async_available": AIOHTTP_AVAILABLE,
        }
    
    def get_metrics(self) -> dict:
        return {
            "network": self.network,
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "cache_enabled": self.redis is not None,
        }
    
    def invalidate_cache(self, address: str):
        if self.redis:
            self.redis.delete(self._cache_key("balance", address))


__all__ = ["TronClient", "TronNetwork", "TransactionVerification"]
