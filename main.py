import pandas as pd
import datetime  # full module
import json
# from datetime import datetime, timedelta
import time
import traceback
import sys
# Ensure the SDK path is included for import
sys.path.append('.')
# Now import the SDK
from xtspythonclientapisdk.Connect import XTSConnect
import threading

xts_marketdata = None
xt=None
Future_instrument_id_list=[]
Equity_instrument_id_list=[]

# Global variable to store running positions
running_positions = []

# Global variable to store net positions
net_positions = []

def get_result_dict():
    global result_dict
    return result_dict


def set_marketdata_connection(connection):
    global xts_marketdata
    xts_marketdata = connection


def delete_file_contents(file_name):
    try:
        # Open the file in write mode, which truncates it (deletes contents)
        with open(file_name, 'w') as file:
            file.truncate(0)
        print(f"Contents of {file_name} have been deleted.")
    except FileNotFoundError:
        print(f"File {file_name} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def interactivelogin():
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    import time
    from selenium.webdriver.common.by import By
    import json
    import pyotp
    from xtspythonclientapisdk.Connect import XTSConnect

    global xt
    # URL="http://122.184.68.130:3008//interactive/thirdparty?appKey=93e98b500aaeb837ead698&returnURL=http://122.184.68.130:3008//interactive/testapi#!/logIn"
    URL="https://strade.shareindia.com//interactive/thirdparty?appKey=a743d238d50923fc2dd127&returnURL=https://strade.shareindia.com/interactive/testapi"
    driver = webdriver.Chrome()
    driver.get(URL)
    time.sleep(2)
    search = driver.find_element(by=By.NAME, value="userID")
    search.send_keys("66BP01")
    search.send_keys(Keys.RETURN)
    time.sleep(1)
    driver.find_element(by=By.ID, value="confirmimage").click()
    search = driver.find_element(by=By.ID, value="login_password_field")
    search.send_keys("Rohit@987")
    driver.find_element("xpath", "/html/body/ui-view/div[1]/div/div/div/div[2]/form/div[4]/div[2]/button").click()
    time.sleep(2)
    totpField = driver.find_element(by=By.NAME, value="efirstPin")
    totp = pyotp.TOTP('OZYCSOBXOIQWSLBJKBYVKNZBNUSX2MD2GRRTKOJEJUYXO5KANNDQ')
    TOTP = totp.now()
    time.sleep(2)
    totpField.send_keys(TOTP)
    driver.find_element(by=By.CLASS_NAME, value="PlaceButton").click()
    time.sleep(3)
    json_list = []
    json_list = driver.find_element(By.TAG_NAME,"pre").get_attribute('innerHTML')
    aDict = json.loads(json_list)
    sDict = json.loads(aDict['session'])
    accessToken=sDict['accessToken']
    print("accessToken:",accessToken)

    driver.close()

    credentials = get_api_credentials()
    interactive_app_key = credentials.get("Interactive_App_Key")
    interactive_app_secret = credentials.get("Interactive_App_Secret")
    if not interactive_app_key or not interactive_app_secret:
        print("Missing Interactive API credentials in Credentials.csv")
        return None
    xt = XTSConnect(apiKey=interactive_app_key, secretKey=interactive_app_secret, source="WEBAPI", root="http://colo.srellp.com:3000")
    try:
        response = xt.interactive_login()
        print("Interactive Login Response:", response)
        if response and 'result' in response and 'token' in response['result']:
            print("Interactive login successful")
            
            # Start the net position fetcher thread
            from main import start_net_position_fetcher
            start_net_position_fetcher()
            
            return xt
        else:
            print("Interactive login failed: ", response)
            return None
    except Exception as e:
        print(f"Error during interactive login: {str(e)}")
        import traceback
        traceback.print_exc()
        return None





def get_open_positions():
    response=xt.get_open_positions()
    print("Get Open Positions: ", response)
    return response

#  INTERAACTIVE LOGIN ABOVE

def place_order(nfo_ins_id,order_quantity,order_side,price,unique_key):
    val=None
    if order_side == "BUY":
        val=xt.TRANSACTION_TYPE_BUY
    elif order_side == "SELL":
        val=xt.TRANSACTION_TYPE_SELL

        
    response=xt.place_order (
        exchangeSegment=xt.EXCHANGE_NSEFO,
        exchangeInstrumentID=nfo_ins_id,
        productType=xt.PRODUCT_MIS,
        orderType=xt.ORDER_TYPE_LIMIT,
        orderSide=val,
        timeInForce=xt.VALIDITY_DAY,
        disclosedQuantity=0,
        orderQuantity=order_quantity,
        limitPrice=price,
        stopPrice=0,
        apiOrderSource="WEBAPI",
        orderUniqueIdentifier="454845",
        clientID= "*****" )

    print("Place Order: ", response)
    write_to_order_logs(f"Broker Order Response: [{datetime.datetime.now()}]  {order_side} quantity: {order_quantity} price: {price} response: {response}")
    print("-" * 50) 
    write_to_order_logs("-" * 50)
    

def write_to_order_logs(message):
    with open('OrderLog.txt', 'a') as file:  # Open the file in append mode
        file.write(message + '\n')

result_dict = {}

def get_user_settings():
    global result_dict, instrument_id_list
    delete_file_contents("OrderLog.txt")
    try:
        csv_path = 'TradeSettings.csv'
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        result_dict = {}
        instrument_id_list = []
        

        for index, row in df.iterrows():
            symbol = row['Symbol']
            expiry = row['EXPIERY']  # Format: 29-05-2025

            # Convert expiry to API format: DDMonYYYY (e.g., 29May2025)
            expiry_api_format = datetime.datetime.strptime(expiry, "%d-%m-%Y").strftime("%d%b%Y")

           
            # Fetch EQ instrument ID (NSECM)
            eq_response = xts_marketdata.get_equity_symbol(
                exchangeSegment=1,      # NSECM
                series='EQ',
                symbol=symbol
            )

            # Fetch FUTSTK instrument ID
            fut_response = xts_marketdata.get_future_symbol(
                exchangeSegment=2,      # NSEFO
                series='FUTSTK',
                symbol=symbol,
                expiryDate=expiry_api_format
            )

            if fut_response['type'] == 'success' and 'result' in fut_response:
                result_item = fut_response['result'][0]
                NSEFOinstrument_id = int(result_item['ExchangeInstrumentID'])
                lot_size = int(result_item.get('LotSize', 0))
                # print(f"lot_size: {lot_size}")

            else:
                print(f"[ERROR] Could not get FUTSTK instrument ID for {symbol} {expiry_api_format}")
                NSEFOinstrument_id = None
                lot_size = None

            # Fetch EQ instrument ID (NSECM)
            eq_response = xts_marketdata.get_equity_symbol(
                exchangeSegment=1,      # NSECM
                series='EQ',
                symbol=symbol
            )

            if eq_response['type'] == 'success' and 'result' in eq_response:
                NSECMinstrument_id = int(eq_response['result'][0]['ExchangeInstrumentID'])
            else:
                print(f"[ERROR] Could not get EQ instrument ID for {symbol}")
                NSECMinstrument_id = None

          
            symbol_dict = {
                "Symbol": symbol,"unique_key" : f"{symbol}_{expiry}",
                "Expiry": expiry,
                "Quantity": int(row['Quantity']),"StrikeStep": int(row['StrikeStep']),
                "AllowedPercentage": int(row['AllowedPercentage']),"NSEFOexchangeInstrumentID": NSEFOinstrument_id,"MarginRequired":int(row['MarginRequired']),
                "NSECMexchangeInstrumentID": NSECMinstrument_id,"LotSize": lot_size,"LTP":None,"StepSize":int(row['StepSize']),"StepNumber":int(row['StepNumber']),
                "StepPercentage":int(row['StepPercentage']),"OptionType":row['OptionType'],"Optionchain":None
                
            }

            if NSEFOinstrument_id:
                Future_instrument_id_list.append({
                "exchangeSegment": 2,
                "exchangeInstrumentID": NSEFOinstrument_id
                })

            if NSECMinstrument_id:
                Equity_instrument_id_list.append({
                    "exchangeSegment": 1,
                    "exchangeInstrumentID": NSECMinstrument_id
                })

            result_dict[symbol_dict["unique_key"]] = symbol_dict


           

        print("result_dict: ", result_dict)
        print("-" * 50)
        print("Future_instrument_id_list: ", Future_instrument_id_list)
        print("-" * 50)
        print("Equity_instrument_id_list: ", Equity_instrument_id_list)
        print("-" * 50)

    except Exception as e:
        print("Error happened in fetching symbol", str(e))


def get_api_credentials():
    credentials = {}
    try:
        df = pd.read_csv('Credentials.csv')
        for index, row in df.iterrows():
            title = row['Title']
            value = row['Value']
            credentials[title] = value
    except pd.errors.EmptyDataError:
        print("The CSV file is empty or has no data.")
    except FileNotFoundError:
        print("The CSV file was not found.")
    except Exception as e:
        print("An error occurred while reading the CSV file:", str(e))
    return credentials




def format_date_time(date_time):
    """
    Format datetime object to required format: MMM DD YYYY HHMMSS
    """
    return date_time.strftime("%b %d %Y %H%M%S")

RUN_INTERVAL_SECONDS=None


def login_interactive_api():
    global xt
    credentials = get_api_credentials()
    interactive_app_key = credentials.get("Interactive_App_Key")
    interactive_app_secret = credentials.get("Interactive_App_Secret")

    print("interactive_app_key: ", interactive_app_key)
    print("interactive_app_secret: ", interactive_app_secret)

    if not interactive_app_key or not interactive_app_secret:
        print("Missing Interactive API credentials in Credentials.csv")
        return None

    try:
        # Create XTSConnect object with correct parameters
        xt = XTSConnect(
            apiKey=interactive_app_key, 
            secretKey=interactive_app_secret, 
            source="WEBAPI", 
            root="http://colo.srellp.com:3000"
        )
        response = xt.interactive_login()
        print("Interactive Login Response:", response)

        if response and 'result' in response and 'token' in response['result']:
            print("Interactive login successful")
            # Start the net position fetcher thread
            from main import start_net_position_fetcher
            start_net_position_fetcher()
            return xt
        else:
            print("Interactive login failed: ", response)
            return None
    except Exception as e:
        print(f"Error during interactive login: {str(e)}")
        import traceback
        traceback.print_exc()
        return None




def login_marketdata_api():
    """
    Login to the Market Data API and return the XTSConnect object.
    """
    global xts_marketdata

    try:
        credentials = get_api_credentials()
        source = "WEBAPI"
        market_data_app_key = credentials.get("Market_Data_API_App_Key")
        market_data_app_secret = credentials.get("Market_Data_API_App_Secret")
        print("market_data_app_key: ", market_data_app_key)
        print("market_data_app_secret: ", market_data_app_secret)
        print("source: ", source)

        if not market_data_app_key or not market_data_app_secret:
            print("Missing Market Data API credentials in Credentials.csv")
            return None

        # Use the correct root URL (do NOT include /apimarketdata)
        xts_marketdata = XTSConnect(
            apiKey=market_data_app_key,
            secretKey=market_data_app_secret,
            source=source,
            root="http://colo.srellp.com:3000"
        )

        print("xts_marketdata object created: ", xts_marketdata)
        response = xts_marketdata.marketdata_login()
        print("Market Data Login Response:", response)
        print("Market Data Login Response type: ", type(xts_marketdata))

        if response and response.get('type') == 'success':
            print("Market Data login successful")
            return xts_marketdata
        else:
            print("Market Data login failed: ", response)
            return None
        

    except Exception as e:
        print(f"Error during market data login: {str(e)}")
        import traceback
        traceback.print_exc()
        return None




def chunk_instruments(instrument_list, chunk_size=50):
    for i in range(0, len(instrument_list), chunk_size):
        yield instrument_list[i:i + chunk_size]



def Equity_MarketQuote(xts_marketdata):
    global Equity_instrument_id_list, result_dict

    if not Equity_instrument_id_list:
        print("Instrument list is empty, skipping quote fetch.")
        return

    # Mapping: InstrumentID → Symbol
    symbol_by_id = {
    params.get("NSECMexchangeInstrumentID"): (symbol, params)
    for symbol, params in result_dict.items()
    if params.get("NSECMexchangeInstrumentID") and params.get("TakeTrade") == True 
        }



    for chunk in chunk_instruments(Equity_instrument_id_list, 50):
        try:
            response = xts_marketdata.get_quote(
                Instruments=chunk,
                xtsMessageCode=1501,
                publishFormat='JSON'
            )
            print(f"response: {response}")
            

            if response and response.get("type") == "success":
                
                quote_strings = response["result"].get("listQuotes", [])

                for quote_str in quote_strings:
                    try:
                        item = json.loads(quote_str)
                        instrument_id = item.get("ExchangeInstrumentID")

                        if instrument_id in symbol_by_id:
                            symbol, params = symbol_by_id[instrument_id]
                            ltp = item.get("LastTradedPrice")
                            params["EQltp"] = int(ltp)  # ✅ Now valid and consistent
                            params["dayOpen"] = item.get("Open")
                            print(f"[params[dayOpen]] {symbol}: {params["dayOpen"]}")
                            print(f"[params[EQltp]] {symbol}: {params["EQltp"]}")

                    except Exception as inner_err:
                        print(f"[WARN] Skipping malformed quote: {inner_err}")
                        continue
            else:
                print(f"[ERROR] Unexpected quote response: {response}")

        except Exception as e:
            print(f"[ERROR] While fetching quote chunk: {e}")
            traceback.print_exc()



def calculate_strike_ranges(ltp, step_percentage, step_size):
    """
    Calculate strike ranges based on LTP, StepPercentage, and StepSize.
    
    Args:
        ltp (int): Last Traded Price
        step_percentage (int): Percentage to calculate range
        step_size (int): Step size for rounding
    
    Returns:
        dict: Dictionary with strikes as keys and nested dict with optionltp and instrument_id
    """
    try:
        # Calculate the percentage value
        percentage_value = (ltp * step_percentage) / 100
        
        # Calculate upper and lower ranges
        upper_range = ltp + percentage_value
        lower_range = ltp - percentage_value
        
        # Round to nearest step_size
        upper_rounded = round(upper_range / step_size) * step_size
        lower_rounded = round(lower_range / step_size) * step_size
        
        # Generate strike dictionary from lower to upper range
        strikes_dict = {}
        current_strike = lower_rounded
        
        while current_strike <= upper_rounded:
            strike_key = int(current_strike)
            strikes_dict[strike_key] = {
                "optionltp": None,
                "instrument_id": None
            }
            current_strike += step_size
        
        return strikes_dict
    
    except Exception as e:
        print(f"Error calculating strike ranges: {str(e)}")
        return {}

def Future_MarketQuote(xts_marketdata):
    global Future_instrument_id_list, result_dict

    if not Future_instrument_id_list:
        print("Instrument list is empty, skipping quote fetch.")
        return

    # Mapping: InstrumentID → Symbol (removed unnecessary conditions)
    symbol_by_id = {
        params.get("NSEFOexchangeInstrumentID"): (symbol, params)
        for symbol, params in result_dict.items()
        if params.get("NSEFOexchangeInstrumentID")
    }

    print(f"Symbol mapping created for {len(symbol_by_id)} instruments")

    for chunk in chunk_instruments(Future_instrument_id_list, 50):
        try:
            response = xts_marketdata.get_quote(
                Instruments=chunk,
                xtsMessageCode=1501,
                publishFormat='JSON'
            )

            if response and response.get("type") == "success":
                quote_strings = response["result"].get("listQuotes", [])
                print("quote_strings: ", quote_strings)
                print("response: ", response)

                for quote_str in quote_strings:
                    try:
                        item = json.loads(quote_str)
                        instrument_id = item.get("ExchangeInstrumentID")

                        if instrument_id in symbol_by_id:
                            symbol, params = symbol_by_id[instrument_id]
                            ltp = item.get("LastTradedPrice")
                            params["Futltp"] = int(ltp)  # ✅ Now valid and consistent
                            print(f"[params[Futltp]] {symbol}: {params['Futltp']}")
                            
                            # Calculate strike ranges after getting LTP
                            if params["Futltp"] and params["StepPercentage"] and params["StepSize"]:
                                step_percentage = int(params["StepPercentage"])
                                step_size = int(params["StepSize"])
                                strikes = calculate_strike_ranges(params["Futltp"], step_percentage, step_size)
                                params["Optionchain"] = strikes
                                print(f"[Optionchain] {symbol}: {strikes}")

                    except Exception as inner_err:
                        print(f"[WARN] Skipping malformed quote: {inner_err}")
                        continue
            else:
                print(f"[ERROR] Unexpected quote response: {response}")

        except Exception as e:
            print(f"[ERROR] While fetching quote chunk: {e}")
            traceback.print_exc()
    
    print("[INFO] Future LTP fetch and strike range calculation completed.")







def main_strategy():
    global allowed_trades_saved
    try:
        global xts_marketdata
        
        if not xts_marketdata:
            print("Market Data API not initialized")
            return
            
        print(f"\nStarting main strategy at {datetime.datetime.now()}")
        
        # Step 1: Fetch Future LTPs and calculate strike ranges
        print("[STEP 1] Fetching Future LTPs and calculating strike ranges...")
        Future_MarketQuote(xts_marketdata) 
        
        # Step 2: Fetch ALL option instrument IDs for all strikes (individual calls)
        print("[STEP 2] Fetching ALL option instrument IDs...")
        instrument_ids_fetched = fetch_option_instrument_ids(xts_marketdata)
        
        if not instrument_ids_fetched:
            print("[ERROR] No instrument IDs were fetched successfully. Cannot proceed to LTP fetch.")
            return
        
        # Step 3: Fetch ALL option LTPs in batches (optimized)
        print("[STEP 3] Fetching ALL option LTPs in batches...")
        Option_MarketQuote(xts_marketdata)
        
        # Step 4: Select strikes based on criteria
        print("[STEP 4] Selecting strikes based on criteria...")
        for unique_key, params in result_dict.items():
            symbol = params.get("Symbol")
            option_type = params.get("OptionType")
            
            if option_type == "CE":
                print(f"Processing CE strikes for {symbol}")
                selected_strikes = select_ce_strikes(params)
                if selected_strikes:
                    params["optionselectedstrike_CE"] = selected_strikes
                    print(f"Selected CE strikes for {symbol}: {list(selected_strikes.keys())}")
                else:
                    print(f"No suitable CE strikes found for {symbol}")
                    params["optionselectedstrike_CE"] = None
            
            elif option_type == "PE":
                print(f"Processing PE strikes for {symbol}")
                selected_strikes = select_pe_strikes(params)
                if selected_strikes:
                    params["optionselectedstrike_PE"] = selected_strikes
                    print(f"Selected PE strikes for {symbol}: {list(selected_strikes.keys())}")
                else:
                    print(f"No suitable PE strikes found for {symbol}")
                    params["optionselectedstrike_PE"] = None
        
        # Step 5: Print summary
        print("[DEBUG] Final selected_strike summary:")
        for unique_key, params in result_dict.items():
            print(f"{params.get('Symbol')} ({params.get('OptionType')}): {params.get('optionselectedstrike_CE') or params.get('optionselectedstrike_PE')}")
            
        print(f"\nMain strategy completed at {datetime.datetime.now()}")
            
    except Exception as e:
        print("Error in main strategy:", str(e))
        traceback.print_exc()

def fetch_option_instrument_ids(xts_marketdata):
    """
    Fetch option instrument IDs for all strikes in the Optionchain for all symbols.
    This function should be called after Future_MarketQuote has calculated the strike ranges.
    Optimized to fetch all instrument IDs first, then proceed to LTP fetching.
    """
    global result_dict
    
    print(f"[INFO] Starting option instrument ID fetch for {len(result_dict)} symbols")
    
    total_strikes = 0
    successful_fetches = 0
    failed_fetches = 0
    
    for unique_key, params in result_dict.items():
        symbol = params.get("Symbol")
        optionchain = params.get("Optionchain")
        expiry = params.get("Expiry")
        option_type = params.get("OptionType")
        
        if not optionchain or not expiry or not option_type:
            print(f"[WARN] Missing data for {symbol}: optionchain={bool(optionchain)}, expiry={expiry}, option_type={option_type}")
            continue
            
        # Convert expiry to API format: DDMonYYYY (e.g., 29May2025)
        expiry_api_format = datetime.datetime.strptime(expiry, "%d-%m-%Y").strftime("%d%b%Y")
        
        strikes_count = len(optionchain)
        total_strikes += strikes_count
        print(f"[INFO] Fetching {strikes_count} option instrument IDs for {symbol} ({option_type})")
        
        # Fetch instrument ID for each strike
        for strike_price in optionchain.keys():
            try:
                opt_response = xts_marketdata.get_option_symbol(
                    exchangeSegment=2,      # NSEFO
                    series='OPTSTK',
                    symbol=symbol,
                    expiryDate=expiry_api_format,
                    optionType=option_type,
                    strikePrice=strike_price
                )
                
                if opt_response['type'] == 'success' and 'result' in opt_response and opt_response['result']:
                    instrument_id = int(opt_response['result'][0]['ExchangeInstrumentID'])
                    optionchain[strike_price]['instrument_id'] = instrument_id
                    successful_fetches += 1
                    print(f"[SUCCESS] {symbol} Strike {strike_price}: Instrument ID = {instrument_id}")
                else:
                    print(f"[ERROR] Could not get option instrument ID for {symbol} Strike {strike_price}")
                    optionchain[strike_price]['instrument_id'] = None
                    failed_fetches += 1
                    
            except Exception as e:
                print(f"[ERROR] Exception while fetching option instrument ID for {symbol} Strike {strike_price}: {str(e)}")
                optionchain[strike_price]['instrument_id'] = None
                failed_fetches += 1
                
        # Update the result_dict with the modified optionchain
        result_dict[unique_key] = params
    
    print(f"[SUMMARY] Instrument ID Fetch Complete:")
    print(f"  Total strikes processed: {total_strikes}")
    print(f"  Successful fetches: {successful_fetches}")
    print(f"  Failed fetches: {failed_fetches}")
    print(f"  Success rate: {(successful_fetches/total_strikes*100):.1f}%" if total_strikes > 0 else "  No strikes to process")
    
    # Now that all instrument IDs are fetched, we can proceed to LTP fetching
    print(f"[INFO] All instrument IDs fetched. Proceeding to LTP fetch...")
    return successful_fetches > 0  # Return True if we have at least some successful fetches

def Option_MarketQuote(xts_marketdata):
    """
    Fetch option LTPs for all strikes in the Optionchain for all symbols.
    Process in chunks of 25 instrument IDs at a time as per API limitation.
    """
    global result_dict
    
    print(f"[INFO] Starting option LTP fetch for {len(result_dict)} symbols")
    
    # Collect all option instrument IDs from all symbols
    option_instrument_id_list = []
    instrument_id_to_strike_mapping = {}
    
    for unique_key, params in result_dict.items():
        symbol = params.get("Symbol")
        optionchain = params.get("Optionchain")
        
        if not optionchain:
            print(f"[WARN] No optionchain found for {symbol}")
            continue
            
        for strike_price, strike_data in optionchain.items():
            instrument_id = strike_data.get("instrument_id")
            if instrument_id:
                option_instrument_id_list.append({
                    "exchangeSegment": 2,  # NSEFO
                    "exchangeInstrumentID": instrument_id
                })
                # Store mapping for later use
                instrument_id_to_strike_mapping[instrument_id] = {
                    "unique_key": unique_key,
                    "symbol": symbol,
                    "strike_price": strike_price
                }
    
    if not option_instrument_id_list:
        print("[WARN] No option instrument IDs found to fetch quotes")
        return
    
    total_instruments = len(option_instrument_id_list)
    print(f"[INFO] Found {total_instruments} option instruments to fetch LTPs")
    
    # Calculate number of chunks
    chunk_size = 25
    num_chunks = (total_instruments + chunk_size - 1) // chunk_size
    print(f"[INFO] Will process in {num_chunks} chunks of {chunk_size} instruments each")
    
    successful_ltps = 0
    failed_ltps = 0
    
    # Process in chunks of 25
    for chunk_index, chunk in enumerate(chunk_instruments(option_instrument_id_list, chunk_size), 1):
        try:
            print(f"[INFO] Processing chunk {chunk_index}/{num_chunks} ({len(chunk)} instruments)")
            
            response = xts_marketdata.get_quote(
                Instruments=chunk,
                xtsMessageCode=1501,
                publishFormat='JSON'
            )
            
            if response and response.get("type") == "success":
                quote_strings = response["result"].get("listQuotes", [])
                
                for quote_str in quote_strings:
                    try:
                        item = json.loads(quote_str)
                        instrument_id = item.get("ExchangeInstrumentID")
                        ltp = item.get("LastTradedPrice")
                        
                        if instrument_id in instrument_id_to_strike_mapping:
                            mapping = instrument_id_to_strike_mapping[instrument_id]
                            unique_key = mapping["unique_key"]
                            symbol = mapping["symbol"]
                            strike_price = mapping["strike_price"]
                            
                            # Update the optionchain with LTP
                            if unique_key in result_dict:
                                result_dict[unique_key]["Optionchain"][strike_price]["optionltp"] = float(ltp) if ltp else None
                                successful_ltps += 1
                                print(f"[SUCCESS] {symbol} Strike {strike_price}: LTP = {ltp}")
                            else:
                                print(f"[ERROR] Unique key {unique_key} not found in result_dict")
                                failed_ltps += 1
                        else:
                            print(f"[WARN] Instrument ID {instrument_id} not found in mapping")
                            failed_ltps += 1
                            
                    except Exception as inner_err:
                        print(f"[WARN] Skipping malformed quote: {inner_err}")
                        failed_ltps += 1
                        continue
            else:
                print(f"[ERROR] Unexpected quote response: {response}")
                failed_ltps += len(chunk)
                
        except Exception as e:
            print(f"[ERROR] While fetching option quote chunk {chunk_index}: {e}")
            failed_ltps += len(chunk)
            traceback.print_exc()
    
    print(f"[SUMMARY] Option LTP Fetch Complete:")
    print(f"  Total instruments processed: {total_instruments}")
    print(f"  Successful LTP fetches: {successful_ltps}")
    print(f"  Failed LTP fetches: {failed_ltps}")
    print(f"  Success rate: {(successful_ltps/total_instruments*100):.1f}%" if total_instruments > 0 else "  No instruments to process")

def select_ce_strikes(params):
    """
    Select CE strikes based on premium difference and allowed percentage
    Returns nested dictionary with selected strikes or None if no match
    """
    optionchain = params.get("Optionchain")
    lot_size = params.get("LotSize")
    margin_required = params.get("MarginRequired")
    allowed_percentage = params.get("AllowedPercentage")
    if not all([optionchain, lot_size, margin_required, allowed_percentage]):
        print(f"[ERROR] Missing required data for strike selection")
        return None
    strikes_desc = sorted(optionchain.keys(), reverse=True)
    midpoint = len(strikes_desc) // 2
    print(f"[INFO] Checking {len(strikes_desc)} CE strikes up to midpoint {midpoint}")
    for strike in optionchain:
        optionchain[strike]["percentage"] = None
    for i in range(midpoint):
        for j in range(i+1, min(i+3, len(strikes_desc))):  # look back by 1 and 2
            strike1 = strikes_desc[i]
            strike2 = strikes_desc[j]
            ltp1 = optionchain[strike1].get("optionltp")
            ltp2 = optionchain[strike2].get("optionltp")
            if ltp1 is None or ltp2 is None:
                continue
            premium_diff = (ltp1 - ltp2) * lot_size
            percentage = abs(premium_diff) / margin_required * 100
            optionchain[strike1]["percentage"] = percentage
            optionchain[strike2]["percentage"] = percentage
            print(f"[DEBUG] CE Comparing {strike1}({ltp1}) vs {strike2}({ltp2}): Premium={premium_diff:.2f}, Percentage={percentage:.2f}%")
            if allowed_percentage <= percentage <= (allowed_percentage + 2):
                print(f"[SUCCESS] Found matching CE strikes: {strike1} and {strike2} with {percentage:.2f}%")
                return {
                    strike1: {
                        "optionltp": ltp1,
                        "instrument_id": optionchain[strike1].get("instrument_id"),
                        "percentage": percentage
                    },
                    strike2: {
                        "optionltp": ltp2,
                        "instrument_id": optionchain[strike2].get("instrument_id"),
                        "percentage": percentage
                    }
                }
    print(f"[INFO] No matching CE strikes found within {allowed_percentage}% to {allowed_percentage + 2}% range")
    return None

def select_pe_strikes(params):
    """
    Select PE strikes based on premium difference and allowed percentage
    Returns nested dictionary with selected strikes or None if no match
    """
    optionchain = params.get("Optionchain")
    lot_size = params.get("LotSize")
    margin_required = params.get("MarginRequired")
    allowed_percentage = params.get("AllowedPercentage")
    if not all([optionchain, lot_size, margin_required, allowed_percentage]):
        print(f"[ERROR] Missing required data for PE strike selection")
        return None
    strikes_asc = sorted(optionchain.keys())
    midpoint = len(strikes_asc) // 2
    print(f"[INFO] Checking {len(strikes_asc)} PE strikes up to midpoint {midpoint}")
    for strike in optionchain:
        optionchain[strike]["percentage"] = None
    for i in range(midpoint):
        for j in range(i+1, min(i+3, len(strikes_asc))):  # look ahead by 1 and 2
            strike1 = strikes_asc[i]
            strike2 = strikes_asc[j]
            ltp1 = optionchain[strike1].get("optionltp")
            ltp2 = optionchain[strike2].get("optionltp")
            if ltp1 is None or ltp2 is None:
                continue
            premium_diff = (ltp2 - ltp1) * lot_size
            percentage = abs(premium_diff) / margin_required * 100
            optionchain[strike1]["percentage"] = percentage
            optionchain[strike2]["percentage"] = percentage
            print(f"[DEBUG] PE Comparing {strike2}({ltp2}) vs {strike1}({ltp1}): Premium={premium_diff:.2f}, Percentage={percentage:.2f}%")
            if allowed_percentage <= percentage <= (allowed_percentage + 2):
                print(f"[SUCCESS] Found matching PE strikes: {strike2} and {strike1} with {percentage:.2f}%")
                return {
                    strike2: {
                        "optionltp": ltp2,
                        "instrument_id": optionchain[strike2].get("instrument_id"),
                        "percentage": percentage
                    },
                    strike1: {
                        "optionltp": ltp1,
                        "instrument_id": optionchain[strike1].get("instrument_id"),
                        "percentage": percentage
                    }
                }
    print(f"[INFO] No matching PE strikes found within {allowed_percentage}% to {allowed_percentage + 2}% range")
    return None

def fetch_net_positions():
    """
    Fetch net positions from XTS API and update the global net_positions list.
    This function is called every 2 seconds in a background thread.
    """
    global net_positions, xt
    try:
        if xt:
            # For dealer accounts, we need to pass clientID
            # From the login response, we can see clientCodes: ['CLI4342']
            response = xt.get_position_netwise(clientID="CLI4342")
            print("response", response)
            if response and response.get('type') == 'success':
                # Extract positionList from the response structure
                result = response.get('result', {})
                positions_data = result.get('positionList', [])
                
                # Filter out empty/zero values
                valid_positions = []
                for pos in positions_data:
                    if pos and pos != 0 and pos != "" and isinstance(pos, dict):
                        valid_positions.append(pos)
                
                net_positions = valid_positions
                print(f"[NET POSITION] Fetched {len(positions_data)} total positions, {len(valid_positions)} valid positions at {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                # Debug: Print the structure of the first valid position
                if valid_positions and len(valid_positions) > 0:
                    print(f"[NET POSITION] Sample position structure: {valid_positions[0]}")
                else:
                    print("[NET POSITION] No valid positions found (this is normal if you have no open positions)")
            else:
                print(f"[NET POSITION] Error fetching net positions: {response}")
        else:
            print("[NET POSITION] Interactive API not logged in")
    except Exception as e:
        print(f"[NET POSITION] Exception while fetching net positions: {str(e)}")

def start_net_position_fetcher():
    """
    Start a background thread that fetches net positions every 2 seconds.
    This function should be called after successful interactive login.
    """
    def net_position_worker():
        print("[NET POSITION] Starting net position fetcher thread...")
        while True:
            try:
                fetch_net_positions()
                time.sleep(2)  # Wait 2 seconds before next fetch
            except Exception as e:
                print(f"[NET POSITION] Error in net position worker: {str(e)}")
                time.sleep(2)  # Continue trying even if there's an error
    
    # Start the background thread
    net_position_thread = threading.Thread(target=net_position_worker, daemon=True)
    net_position_thread.start()
    print("[NET POSITION] Net position fetcher thread started successfully")

def get_net_positions():
    """
    Return the latest net positions for the net position panel.
    Extracts and returns: Symbol, Quantity, NetAmount, RealizedMTM, UnrealizedMTM, MTM, ProductType, ExchangeInstrumentId.
    """
    global net_positions
    result = []
    
    # net_positions is now a list of dicts from response['result']['positionList']
    for pos in net_positions:
        try:
            # Only process dicts
            if not isinstance(pos, dict):
                continue
            result.append({
                'symbol': pos.get('TradingSymbol', ''),
                'quantity': pos.get('Quantity', '0'),
                'netAmount': pos.get('NetAmount', ''),
                'realizedMTM': pos.get('RealizedMTM', ''),
                'unrealizedMTM': pos.get('UnrealizedMTM', ''),
                'mtm': pos.get('MTM', ''),
                'productType': pos.get('ProductType', ''),
                'exchangeInstrumentId': pos.get('ExchangeInstrumentId', ''),
            })
        except Exception as e:
            print('[NET POSITION] Error extracting fields:', e)
    return result

# --- USAGE EXAMPLE ---
# After successful login, call:
# start_net_position_fetcher()

def Future_MarketQuote_for_symbol(xts_marketdata, unique_key):
    """Fetch Future LTP and calculate strike ranges for a single symbol."""
    global result_dict
    params = result_dict.get(unique_key)
    if not params or not params.get("NSEFOexchangeInstrumentID"):
        print(f"[WARN] No NSEFOexchangeInstrumentID for {unique_key}")
        return
    instrument_id = params["NSEFOexchangeInstrumentID"]
    try:
        response = xts_marketdata.get_quote(
            Instruments=[{"exchangeSegment": 2, "exchangeInstrumentID": instrument_id}],
            xtsMessageCode=1501,
            publishFormat='JSON'
        )
        if response and response.get("type") == "success":
            quote_strings = response["result"].get("listQuotes", [])
            for quote_str in quote_strings:
                item = json.loads(quote_str)
                ltp = item.get("LastTradedPrice")
                params["Futltp"] = int(ltp) if ltp else None
                if params["Futltp"] and params["StepPercentage"] and params["StepSize"]:
                    step_percentage = int(params["StepPercentage"])
                    step_size = int(params["StepSize"])
                    strikes = calculate_strike_ranges(params["Futltp"], step_percentage, step_size)
                    params["Optionchain"] = strikes
        else:
            print(f"[ERROR] Unexpected quote response for {unique_key}: {response}")
    except Exception as e:
        print(f"[ERROR] While fetching quote for {unique_key}: {e}")
        traceback.print_exc()
    result_dict[unique_key] = params

def fetch_option_instrument_ids_for_symbol(xts_marketdata, unique_key):
    """Fetch option instrument IDs for all strikes for a single symbol."""
    global result_dict
    params = result_dict.get(unique_key)
    if not params:
        return
    symbol = params.get("Symbol")
    optionchain = params.get("Optionchain")
    expiry = params.get("Expiry")
    option_type = params.get("OptionType")
    if not optionchain or not expiry or not option_type:
        return
    expiry_api_format = datetime.datetime.strptime(expiry, "%d-%m-%Y").strftime("%d%b%Y")
    for strike_price in optionchain.keys():
        try:
            opt_response = xts_marketdata.get_option_symbol(
                exchangeSegment=2,
                series='OPTSTK',
                symbol=symbol,
                expiryDate=expiry_api_format,
                optionType=option_type,
                strikePrice=strike_price
            )
            if opt_response['type'] == 'success' and 'result' in opt_response and opt_response['result']:
                instrument_id = int(opt_response['result'][0]['ExchangeInstrumentID'])
                optionchain[strike_price]['instrument_id'] = instrument_id
            else:
                optionchain[strike_price]['instrument_id'] = None
        except Exception as e:
            optionchain[strike_price]['instrument_id'] = None
    params["Optionchain"] = optionchain
    result_dict[unique_key] = params

def Option_MarketQuote_for_symbol(xts_marketdata, unique_key):
    """Fetch option LTPs for all strikes for a single symbol."""
    global result_dict
    params = result_dict.get(unique_key)
    if not params:
        return
    optionchain = params.get("Optionchain")
    if not optionchain:
        return
    option_instrument_id_list = []
    for strike_price, strike_data in optionchain.items():
        instrument_id = strike_data.get("instrument_id")
        if instrument_id:
            option_instrument_id_list.append({
                "exchangeSegment": 2,
                "exchangeInstrumentID": instrument_id
            })
    if not option_instrument_id_list:
        return
    chunk_size = 25
    for chunk in chunk_instruments(option_instrument_id_list, chunk_size):
        try:
            response = xts_marketdata.get_quote(
                Instruments=chunk,
                xtsMessageCode=1501,
                publishFormat='JSON'
            )
            if response and response.get("type") == "success":
                quote_strings = response["result"].get("listQuotes", [])
                for quote_str in quote_strings:
                    item = json.loads(quote_str)
                    instrument_id = item.get("ExchangeInstrumentID")
                    ltp = item.get("LastTradedPrice")
                    for strike_price, strike_data in optionchain.items():
                        if strike_data.get("instrument_id") == instrument_id:
                            strike_data["optionltp"] = float(ltp) if ltp else None
                            break
            else:
                continue
        except Exception as e:
            continue
    params["Optionchain"] = optionchain
    result_dict[unique_key] = params

if __name__ == "__main__":
    # # Initialize settings and credentials
    #   # <-- Add this line
    
    get_api_credentials()
    xts_marketdata = login_marketdata_api()
    login_interactive_api()
    # interactivelogin()
    get_user_settings()
    # fetch_MarketQuote(xts_marketdata)

    
    # Initialize Market Data API
    
    if xts_marketdata:
        while True:
            now = datetime.datetime.now()
            print(f"\nStarting main strategy at {datetime.datetime.now()}")
            main_strategy()
            time.sleep(2)
    else:
        print("Failed to initialize Market Data API. Exiting...")
