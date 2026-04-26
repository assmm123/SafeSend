# إضافة الدالة مع المسافة الصحيحة
sed -i '$ d' src/services/tron_client.py

cat >> src/services/tron_client.py << 'PATCH'

    # ============================================
    # Compatibility Methods for EscrowEngine
    # ============================================
    
    def check_incoming_transaction(
        self,
        address: str,
        expected_amount: Decimal,
        memo: Optional[str] = None
    ) -> Optional[dict]:
        """
        فحص معاملة واردة - متوافق مع EscrowEngine
        
        Args:
            address: عنوان المستلم
            expected_amount: المبلغ المتوقع
            memo: مذكرة
            
        Returns:
            dict: معلومات المعاملة أو None
        """
        return self.check_usdt_transaction(address, expected_amount, memo)

__all__ = ["TronClient", "TronNetwork"]
PATCH

echo "✅ تم الإصلاح"
# تعديل check_incoming_transaction
sed -i 's/def check_incoming_transaction(self, address: str, expected_amount: Decimal, memo: str = None):/def check_incoming_transaction(self, expected_address: str = None, address: str = None, expected_amount: Decimal = None, memo: str = None):/' src/services/tron_client.py

# إضافة منطق التعامل مع كلا الاسمين
sed -i '/def check_incoming_transaction/a\        addr = expected_address or address' src/services/tron_client.py
sed -i 's/return self.check_usdt_transaction(address, expected_amount, memo)/return self.check_usdt_transaction(addr, expected_amount, memo)/' src/services/tron_client.py
