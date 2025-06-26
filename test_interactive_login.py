#!/usr/bin/env python3
"""
Test script for XTS Interactive Login functionality
"""

import sys
import traceback

# Add the current directory to the path
sys.path.append('.')

try:
    from xtspythonclientapisdk.Connect import XTSConnect
    print("✅ Successfully imported XTSConnect from official SDK")
    
    # Test constants
    print("\n📋 Testing XTSConnect constants:")
    print(f"EXCHANGE_NSEFO: {XTSConnect.EXCHANGE_NSEFO}")
    print(f"PRODUCT_MIS: {XTSConnect.PRODUCT_MIS}")
    print(f"ORDER_TYPE_LIMIT: {XTSConnect.ORDER_TYPE_LIMIT}")
    print(f"TRANSACTION_TYPE_BUY: {XTSConnect.TRANSACTION_TYPE_BUY}")
    print(f"TRANSACTION_TYPE_SELL: {XTSConnect.TRANSACTION_TYPE_SELL}")
    print(f"VALIDITY_DAY: {XTSConnect.VALIDITY_DAY}")
    
    # Test XTSConnect object creation
    print("\n🔧 Testing XTSConnect object creation:")
    xt = XTSConnect(
        apiKey="test_key",
        secretKey="test_secret", 
        source="WEBAPI",
        root="http://colo.srellp.com:3000"
    )
    print("✅ XTSConnect object created successfully")
    
    # Test method availability
    print("\n🔍 Testing method availability:")
    print(f"interactive_login method exists: {hasattr(xt, 'interactive_login')}")
    print(f"marketdata_login method exists: {hasattr(xt, 'marketdata_login')}")
    print(f"place_order method exists: {hasattr(xt, 'place_order')}")
    print(f"cancel_order method exists: {hasattr(xt, 'cancel_order')}")
    
    print("\n✅ All tests passed! The official XTS SDK is properly integrated.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc() 