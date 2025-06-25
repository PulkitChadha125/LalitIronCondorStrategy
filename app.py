from flask import Flask, render_template, jsonify, request
import csv
import json
from datetime import datetime
from main import login_marketdata_api, login_interactive_api, get_user_settings, get_result_dict, Future_instrument_id_list, Equity_instrument_id_list

app = Flask(__name__)

scanner_status = "stopped"
logs = []
market_data_logged_in = False
interactive_logged_in = False
xts_marketdata_obj = None  # Global to store the API object
result_data = None


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {message}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/login_marketdata', methods=['POST'])
def login_marketdata():
    global market_data_logged_in, xts_marketdata_obj
    xts_marketdata_obj = login_marketdata_api()
    if xts_marketdata_obj and hasattr(xts_marketdata_obj, 'token') and xts_marketdata_obj.token:
        market_data_logged_in = True

        from main import set_marketdata_connection
        set_marketdata_connection(xts_marketdata_obj)
        log_message("Market Data API login successful.")
        return jsonify({"status": "success", "message": "Market Data API login successful."})
    else:
        market_data_logged_in = False
        log_message("Market Data API login failed.")
        return jsonify({"status": "error", "message": "Market Data API login failed."})

@app.route('/api/login_interactive', methods=['POST'])
def login_interactive():
    global interactive_logged_in, xts_marketdata_obj
    xts_interactive_obj = login_interactive_api()
    if xts_interactive_obj:
        interactive_logged_in = True
        log_message("Interactive API object created successfully.")
        return jsonify({"status": "success", "message": "Interactive API object created successfully."})
    else:
        interactive_logged_in = False
        log_message("Interactive API object creation failed.")
        return jsonify({"status": "error", "message": "Interactive API object creation failed."})

@app.route('/api/start_scanner', methods=['POST'])
def start_scanner():
    global scanner_status, xts_marketdata_obj
    if scanner_status == "running":
        return jsonify({"status": "error", "message": "Scanner is already running"})
    
    if not xts_marketdata_obj or not hasattr(xts_marketdata_obj, 'token') or not xts_marketdata_obj.token:
        log_message("[ERROR] Market Token is missing. Please login again.")
        return jsonify({"status": "error", "message": "Market Token is missing. Please login again."})

    if not market_data_logged_in or not xts_marketdata_obj:
        log_message("Please login to Market Data API before starting the scanner.")
        return jsonify({"status": "error", "message": "Login to Market Data API first."})

    scanner_status = "running"
    log_message("Scanner started and fetching LTPs...")

    try:
        # Use the existing get_user_settings function to load CSV and get instrument IDs
        from main import get_user_settings, Future_MarketQuote, get_result_dict, set_marketdata_connection
        
        # Set the global market data connection
        set_marketdata_connection(xts_marketdata_obj)
        
        # Load settings and get instrument IDs
        get_user_settings()
        result_dict = get_result_dict()
        print("result_dict: ", result_dict)
        
        if not result_dict:
            log_message("No symbols found in TradeSettings.csv")
            scanner_status = "stopped"
            return jsonify({"status": "error", "message": "No symbols found in TradeSettings.csv"})
        
        log_message(f"Loaded {len(result_dict)} symbols from TradeSettings.csv")
        
        # Use the existing Future_MarketQuote function to fetch LTPs
        Future_MarketQuote(xts_marketdata_obj)
        
        # Fetch option instrument IDs for all strikes
        from main import fetch_option_instrument_ids
        log_message("Fetching option instrument IDs for all strikes...")
        fetch_option_instrument_ids(xts_marketdata_obj)
        
        # Fetch option LTPs for all strikes
        from main import Option_MarketQuote
        log_message("Fetching option LTPs for all strikes...")
        Option_MarketQuote(xts_marketdata_obj)
        
        # Select CE strikes based on premium difference
        from main import select_ce_strikes, select_pe_strikes
        log_message("Selecting CE strikes based on premium difference...")
        for unique_key, params in result_dict.items():
            symbol = params.get("Symbol")
            option_type = params.get("OptionType")
            
            if option_type == "CE":
                log_message(f"Processing CE strikes for {symbol}")
                selected_strikes = select_ce_strikes(params)
                if selected_strikes:
                    params["optionselectedstrike_CE"] = selected_strikes
                    log_message(f"Selected CE strikes for {symbol}: {list(selected_strikes.keys())}")
                else:
                    log_message(f"No suitable CE strikes found for {symbol}")
                    params["optionselectedstrike_CE"] = None
        
        # Select PE strikes based on premium difference
        log_message("Selecting PE strikes based on premium difference...")
        for unique_key, params in result_dict.items():
            symbol = params.get("Symbol")
            option_type = params.get("OptionType")
            
            if option_type == "PE":
                log_message(f"Processing PE strikes for {symbol}")
                selected_strikes = select_pe_strikes(params)
                if selected_strikes:
                    params["optionselectedstrike_PE"] = selected_strikes
                    log_message(f"Selected PE strikes for {symbol}: {list(selected_strikes.keys())}")
                else:
                    log_message(f"No suitable PE strikes found for {symbol}")
                    params["optionselectedstrike_PE"] = None

        # Display LTPs in scanner logs
        for unique_key, data in result_dict.items():
            symbol = data.get("Symbol")
            fut_ltp = data.get("Futltp")
            optionchain = data.get("Optionchain")
            
            if fut_ltp is not None:
                log_message(f"{symbol} | LTP: {fut_ltp}")
                if optionchain:
                    strikes_list = list(optionchain.keys())
                    log_message(f"{symbol} | Strike Range: {strikes_list}")
                    log_message(f"{symbol} | Number of Strikes: {len(strikes_list)}")
                    
                    # Print complete optionchain dictionary
                    log_message(f"{symbol} | Complete Optionchain Dictionary:")
                    log_message(f"{optionchain}")
                    
                    # Also show a few examples for quick reference
                    log_message(f"{symbol} | Sample Strikes with Instrument IDs, LTPs, and Percentages:")
                    for i, strike in enumerate(strikes_list[:3]):  # Show first 3 strikes
                        instrument_id = optionchain[strike].get("instrument_id")
                        optionltp = optionchain[strike].get("optionltp")
                        percentage = optionchain[strike].get("percentage")
                        log_message(f"  Strike {strike}: Instrument ID = {instrument_id}, LTP = {optionltp}, Percentage = {percentage}")
                    
                    if len(strikes_list) > 3:
                        log_message(f"  ... and {len(strikes_list) - 3} more strikes")
                    
                    # Display selected CE strikes if available
                    selected_ce = data.get("optionselectedstrike_CE")
                    if selected_ce:
                        log_message(f"{symbol} | Selected CE Strikes:")
                        for strike, strike_data in selected_ce.items():
                            ltp = strike_data.get("optionltp")
                            instrument_id = strike_data.get("instrument_id")
                            log_message(f"  Strike {strike}: LTP = {ltp}, Instrument ID = {instrument_id}")
                        
                        # Calculate and display premium difference
                        strikes = list(selected_ce.keys())
                        if len(strikes) == 2:
                            strike1, strike2 = strikes[0], strikes[1]  # Higher and lower strikes
                            ltp1 = selected_ce[strike1].get("optionltp")
                            ltp2 = selected_ce[strike2].get("optionltp")
                            lot_size = data.get("LotSize")
                            margin_required = data.get("MarginRequired")
                            
                            if all([ltp1, ltp2, lot_size, margin_required]):
                                premium_diff = (ltp1 - ltp2) * lot_size
                                percentage = abs(premium_diff) / margin_required * 100
                                log_message(f"  Premium Difference: {premium_diff:.2f}")
                                log_message(f"  Percentage: {percentage:.2f}%")
                    else:
                        log_message(f"{symbol} | No selected CE strikes")
                    # Display selected PE strikes if available
                    selected_pe = data.get("optionselectedstrike_PE")
                    if selected_pe:
                        log_message(f"{symbol} | Selected PE Strikes:")
                        for strike, strike_data in selected_pe.items():
                            ltp = strike_data.get("optionltp")
                            instrument_id = strike_data.get("instrument_id")
                            log_message(f"  Strike {strike}: LTP = {ltp}, Instrument ID = {instrument_id}")
                        strikes = list(selected_pe.keys())
                        if len(strikes) == 2:
                            strike1, strike2 = strikes[0], strikes[1]
                            ltp1 = selected_pe[strike1].get("optionltp")
                            ltp2 = selected_pe[strike2].get("optionltp")
                            lot_size = data.get("LotSize")
                            margin_required = data.get("MarginRequired")
                            if all([ltp1, ltp2, lot_size, margin_required]):
                                premium_diff = (ltp2 - ltp1) * lot_size
                                percentage = abs(premium_diff) / margin_required * 100
                                log_message(f"  Premium Difference: {premium_diff:.2f}")
                                log_message(f"  Percentage: {percentage:.2f}%")
                    else:
                        log_message(f"{symbol} | No selected PE strikes")
                else:
                    log_message(f"{symbol} | Strike Range: Not calculated")
            else:
                log_message(f"{symbol} | LTP: Not available")
        
        log_message("LTP fetch completed.")
        
    except Exception as e:
        log_message(f"Error during scanner run: {str(e)}")
        import traceback
        traceback.print_exc()

    scanner_status = "stopped"
    return jsonify({"status": "success", "message": "Scanner ran once."})

@app.route('/api/stop_scanner', methods=['POST'])
def stop_scanner():
    global scanner_status
    if scanner_status != "running":
        return jsonify({"status": "error", "message": "Scanner is not running"})
    scanner_status = "stopped"
    log_message("Scanner stopped by user.")
    return jsonify({"status": "success", "message": "Scanner stopped"})

@app.route('/api/reload_settings', methods=['POST'])
def reload_settings():
    global result_data
    try:
        get_user_settings()  # Load from CSV and fetch instrument IDs
        result_data = get_result_dict()
        log_message("Loaded settings from TradeSettings.csv:")
        print("result_dict: ", result_data) 
        for key, value in result_data.items():
            symbol = value.get("Symbol")
            expiry = value.get("Expiry")
            qty = value.get("Quantity")
            lot_size = value.get("LotSize")
            fut_id = value.get("NSEFOexchangeInstrumentID")
            eq_id = value.get("NSECMexchangeInstrumentID")
            log_message(f"{symbol} | Expiry: {expiry} | Qty: {qty} | LotSize: {lot_size} | FUT_ID: {fut_id} | EQ_ID: {eq_id}")

        
        log_message(f"Future_instrument_id_list: {Future_instrument_id_list}")
        log_message(f"Equity_instrument_id_list: {Equity_instrument_id_list}")
        log_message("-" * 50)

        return jsonify({"status": "success", "message": "Settings loaded from CSV."})
    
    
    except Exception as e:
        log_message(f"Error loading settings: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/get_logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": logs})

@app.route('/api/selected_strikes', methods=['GET'])
def get_selected_strikes():
    from main import result_dict
    selected_strikes_list = []
    for unique_key, params in result_dict.items():
        symbol = params.get("Symbol")
        expiry = params.get("Expiry")
        # Collect CE strikes
        selected_ce = params.get("optionselectedstrike_CE")
        if selected_ce:
            for strike, strike_data in selected_ce.items():
                selected_strikes_list.append({
                    "symbol": symbol,
                    "strike": strike,
                    "optiontype": "CE",
                    "expiry": expiry,
                    "instrument_id": strike_data.get("instrument_id")
                })
        # Collect PE strikes
        selected_pe = params.get("optionselectedstrike_PE")
        if selected_pe:
            for strike, strike_data in selected_pe.items():
                selected_strikes_list.append({
                    "symbol": symbol,
                    "strike": strike,
                    "optiontype": "PE",
                    "expiry": expiry,
                    "instrument_id": strike_data.get("instrument_id")
                })
    # Sort so that same symbol strikes are together
    selected_strikes_list.sort(key=lambda x: (x["symbol"], x["optiontype"], x["strike"]))
    print("[DEBUG] API selected_strikes_list:", selected_strikes_list)
    return jsonify({"selected_strikes": selected_strikes_list})

if __name__ == '__main__':
    app.run(debug=True, port=5000) 