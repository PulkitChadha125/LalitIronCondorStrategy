import sys
sys.path.append('.')
from main import login_marketdata_api, login_interactive_api

def test_market_data_login():
    print("Testing Market Data API Login...")
    print("=" * 50)
    
    try:
        result = login_marketdata_api()
        if result:
            print("✅ Market Data Login successful!")
            print(f"Object type: {type(result)}")
            print(f"Has token: {hasattr(result, 'token')}")
            if hasattr(result, 'token'):
                print(f"Token: {result.token}")
        else:
            print("❌ Market Data Login failed!")
    except Exception as e:
        print(f"❌ Error during market data login: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_data_login()