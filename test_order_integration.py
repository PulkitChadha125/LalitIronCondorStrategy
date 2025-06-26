#!/usr/bin/env python3
"""
Test script for Order Placement Integration
"""

import sys
import traceback

# Add the current directory to the path
sys.path.append('.')

try:
    from main import result_dict, xt, place_order
    print("✅ Successfully imported required modules")
    
    # Test 1: Check if result_dict is accessible
    print("\n📋 Testing result_dict access:")
    if result_dict:
        print(f"✅ result_dict is available with {len(result_dict)} entries")
        for key, value in list(result_dict.items())[:2]:  # Show first 2 entries
            print(f"  Key: {key}")
            print(f"  Symbol: {value.get('Symbol')}")
            print(f"  LotSize: {value.get('LotSize')}")
            print(f"  Quantity: {value.get('Quantity')}")
    else:
        print("❌ result_dict is empty or not available")
    
    # Test 2: Check if interactive API object is available
    print("\n🔧 Testing interactive API object:")
    if xt:
        print(f"✅ Interactive API object is available")
        print(f"  Token: {'Available' if xt.token else 'Not available'}")
        print(f"  UserID: {xt.userID}")
    else:
        print("❌ Interactive API object is not available")
    
    # Test 3: Check if place_order function is available
    print("\n🔍 Testing place_order function:")
    if 'place_order' in globals():
        print("✅ place_order function is available")
    else:
        print("❌ place_order function is not available")
    
    # Test 4: Check selected strikes structure
    print("\n📊 Testing selected strikes structure:")
    if result_dict:
        for key, value in list(result_dict.items())[:1]:  # Check first entry
            symbol = value.get('Symbol')
            option_type = value.get('OptionType')
            selected_strikes_key = f"optionselectedstrike_{option_type}"
            selected_strikes = value.get(selected_strikes_key)
            
            print(f"  Symbol: {symbol}")
            print(f"  Option Type: {option_type}")
            print(f"  Selected Strikes Key: {selected_strikes_key}")
            
            if selected_strikes:
                print(f"  ✅ Selected strikes available: {list(selected_strikes.keys())}")
                for strike, strike_data in selected_strikes.items():
                    print(f"    Strike {strike}:")
                    print(f"      Instrument ID: {strike_data.get('instrument_id')}")
                    print(f"      LTP: {strike_data.get('optionltp')}")
                    print(f"      Percentage: {strike_data.get('percentage')}")
            else:
                print(f"  ❌ No selected strikes for {symbol}")
    
    print("\n✅ All integration tests completed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc() 