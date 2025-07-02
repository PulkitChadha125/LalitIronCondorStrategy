from flask import Flask, render_template, jsonify, request
import csv
import json
from datetime import datetime
from main import login_marketdata_api, login_interactive_api, get_user_settings, get_result_dict, Future_instrument_id_list, Equity_instrument_id_list
import logging
import os

app = Flask(__name__)

scanner_status = "stopped"
logs = []
market_data_logged_in = False
interactive_logged_in = False
xts_marketdata_obj = None  # Global to store the API object
result_data = None

# New variables for incremental scanning
incremental_scanner_status = "stopped"
current_symbol_index = 0
symbols_to_scan = []
incremental_results = {}

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
        
        # Use main_strategy to handle all the processing in one go
        from main import main_strategy
        log_message("Running main strategy...")
        main_strategy()
        
        # Note: All processing (fetch_option_instrument_ids, Option_MarketQuote, strike selection) 
        # is now handled within main_strategy() to avoid duplication

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
                    "instrument_id": strike_data.get("instrument_id"),
                    "optionltp": strike_data.get("optionltp"),
                    "unique_key": unique_key
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
                    "instrument_id": strike_data.get("instrument_id"),
                    "optionltp": strike_data.get("optionltp"),
                    "unique_key": unique_key
                })
    # Sort so that same symbol strikes are together
    selected_strikes_list.sort(key=lambda x: (x["symbol"], x["optiontype"], x["strike"]))
    print("[DEBUG] API selected_strikes_list:", selected_strikes_list)
    return jsonify({"selected_strikes": selected_strikes_list})

@app.route('/api/place_order', methods=['POST'])
def place_order_api():
    """API endpoint to place orders via buy/sell buttons"""
    try:
        from main import result_dict, xt, place_order
        
        data = request.get_json()
        symbol = data.get("symbol")
        strike = data.get("strike")
        optiontype = data.get("optiontype")
        order_side = data.get("order_side")  # "BUY" or "SELL"
        unique_key = data.get("unique_key")
        price = data.get("price")
        
        if not all([symbol, strike, optiontype, order_side, unique_key]):
            return jsonify({"status": "error", "message": "Missing required parameters"})
        
        # Convert strike to integer since dictionary keys are integers
        try:
            strike = int(strike)
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": f"Invalid strike value: {strike}"})
        
        # Get the params from result_dict using unique_key
        params = result_dict.get(unique_key)
        if not params:
            return jsonify({"status": "error", "message": f"Symbol {symbol} not found in result_dict"})
        
        # Get the selected strikes based on option type
        selected_strikes_key = f"optionselectedstrike_{optiontype}"
        selected_strikes = params.get(selected_strikes_key)
        
        # Debug logging
        log_message(f"[DEBUG] Looking for strike {strike} (type: {type(strike)}) in {optiontype} strikes")
        log_message(f"[DEBUG] Available strikes: {list(selected_strikes.keys()) if selected_strikes else 'None'}")
        log_message(f"[DEBUG] Strike types: {[type(k) for k in (selected_strikes.keys() if selected_strikes else [])]}")
        
        if not selected_strikes:
            return jsonify({"status": "error", "message": f"No {optiontype} strikes selected for {symbol}"})
        
        if strike not in selected_strikes:
            return jsonify({"status": "error", "message": f"Strike {strike} not found in selected {optiontype} strikes. Available: {list(selected_strikes.keys())}"})
        
        # Get the strike data
        strike_data = selected_strikes[strike]
        instrument_id = strike_data.get("instrument_id")
        optionltp = strike_data.get("optionltp")
        
        if not instrument_id or not optionltp:
            return jsonify({"status": "error", "message": f"Missing instrument_id or optionltp for strike {strike}"})
        
        # Calculate order quantity: lot_size * quantity
        lot_size = params.get("LotSize")
        quantity = params.get("Quantity")
        
        if not lot_size or not quantity:
            return jsonify({"status": "error", "message": "Missing lot_size or quantity"})
        
        order_quantity = lot_size * quantity
        
        # Check if interactive API is logged in
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in. Please login first."})
        
        # Use the provided price if given, else fallback to optionltp
        order_price = None
        try:
            order_price = float(price) if price not in (None, "") else float(optionltp)
        except Exception:
            order_price = float(optionltp)
        
        # Place the order
        response = place_order(
            nfo_ins_id=instrument_id,
            order_quantity=order_quantity,
            order_side=order_side,
            price=order_price,
            unique_key=unique_key
        )
        
        log_message(f"[ORDER] {order_side} order placed for {symbol} {strike} {optiontype}")
        log_message(f"[ORDER] Quantity: {order_quantity}, Price: {order_price}, Response: {response}")
        
        return jsonify({
            "status": "success", 
            "message": f"{order_side} order placed successfully",
            "order_details": {
                "symbol": symbol,
                "strike": strike,
                "optiontype": optiontype,
                "order_side": order_side,
                "quantity": order_quantity,
                "price": order_price,
                "response": response
            }
        })
        
    except Exception as e:
        log_message(f"[ERROR] Failed to place order: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to place order: {str(e)}"})

@app.route('/api/login_status', methods=['GET'])
def get_login_status():
    """API endpoint to check login status of both APIs"""
    try:
        from main import xts_marketdata, xt
        
        market_data_status = "logged_in" if (xts_marketdata and xts_marketdata.token) else "not_logged_in"
        interactive_status = "logged_in" if (xt and xt.token) else "not_logged_in"
        
        return jsonify({
            "market_data_api": market_data_status,
            "interactive_api": interactive_status
        })
    except Exception as e:
        return jsonify({
            "market_data_api": "error",
            "interactive_api": "error",
            "error": str(e)
        })

@app.route('/netposition')
def netposition():
    """Net Position Panel page"""
    return render_template('netposition.html')

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions from the net position fetcher"""
    try:
        from main import get_net_positions
        positions = get_net_positions()
        return jsonify({"status": "success", "positions": positions})
    except Exception as e:
        log_message(f"Error getting positions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/close_position', methods=['POST'])
def close_position():
    """API endpoint to close a specific position"""
    try:
        from main import xt
        
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in"})
        
        data = request.get_json()
        position_id = data.get('position_id')
        
        if not position_id:
            return jsonify({"status": "error", "message": "Position ID is required"})
        
        # Close position using XTS API
        response = xt.close_position(position_id)
        
        if response.get('type') == 'success':
            log_message(f"[POSITION] Closed position {position_id}")
            return jsonify({
                "status": "success",
                "message": "Position closed successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to close position: {response.get('description', 'Unknown error')}"
            })
            
    except Exception as e:
        log_message(f"[ERROR] Failed to close position: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to close position: {str(e)}"})

@app.route('/api/close_all_positions', methods=['POST'])
def close_all_positions():
    """API endpoint to close all positions"""
    try:
        from main import xt
        
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in"})
        
        # Get all positions first
        positions_response = xt.get_positions()
        
        if positions_response.get('type') != 'success':
            return jsonify({
                "status": "error",
                "message": f"Failed to get positions: {positions_response.get('description', 'Unknown error')}"
            })
        
        positions = positions_response.get('result', [])
        closed_count = 0
        
        for position in positions:
            if position.get('Quantity', 0) > 0:  # Only close active positions
                try:
                    response = xt.close_position(position.get('PositionID'))
                    if response.get('type') == 'success':
                        closed_count += 1
                except Exception as e:
                    log_message(f"[ERROR] Failed to close position {position.get('PositionID')}: {str(e)}")
        
        log_message(f"[POSITION] Closed {closed_count} positions")
        return jsonify({
            "status": "success",
            "message": f"Closed {closed_count} positions successfully"
        })
        
    except Exception as e:
        log_message(f"[ERROR] Failed to close all positions: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to close all positions: {str(e)}"})

@app.route('/api/close_selected_positions', methods=['POST'])
def close_selected_positions():
    """API endpoint to close selected positions"""
    try:
        from main import xt
        
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in"})
        
        data = request.get_json()
        position_ids = data.get('position_ids', [])
        
        if not position_ids:
            return jsonify({"status": "error", "message": "No position IDs provided"})
        
        closed_count = 0
        
        for position_id in position_ids:
            try:
                response = xt.close_position(position_id)
                if response.get('type') == 'success':
                    closed_count += 1
            except Exception as e:
                log_message(f"[ERROR] Failed to close position {position_id}: {str(e)}")
        
        log_message(f"[POSITION] Closed {closed_count} selected positions")
        return jsonify({
            "status": "success",
            "message": f"Closed {closed_count} positions successfully"
        })
        
    except Exception as e:
        log_message(f"[ERROR] Failed to close selected positions: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to close selected positions: {str(e)}"})

@app.route('/api/export_positions', methods=['GET'])
def export_positions():
    """API endpoint to export positions to CSV"""
    try:
        from main import xt
        import csv
        from io import StringIO
        
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in"})
        
        # Get positions
        response = xt.get_positions()
        
        if response.get('type') != 'success':
            return jsonify({"status": "error", "message": "Failed to fetch positions"})
        
        positions = response.get('result', [])
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Symbol', 'Strike', 'Option Type', 'Quantity', 'Average Price', 
            'LTP', 'P&L', 'Status', 'Order Side', 'Exchange Segment', 'Trade Date'
        ])
        
        # Write data
        for pos in positions:
            avg_price = pos.get('AveragePrice', 0)
            ltp = pos.get('LastTradedPrice', 0)
            quantity = pos.get('Quantity', 0)
            
            # Calculate P&L
            pnl = (ltp - avg_price) * quantity if pos.get('OrderSide') == 'BUY' else (avg_price - ltp) * quantity
            
            writer.writerow([
                pos.get('ScripName', ''),
                pos.get('StrikePrice', ''),
                pos.get('OptionType', ''),
                quantity,
                avg_price,
                ltp,
                pnl,
                'ACTIVE' if quantity > 0 else 'CLOSED',
                pos.get('OrderSide', ''),
                pos.get('ExchangeSegment', ''),
                pos.get('TradeDate', '')
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=positions_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
        
    except Exception as e:
        log_message(f"[ERROR] Failed to export positions: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to export positions: {str(e)}"})

@app.route('/api/position_history', methods=['GET'])
def get_position_history():
    """API endpoint to get position history"""
    try:
        from main import xt
        
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in"})
        
        # Get position history from XTS API
        response = xt.get_position_history()
        
        if response.get('type') == 'success':
            history = response.get('result', [])
            return jsonify({
                "status": "success",
                "history": history
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to get position history: {response.get('description', 'Unknown error')}"
            })
            
    except Exception as e:
        log_message(f"[ERROR] Failed to get position history: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get position history: {str(e)}"})

@app.route('/api/exit_position', methods=['POST'])
def exit_position_api():
    """API endpoint to exit positions from net position panel"""
    try:
        from main import xt, place_order
        
        data = request.get_json()
        instrument_id = data.get("instrument_id")
        order_quantity = data.get("order_quantity")
        order_side = data.get("order_side")  # "BUY" or "SELL"
        price = data.get("price", 0)  # Market order if 0
        symbol = data.get("symbol", "")
        
        if not all([instrument_id, order_quantity, order_side]):
            return jsonify({"status": "error", "message": "Missing required parameters: instrument_id, order_quantity, order_side"})
        
        # Check if interactive API is logged in
        if not xt or not xt.token:
            return jsonify({"status": "error", "message": "Interactive API not logged in. Please login first."})
        
        # Place the exit order
        response = place_order(
            nfo_ins_id=instrument_id,
            order_quantity=order_quantity,
            order_side=order_side,
            price=price,
            unique_key=f"exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        log_message(f"[EXIT ORDER] {order_side} order placed for {symbol}")
        log_message(f"[EXIT ORDER] Quantity: {order_quantity}, Price: {price}, Response: {response}")
        
        return jsonify({
            "status": "success", 
            "message": f"{order_side} exit order placed successfully",
            "order_details": {
                "symbol": symbol,
                "order_side": order_side,
                "quantity": order_quantity,
                "price": price,
                "response": response
            }
        })
        
    except Exception as e:
        log_message(f"[ERROR] Failed to place exit order: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to place exit order: {str(e)}"})

@app.route('/api/start_incremental_scanner', methods=['POST'])
def start_incremental_scanner():
    global incremental_scanner_status, current_symbol_index, symbols_to_scan, incremental_results, xts_marketdata_obj
    
    if incremental_scanner_status == "running":
        return jsonify({"status": "error", "message": "Incremental scanner is already running"})
    
    if not xts_marketdata_obj or not hasattr(xts_marketdata_obj, 'token') or not xts_marketdata_obj.token:
        log_message("[ERROR] Market Token is missing. Please login again.")
        return jsonify({"status": "error", "message": "Market Token is missing. Please login again."})

    if not market_data_logged_in or not xts_marketdata_obj:
        log_message("Please login to Market Data API before starting the scanner.")
        return jsonify({"status": "error", "message": "Login to Market Data API first."})

    try:
        # Load settings and get symbol list
        from main import get_user_settings, set_marketdata_connection
        
        # Set the global market data connection
        set_marketdata_connection(xts_marketdata_obj)
        
        # Load settings and get symbol list
        get_user_settings()
        from main import result_dict
        
        if not result_dict:
            log_message("No symbols found in TradeSettings.csv")
            return jsonify({"status": "error", "message": "No symbols found in TradeSettings.csv"})
        
        # Initialize incremental scanning variables
        symbols_to_scan = list(result_dict.keys())
        current_symbol_index = 0
        # Don't clear incremental_results - preserve previous results
        if not incremental_results:
            incremental_results = {}
        incremental_scanner_status = "running"
        
        existing_results_count = len(incremental_results)
        if existing_results_count > 0:
            log_message(f"Incremental scanner started with {len(symbols_to_scan)} symbols (adding to {existing_results_count} existing results)")
            message = f"Incremental scanner started with {len(symbols_to_scan)} symbols (adding to {existing_results_count} existing results)"
        else:
            log_message(f"Incremental scanner started with {len(symbols_to_scan)} symbols")
            message = f"Incremental scanner started with {len(symbols_to_scan)} symbols"
        
        log_message("Processing symbols one by one...")
        
        # Start the first symbol processing
        process_next_symbol()
        
        return jsonify({
            "status": "success", 
            "message": message,
            "total_symbols": len(symbols_to_scan),
            "existing_results": existing_results_count
        })
        
    except Exception as e:
        log_message(f"Error starting incremental scanner: {str(e)}")
        incremental_scanner_status = "stopped"
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Error starting scanner: {str(e)}"})

def process_next_symbol():
    """Process the next symbol in the queue"""
    global current_symbol_index, symbols_to_scan, incremental_scanner_status, incremental_results, xts_marketdata_obj
    
    if incremental_scanner_status != "running" or current_symbol_index >= len(symbols_to_scan):
        incremental_scanner_status = "stopped"
        log_message("Incremental scanner completed.")
        return
    
    try:
        unique_key = symbols_to_scan[current_symbol_index]
        from main import result_dict
        symbol_data = result_dict.get(unique_key, {})
        symbol = symbol_data.get("Symbol", "Unknown")
        
        log_message(f"Processing symbol {current_symbol_index + 1}/{len(symbols_to_scan)}: {symbol}")
        
        # Process this single symbol
        result = process_single_symbol(unique_key, symbol_data)
        
        # Store the result
        incremental_results[unique_key] = result
        
        # Log the result
        if result.get("success"):
            log_message(f"✓ {symbol} completed successfully")
            if result.get("selected_strikes"):
                log_message(f"  Selected strikes: {result['selected_strikes']}")
        else:
            log_message(f"✗ {symbol} failed: {result.get('error', 'Unknown error')}")
        
        # Move to next symbol
        current_symbol_index += 1
        
        # Process next symbol after a short delay
        import threading
        threading.Timer(1.0, process_next_symbol).start()
        
    except Exception as e:
        log_message(f"Error processing symbol: {str(e)}")
        current_symbol_index += 1
        # Continue with next symbol
        import threading
        threading.Timer(1.0, process_next_symbol).start()

def process_single_symbol(unique_key, symbol_data):
    """Process a single symbol and return the result"""
    try:
        symbol = symbol_data.get("Symbol")
        option_type = symbol_data.get("OptionType")
        
        log_message(f"Fetching LTP for {symbol}...")
        
        # Step 1: Fetch Future LTP for this symbol (per-symbol)
        from main import Future_MarketQuote_for_symbol
        Future_MarketQuote_for_symbol(xts_marketdata_obj, unique_key)
        
        # Get updated data
        from main import result_dict
        updated_data = result_dict.get(unique_key, {})
        fut_ltp = updated_data.get("Futltp")
        optionchain = updated_data.get("Optionchain")
        
        if fut_ltp is None:
            return {"success": False, "error": "Could not fetch LTP"}
        
        log_message(f"{symbol} LTP: {fut_ltp}")
        
        if not optionchain:
            return {"success": False, "error": "No option chain available"}
        
        # Step 2: Fetch option instrument IDs for this symbol (per-symbol)
        log_message(f"Fetching option instrument IDs for {symbol}...")
        from main import fetch_option_instrument_ids_for_symbol
        fetch_option_instrument_ids_for_symbol(xts_marketdata_obj, unique_key)
        
        # Step 3: Fetch option LTPs for this symbol (per-symbol)
        log_message(f"Fetching option LTPs for {symbol}...")
        from main import Option_MarketQuote_for_symbol
        Option_MarketQuote_for_symbol(xts_marketdata_obj, unique_key)
        
        # Step 4: Select strikes for this symbol
        log_message(f"Selecting strikes for {symbol}...")
        selected_strikes = None
        if option_type == "CE":
            from main import select_ce_strikes
            selected_strikes = select_ce_strikes(updated_data)
        elif option_type == "PE":
            from main import select_pe_strikes
            selected_strikes = select_pe_strikes(updated_data)
        
        # Update the result_dict with selected strikes (always, even if None)
        if option_type == "CE":
            updated_data["optionselectedstrike_CE"] = selected_strikes if selected_strikes else None
        else:
            updated_data["optionselectedstrike_PE"] = selected_strikes if selected_strikes else None
        result_dict[unique_key] = updated_data
        
        return {
            "success": True,
            "symbol": symbol,
            "ltp": fut_ltp,
            "strikes_count": len(optionchain),
            "selected_strikes": list(selected_strikes.keys()) if selected_strikes else [],
            "option_type": option_type
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def fetch_single_symbol_option_ids(unique_key, symbol_data):
    """Fetch option instrument IDs for a single symbol"""
    try:
        symbol = symbol_data.get("Symbol")
        optionchain = symbol_data.get("Optionchain", {})
        expiry = symbol_data.get("Expiry")
        option_type = symbol_data.get("OptionType")
        
        if not optionchain or not expiry or not option_type:
            return False
        
        # Convert expiry to API format
        import datetime
        expiry_api_format = datetime.datetime.strptime(expiry, "%d-%m-%Y").strftime("%d%b%Y")
        
        successful_fetches = 0
        for strike_price in optionchain.keys():
            try:
                opt_response = xts_marketdata_obj.get_option_symbol(
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
                else:
                    optionchain[strike_price]['instrument_id'] = None
                    
            except Exception as e:
                optionchain[strike_price]['instrument_id'] = None
        
        # Update the result_dict
        from main import result_dict
        symbol_data["Optionchain"] = optionchain
        result_dict[unique_key] = symbol_data
        
        return successful_fetches > 0
        
    except Exception as e:
        log_message(f"Error fetching option IDs for {symbol}: {str(e)}")
        return False

def fetch_single_symbol_option_ltps(unique_key, symbol_data):
    """Fetch option LTPs for a single symbol"""
    try:
        symbol = symbol_data.get("Symbol")
        optionchain = symbol_data.get("Optionchain", {})
        
        if not optionchain:
            return False
        
        # Collect instrument IDs for this symbol
        option_instrument_id_list = []
        for strike_price, strike_data in optionchain.items():
            instrument_id = strike_data.get("instrument_id")
            if instrument_id:
                option_instrument_id_list.append({
                    "exchangeSegment": 2,  # NSEFO
                    "exchangeInstrumentID": instrument_id
                })
        
        if not option_instrument_id_list:
            return False
        
        # Fetch LTPs in chunks of 25
        from main import chunk_instruments
        chunk_size = 25
        
        for chunk in chunk_instruments(option_instrument_id_list, chunk_size):
            try:
                response = xts_marketdata_obj.get_quote(
                    Instruments=chunk,
                    xtsMessageCode=1501,
                    publishFormat='JSON'
                )
                
                if response and response.get("type") == "success":
                    quote_strings = response["result"].get("listQuotes", [])
                    
                    for quote_str in quote_strings:
                        try:
                            quote_data = json.loads(quote_str)
                            instrument_id = quote_data.get("ExchangeInstrumentID")
                            ltp = quote_data.get("Touchline", {}).get("LastTradedPrice", 0)
                            
                            # Find the strike price for this instrument ID
                            for strike_price, strike_data in optionchain.items():
                                if strike_data.get("instrument_id") == instrument_id:
                                    strike_data["optionltp"] = ltp
                                    break
                                    
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                log_message(f"Error fetching LTPs for chunk: {str(e)}")
                continue
        
        # Update the result_dict
        from main import result_dict
        symbol_data["Optionchain"] = optionchain
        result_dict[unique_key] = symbol_data
        
        return True
        
    except Exception as e:
        log_message(f"Error fetching option LTPs for {symbol}: {str(e)}")
        return False

@app.route('/api/stop_incremental_scanner', methods=['POST'])
def stop_incremental_scanner():
    global incremental_scanner_status
    if incremental_scanner_status != "running":
        return jsonify({"status": "error", "message": "Incremental scanner is not running"})
    incremental_scanner_status = "stopped"
    log_message("Incremental scanner stopped by user.")
    return jsonify({"status": "success", "message": "Incremental scanner stopped"})

@app.route('/api/incremental_scanner_status', methods=['GET'])
def get_incremental_scanner_status():
    global incremental_scanner_status, current_symbol_index, symbols_to_scan, incremental_results
    
    return jsonify({
        "status": incremental_scanner_status,
        "current_index": current_symbol_index,
        "total_symbols": len(symbols_to_scan),
        "completed_symbols": len(incremental_results),
        "progress_percentage": (current_symbol_index / len(symbols_to_scan) * 100) if symbols_to_scan else 0,
        "results": incremental_results
    })

@app.route('/api/clear_incremental_results', methods=['POST'])
def clear_incremental_results():
    global incremental_results, current_symbol_index, symbols_to_scan, incremental_scanner_status
    
    if incremental_scanner_status == "running":
        return jsonify({"status": "error", "message": "Cannot clear results while scanner is running"})
    
    incremental_results = {}
    current_symbol_index = 0
    symbols_to_scan = []
    log_message("Incremental scanner results cleared.")
    
    return jsonify({"status": "success", "message": "Incremental scanner results cleared"})

if __name__ == '__main__':
    app.run(debug=True, port=5000) 