#!/usr/bin/env python3
"""
Test script to verify the optimized flow:
1. Fetch Future LTPs and calculate strike ranges
2. Fetch ALL option instrument IDs (individual calls)
3. Fetch ALL option LTPs in batches
4. Select strikes based on criteria
"""

import sys
import os

# Add the current directory to Python path
sys.path.append('.')

from main import (
    login_marketdata_api, 
    get_user_settings, 
    set_marketdata_connection,
    main_strategy,
    get_result_dict
)

def test_optimized_flow():
    print("=" * 60)
    print("TESTING OPTIMIZED FLOW")
    print("=" * 60)
    
    try:
        # Step 1: Login to Market Data API
        print("\n[STEP 1] Logging into Market Data API...")
        xts_marketdata = login_marketdata_api()
        if not xts_marketdata:
            print("❌ Failed to login to Market Data API")
            return False
        
        print("✅ Market Data API login successful")
        set_marketdata_connection(xts_marketdata)
        
        # Step 2: Load user settings
        print("\n[STEP 2] Loading user settings...")
        get_user_settings()
        result_dict = get_result_dict()
        
        if not result_dict:
            print("❌ No symbols found in TradeSettings.csv")
            return False
        
        print(f"✅ Loaded {len(result_dict)} symbols from TradeSettings.csv")
        
        # Step 3: Run the optimized main strategy
        print("\n[STEP 3] Running optimized main strategy...")
        main_strategy()
        
        # Step 4: Verify results
        print("\n[STEP 4] Verifying results...")
        result_dict = get_result_dict()
        
        success_count = 0
        for unique_key, params in result_dict.items():
            symbol = params.get("Symbol")
            fut_ltp = params.get("Futltp")
            optionchain = params.get("Optionchain")
            selected_ce = params.get("optionselectedstrike_CE")
            selected_pe = params.get("optionselectedstrike_PE")
            
            print(f"\n📊 {symbol}:")
            print(f"   Future LTP: {fut_ltp}")
            print(f"   Optionchain strikes: {len(optionchain) if optionchain else 0}")
            
            if optionchain:
                # Check if instrument IDs were fetched
                instrument_ids_fetched = sum(1 for strike_data in optionchain.values() 
                                           if strike_data.get("instrument_id") is not None)
                print(f"   Instrument IDs fetched: {instrument_ids_fetched}/{len(optionchain)}")
                
                # Check if LTPs were fetched
                ltps_fetched = sum(1 for strike_data in optionchain.values() 
                                 if strike_data.get("optionltp") is not None)
                print(f"   LTPs fetched: {ltps_fetched}/{len(optionchain)}")
            
            if selected_ce:
                print(f"   Selected CE strikes: {list(selected_ce.keys())}")
                success_count += 1
            elif selected_pe:
                print(f"   Selected PE strikes: {list(selected_pe.keys())}")
                success_count += 1
            else:
                print(f"   ❌ No strikes selected")
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Total symbols processed: {len(result_dict)}")
        print(f"   Symbols with selected strikes: {success_count}")
        print(f"   Success rate: {(success_count/len(result_dict)*100):.1f}%")
        
        if success_count > 0:
            print("\n✅ Optimized flow test PASSED!")
            return True
        else:
            print("\n❌ Optimized flow test FAILED - No strikes selected")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimized_flow()
    sys.exit(0 if success else 1) 