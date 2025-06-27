#!/usr/bin/env python3
"""
Test script to verify net position fetcher works correctly
"""

import sys
import time
import traceback

# Add the current directory to the path
sys.path.append('.')

from main import login_interactive_api, get_net_positions

def test_net_position_fetcher():
    """Test the net position fetcher"""
    print("Testing Net Position Fetcher...")
    print("=" * 50)
    
    try:
        # Test interactive login (this will also start the net position fetcher thread)
        print("1. Testing Interactive Login...")
        xt = login_interactive_api()
        
        if xt:
            print("✅ Interactive login successful!")
            print("2. Net position fetcher thread should be started automatically...")
            print("3. Testing net position fetching...")
            
            # Wait a few seconds for the first fetch to complete
            print("   Waiting for first net position fetch...")
            time.sleep(3)
            
            # Test getting net positions
            positions = get_net_positions()
            print(f"✅ Retrieved {len(positions)} net positions")

            print("positions", positions)
            
           
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_net_position_fetcher()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")
        sys.exit(1) 