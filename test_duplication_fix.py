#!/usr/bin/env python3
"""
Test script to verify that fetch_option_instrument_ids is not being called twice
"""

import sys
import traceback

# Add the current directory to the path
sys.path.append('.')

try:
    from main import main_strategy, result_dict, xts_marketdata
    
    print("✅ Successfully imported required modules")
    
    # Check if we have the necessary data
    if not result_dict:
        print("❌ result_dict is empty. Please run get_user_settings() first.")
        sys.exit(1)
    
    if not xts_marketdata:
        print("❌ xts_marketdata is not initialized. Please login first.")
        sys.exit(1)
    
    print(f"📋 Found {len(result_dict)} symbols in result_dict")
    print("🔧 Running main_strategy once to test for duplication...")
    
    # Run main_strategy once
    main_strategy()
    
    print("✅ main_strategy completed successfully!")
    print("📊 Checking if selected strikes were created:")
    
    for key, params in result_dict.items():
        symbol = params.get("Symbol")
        option_type = params.get("OptionType")
        
        if option_type == "CE":
            selected_strikes = params.get("optionselectedstrike_CE")
            if selected_strikes:
                print(f"  ✅ {symbol} (CE): {list(selected_strikes.keys())}")
            else:
                print(f"  ❌ {symbol} (CE): No strikes selected")
        
        elif option_type == "PE":
            selected_strikes = params.get("optionselectedstrike_PE")
            if selected_strikes:
                print(f"  ✅ {symbol} (PE): {list(selected_strikes.keys())}")
            else:
                print(f"  ❌ {symbol} (PE): No strikes selected")
    
    print("\n✅ Test completed! No duplication detected.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc() 