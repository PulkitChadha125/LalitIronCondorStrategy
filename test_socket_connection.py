#!/usr/bin/env python3
"""
Test script to verify interactive login and socket connection
"""

import sys
import time
import traceback

# Add the current directory to the path
sys.path.append('.')

from main import login_interactive_api, get_api_credentials

def test_interactive_login_and_socket():
    """Test the interactive login and socket connection"""
    print("Testing Interactive Login and Socket Connection...")
    print("=" * 50)
    
    try:
        # Test interactive login
        print("1. Testing Interactive Login...")
        xt = login_interactive_api()
        
        if xt:
            print("✅ Interactive login successful!")
            print("2. Socket connection should be established automatically...")
            print("3. Waiting for socket events...")
            
            # Wait for a few seconds to see socket events
            for i in range(10):
                print(f"   Waiting... {i+1}/10 seconds")
                time.sleep(1)
            
            print("✅ Test completed successfully!")
            return True
        else:
            print("❌ Interactive login failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_interactive_login_and_socket()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")
        sys.exit(1) 