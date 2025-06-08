import os
import json
import logging
import threading
import time
from datetime import datetime
import webbrowser
import requests
import pyotp
from SmartApi import SmartConnect

from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty, BooleanProperty

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDFloatingActionButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.uix.screenmanager import Screen

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Color Palette: Deep Teal, Coral, Cream, Dark Slate
COLOR_PALETTE = {
    "primary": "#006D77",  # Deep Teal
    "secondary": "#FF9B85",  # Coral
    "background": "#F8F4E3",  # Cream
    "surface": "#2F4858",  # Dark Slate
    "text_light": "#FFFFFF",
    "text_dark": "#333333"
}

# Android-specific imports and setup
ANDROID = False
if platform == 'android':
    try:
        from android.permissions import Permission, check_permission, request_permissions
        from android.storage import app_storage_path
        ANDROID = True
    except ImportError:
        logger.warning("Android modules not available - running in non-Android mode")

def request_android_permissions():
    if not ANDROID:
        return
        
    try:
        required_permissions = [
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.INTERNET,
            Permission.ACCESS_NETWORK_STATE
        ]
        
        permissions_to_request = [
            perm for perm in required_permissions 
            if not check_permission(perm)
        ]
        
        if permissions_to_request:
            request_permissions(permissions_to_request)
    except Exception as e:
        logger.error(f"Android permission request failed: {str(e)}")

def get_data_dir():
    if ANDROID:
        try:
            from android.storage import app_storage_path
            data_dir = os.path.join(app_storage_path(), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            return data_dir
        except Exception as e:
            logger.error(f"Android storage error: {str(e)}")
            return os.path.expanduser('~/twentyfive_data')
    else:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir

class ClickableImage(ButtonBehavior, Image):
    def on_release(self):
        logger.info("Opening Instagram link")
        webbrowser.open("https://www.instagram.com/twenty.five_sg/")

class AnimatedLabel(MDLabel):
    anim_font_size = NumericProperty(0)
    anim_opacity = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(anim_font_size=self.update_font_size)
        self.bind(anim_opacity=self.update_opacity)
    
    def update_font_size(self, instance, value):
        self.font_size = value
    
    def update_opacity(self, instance, value):
        self.opacity = value

class FirstScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.start_animations, 1.0)
        Clock.schedule_once(self.go_to_main, 5.0)

    def start_animations(self, dt):
        anim = Animation(anim_font_size=50, anim_opacity=1, duration=1.5, t='out_back')
        anim.start(self.ids.main_label)
        Clock.schedule_once(self.animate_shaukeen, 1.0)

    def animate_shaukeen(self, dt):
        anim = Animation(anim_font_size=25, anim_opacity=1, duration=1.5, t='out_back')
        anim.start(self.ids.sha_label)

    def go_to_main(self, dt):
        self.manager.current = 'main'

class StockListItem(OneLineAvatarIconListItem):
    pass

class MainScreen(MDScreen):
    pass

class CredentialsInputScreen(MDScreen):
    is_active = BooleanProperty(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_file = os.path.join(get_data_dir(), "config.json")

    def on_pre_enter(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.ids.username_field.text = config.get('USERNAME', '')
                    self.ids.pin_field.text = config.get('PIN', '')
                    self.ids.api_key_field.text = config.get('API_KEY', '')
                    self.ids.token_field.text = config.get('TOKEN', '')
                    self.ids.quantity_field.text = config.get('QTY', '1')
                    self.is_active = config.get('STATUS', 'ON') == 'ON'
            except Exception as e:
                logger.error(f"Error loading config: {str(e)}")

    def toggle_active(self, *args):
        self.is_active = not self.is_active
        self.save_credentials()

    def save_credentials(self, *args):
        config = {
            "STATUS": "ON" if self.is_active else "OFF",
            "API_KEY": self.ids.api_key_field.text,
            "USERNAME": self.ids.username_field.text,
            "PIN": self.ids.pin_field.text,
            "TOKEN": self.ids.token_field.text,
            "QTY": self.ids.quantity_field.text,
            "LIST": self.get_watchlist_symbols()
        }
        
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
            
            self.ids.status_label.text = "[color=00AA00]✓ Config saved successfully![/color]"
            self.ids.status_label.markup = True
            
            if self.is_active:
                MDApp.get_running_app().start_background_process()
        except Exception as e:
            self.ids.status_label.text = f"[color=FF0000]✗ Error: {str(e)}[/color]"
            self.ids.status_label.markup = True
    
    def get_watchlist_symbols(self):
        main_screen = self.manager.get_screen('main')
        return [item.text.split(" - ")[0] for item in main_screen.ids.watchlist.children]
    
    def go_back(self, *args):
        self.manager.current = "main"

class TwentyFiveApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        self.current_stock = None
        self.dialog = None
        self.config_file = os.path.join(get_data_dir(), "config.json")
        self.background_thread = None
        self.stop_background = False
        self.color_palette = COLOR_PALETTE
        self.has_logo = False
        logger.info("TwentyFiveApp initialized")
    
    def build(self):
        logger.info("Building application UI")
        Window.keyboard_anim_args = {'d': .2, 't': 'in_out_expo'}
        Window.softinput_mode = 'below_target'
        
        if platform in ['win', 'linux', 'macosx']:
            Window.size = (400, 700)
        
        # Check for logo
        logo_paths = [
            os.path.join('data', 'TFlogo.png'),
            os.path.join('assets', 'TFlogo.png'),
            os.path.join(os.path.dirname(__file__), 'data', 'TFlogo.png')
        ]
        self.has_logo = any(os.path.exists(path) for path in logo_paths)
        
        # Load KV file with fallback
        kv_paths = [
            os.path.join('data', 'twentyfive.kv'),
            os.path.join('assets', 'twentyfive.kv'),
            os.path.join(os.path.dirname(__file__), 'twentyfive.kv')
        ]
        
        for path in kv_paths:
            try:
                if os.path.exists(path):
                    return Builder.load_file(path)
            except Exception as e:
                logger.error(f"Failed to load KV file from {path}: {str(e)}")
        
        # Fallback UI if KV loading fails
        from kivymd.uix.screenmanager import MDScreenManager
        sm = MDScreenManager()
        sm.add_widget(MDScreen(name='error'))
        return sm
    
    def on_start(self):
        logger.info("Application started - initializing components")
        request_android_permissions()
        
        try:
            self.initialize_session()
            self.load_watchlist_from_config()
            self.start_background_process()
        except Exception as e:
            logger.error(f"Error during startup: {str(e)}")
            self.show_error_dialog("Startup Error", f"Application failed to start: {str(e)}")


    def initialize_session(self):
        logger.info("Initializing NSE session")
        try:
            self.session.get("https://www.nseindia.com", timeout=5)
            self.session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=5)
            logger.info("NSE session initialized successfully")
        except Exception as e:
            logger.error(f"Session initialization failed: {str(e)}")
            self.show_error_dialog("Connection Error", "Failed to initialize connection to NSE")

    def on_stop(self):
        logger.info("Application stopping - cleaning up resources")
        self.stop_background = True
        if self.background_thread and self.background_thread.is_alive():
            logger.debug("Waiting for background thread to finish")
            self.background_thread.join()
        logger.info("Application shutdown complete")

    def start_background_process(self):
        if self.background_thread and self.background_thread.is_alive():
            logger.warning("Background thread already running")
            return
            
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if config.get('STATUS') == 'ON':
                        logger.info("Starting background trading process")
                        self.stop_background = False
                        self.background_thread = threading.Thread(
                            target=self.run_background_process,
                            name="TradingBackgroundThread"
                        )
                        self.background_thread.daemon = True
                        self.background_thread.start()
                    else:
                        logger.info("Background process is disabled in config")
            except Exception as e:
                logger.error(f"Error reading config file: {str(e)}")
        else:
            logger.warning("Config file not found - background process not started")

    def run_background_process(self):
        """Run the main trading logic in background"""
        logger.info("Background trading process started")
        
        while not self.stop_background:
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.debug("Loaded config file")
                
                if config.get('STATUS') != 'ON':
                    logger.info("Background process disabled in config - stopping")
                    break
                
                logger.info("Initializing AngelOne API connection")
                smartApi = SmartConnect(api_key=config['API_KEY'])
                totp = pyotp.TOTP(config['TOKEN']).now()
                smartApi.generateSession(config['USERNAME'], config['PIN'], totp)
                logger.info("AngelOne API session generated successfully")
                
                if datetime.now().day == 25:
                    logger.info("Checking for quantity doubling (25th of month)")
                    try:
                        with open(self.config_file, 'r+') as f_config:
                            config = json.load(f_config)
                            logger.debug("Loaded config for quantity doubling check")

                            doubled_file = os.path.join(get_data_dir(), ".doubled")
                            try:
                                with open(doubled_file, 'r') as f_doubled:
                                    doubled_data = json.load(f_doubled)
                                    logger.debug("Loaded doubled tracking file")
                            except (FileNotFoundError, json.JSONDecodeError):
                                doubled_data = {"LAST_DOUBLED": ""}
                                logger.info("Created new doubled tracking file")

                            current_month_year = datetime.now().strftime("%Y-%m")
                            last_doubled = doubled_data.get('LAST_DOUBLED', "")

                            if last_doubled != current_month_year:
                                logger.info(f"Doubling quantity for {current_month_year}")
                                
                                old_qty = config['QTY']
                                config['QTY'] = str(int(config['QTY']) * 2)
                                logger.info(f"Quantity changed from {old_qty} to {config['QTY']}")

                                doubled_data['LAST_DOUBLED'] = current_month_year

                                f_config.seek(0)
                                json.dump(config, f_config, indent=4)
                                f_config.truncate()
                                logger.debug("Saved updated config file")

                                with open(doubled_file, 'w') as f_doubled:
                                    json.dump(doubled_data, f_doubled, indent=4)
                                logger.debug("Saved doubled tracking file")

                    except Exception as e:
                        logger.error(f"Error in quantity doubling process: {str(e)}")
                
                logger.info("Waiting for market open time (09:30)")
                while True:
                    now = datetime.now()
                    current_time = now.strftime("%H:%M")
                    if current_time == "09:30":
                        logger.info("Market open time reached - proceeding with trading")
                        break
                    if self.stop_background:
                        logger.info("Background process stopped while waiting for market open")
                        return
                    time.sleep(1)
                
                logger.info("Saving BTS values")
                self.save_bts_values(config)
                time.sleep(2)
                logger.info("Placing orders")
                self.place_all_orders(config)
                
                logger.info("Trading complete - waiting until next day")
                time.sleep(86400 - 60)
                
            except Exception as e:
                logger.error(f"Error in background process: {str(e)}", exc_info=True)
                time.sleep(60)

    def save_bts_values(self, config, max_retries=5):
        """Save stock values to JSON file with retry mechanism"""
        company_names = config['LIST']
        results = {}
        logger.info(f"Saving BTS values for {len(company_names)} stocks")

        for name in company_names:
            retry_count = 0
            success = False
            logger.debug(f"Processing stock: {name}")

            while retry_count < max_retries and not success:
                try:
                    stock = self.get_stock_value(name)
                    logger.debug(f"Retrieved stock data for {name}")

                    if not stock:
                        logger.warning(f"Stock details not found for {name}")
                        results[name] = "Details not found"
                        break
                    
                    nse_symbol = stock['symbol'].replace('-EQ', '')
                    logger.debug(f"Fetching NSE price for {nse_symbol}")
                    price_data = self.fetch_nse_price(nse_symbol)

                    if not price_data:
                        logger.warning(f"No price data for {nse_symbol}")
                        raise ValueError(f"No price data for {nse_symbol}")

                    price = price_data.get('intraDayHighLow', {}).get('max')
                    logger.debug(f"Current price for {nse_symbol}: {price}")

                    if not price:
                        logger.warning(f"No valid price for {nse_symbol}")
                        raise ValueError(f"No valid price for {nse_symbol}")

                    d_price = price / 1000
                    limit_price = self.round_to_05(price + (price / 10000))
                    squareoff = self.round_to_05(price + (d_price * 3))
                    stoploss = self.round_to_05(price - d_price)
                    logger.debug(f"Calculated values - Limit: {limit_price}, Squareoff: {squareoff}, Stoploss: {stoploss}")

                    results[name] = {
                        "symbol": stock['symbol'],
                        "name": stock['name'],
                        "token": stock['token'],
                        "exchange": stock['exch_seg'],
                        "price": limit_price,
                        "squareoff": squareoff,
                        "stoploss": stoploss
                    }
                    success = True
                    logger.info(f"Successfully processed {name}")

                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Attempt {retry_count} failed for {name}: {str(e)}")
                    if retry_count == max_retries:
                        results[name] = f"Failed after {max_retries} attempts: {str(e)}"
                        logger.error(f"Final attempt failed for {name}")
                    else:
                        time.sleep(1)

        logger.info("Writing stock data to file")
        stock_data_file = os.path.join(get_data_dir(), "stock_data.json")
        with open(stock_data_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info("Stock data saved successfully")

    def place_all_orders(self, config):
        """Place orders for all stocks in watchlist"""
        logger.info("Starting to place orders")
        
        try:
            stock_data_file = os.path.join(get_data_dir(), "stock_data.json")
            with open(stock_data_file) as f:
                stocks = json.load(f)
                logger.debug(f"Loaded stock data for {len(stocks)} items")
        except Exception as e:
            logger.error(f"Failed to load stock data: {str(e)}")
            return
        
        try:
            smartApi = SmartConnect(api_key=config['API_KEY'])
            totp = pyotp.TOTP(config['TOKEN']).now()
            smartApi.generateSession(config['USERNAME'], config['PIN'], totp)
            logger.info("AngelOne API session created successfully")
        except Exception as e:
            logger.error(f"Failed to create AngelOne session: {str(e)}")
            return
        
        for stock_name, data in stocks.items():
            try:
                if isinstance(data, str):
                    logger.warning(f"Skipping {stock_name} due to error: {data}")
                    continue
                    
                logger.info(f"Placing order for {stock_name} ({data['symbol']})")
                orderparams = {
                    "variety": "ROBO",
                    "tradingsymbol": data['symbol'],
                    "symboltoken": data['token'],
                    "transactiontype": "BUY",
                    "exchange": data['exchange'],
                    "ordertype": "LIMIT",
                    "producttype": "INTRADAY",
                    "duration": "DAY",
                    "price": str(data['price']),
                    "squareoff": str(data['squareoff']),
                    "stoploss": str(data['stoploss']),
                    "quantity": str(config['QTY'])
                }
                logger.debug(f"Order params: {orderparams}")
                
                response = smartApi.placeOrder(orderparams)
                logger.info(f"Order placed successfully for {stock_name}. Response: {response}")
                
            except Exception as e:
                logger.error(f"Failed to place order for {stock_name}: {str(e)}")

    def get_stock_value(self, name):
        """Fetch stock details from AngelOne API"""
        logger.debug(f"Fetching stock value for {name}")
        try:
            data = requests.get("https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=3).json()
            exact_match = next((s for s in data if s['name'].lower() == name.lower()), None)
            if exact_match:
                logger.debug(f"Found exact match for {name}")
                return exact_match
            return next((s for s in data if name.lower() in s['name'].lower()), None)
        except Exception as e:
            logger.error(f"Error fetching data for {name}: {str(e)}")
            return None

    def fetch_nse_price(self, symbol):
        """Fetch current market price from NSE"""
        logger.debug(f"Fetching NSE price for {symbol}")
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US"
            })
            
            session.get("https://www.nseindia.com", timeout=5)
            session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=5)
            
            response = session.get(
                f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Successfully fetched price for {symbol}")
                data = response.json()
                return data.get('priceInfo', {})
            else:
                logger.warning(f"Non-200 response for {symbol}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {str(e)}")
        return None

    def round_to_05(self, value: float) -> float:
        """Round value to nearest 0.05"""
        rounded = round(round(value / 0.05) * 0.05, 2)
        logger.debug(f"Rounded {value} to {rounded}")
        return rounded

    def load_watchlist_from_config(self):
        """Load watchlist from config file if exists"""
        logger.info("Loading watchlist from config")
        
        if not os.path.exists(get_data_dir()):
            os.makedirs(get_data_dir())
            logger.info(f"Created data directory at {get_data_dir()}")
        
        config_path = os.path.join(get_data_dir(), "config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                    if 'LIST' in config:
                        main_screen = self.root.get_screen('main')
                        watchlist = main_screen.ids.watchlist
                        
                        watchlist.clear_widgets()
                        logger.info(f"Loading {len(config['LIST'])} watchlist items")
                        
                        for symbol in config['LIST']:
                            list_item = StockListItem(
                                text=f"{symbol} - ₹0.00",
                                theme_text_color="Custom",
                                text_color=self.color_palette["surface"]
                            )
                            
                            icon = IconLeftWidget(
                                icon="chart-line",
                                theme_text_color="Custom",
                                text_color=self.color_palette["primary"]
                            )
                            list_item.add_widget(icon)
                            
                            watchlist.add_widget(list_item)
                        
                        logger.info("Watchlist loaded successfully")
                        
                        if config['LIST']:
                            Clock.schedule_once(lambda dt: self.update_watchlist_prices(), 1)
                            
                    else:
                        logger.info("No watchlist found in config - starting with empty watchlist")
                        
            except json.JSONDecodeError as e:
                logger.error(f"Config file corrupted: {str(e)}")
                self.show_error_dialog("Config Error", "Configuration file is corrupted")
                
            except Exception as e:
                logger.error(f"Error loading watchlist from config: {str(e)}")
                self.show_error_dialog("Error", f"Failed to load watchlist: {str(e)}")
        else:
            logger.info("No config file found - starting with empty watchlist")
            
            default_config = {
                "STATUS": "OFF",
                "API_KEY": "",
                "USERNAME": "",
                "PIN": "",
                "TOKEN": "",
                "QTY": "1",
                "LIST": []
            }
            
            try:
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info("Created default config file")
            except Exception as e:
                logger.error(f"Failed to create default config: {str(e)}")

    def update_watchlist_prices(self):
        """Update prices for all stocks in watchlist"""
        logger.info("Updating watchlist prices")
        main_screen = self.root.get_screen('main')
        
        for item in main_screen.ids.watchlist.children:
            symbol = item.text.split(" - ")[0]
            
            try:
                price_data = self.fetch_nse_price(symbol)
                
                if price_data and 'lastPrice' in price_data:
                    current_price = price_data['lastPrice']
                    item.text = f"{symbol} - ₹{current_price}"
                    logger.debug(f"Updated price for {symbol}: ₹{current_price}")
                else:
                    logger.warning(f"Could not fetch price for {symbol}")
                    item.text = f"{symbol} - Price N/A"
                    
            except Exception as e:
                logger.error(f"Error updating price for {symbol}: {str(e)}")
                item.text = f"{symbol} - Error"
                
    def search_stock(self):
        symbol = self.root.get_screen('main').ids.search_field.text.strip()
        logger.info(f"Searching for stock: {symbol}")
        if not symbol:
            logger.warning("Empty stock symbol entered")
            self.show_error_dialog("Input Error", "Please enter a stock symbol")
            return

        try:
            logger.debug(f"Sending request to NSE API for {symbol}")
            response = self.session.get(
                f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.current_stock = {
                    "symbol": data["info"]["symbol"],
                    "companyName": data["info"]["companyName"],
                    "lastPrice": data["priceInfo"]["lastPrice"]
                }
                logger.info(f"Found stock: {self.current_stock['symbol']} - {self.current_stock['companyName']}")

                screen = self.root.get_screen('main')
                screen.ids.search_result_symbol.text = f"{self.current_stock['symbol']} - ₹{self.current_stock['lastPrice']}"
                screen.ids.search_result_name.text = self.current_stock["companyName"]
                screen.ids.search_result_box.opacity = 1

            else:
                logger.warning(f"Stock not found or API error: {response.status_code}")
                self.show_error_dialog("API Error", f"Stock not found or API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {str(e)}")
            self.show_error_dialog("Error", f"Failed to fetch stock data: {str(e)}")

    def add_to_watchlist(self):
        if not self.current_stock:
            logger.warning("Attempt to add null stock to watchlist")
            return

        screen = self.root.get_screen('main')
        for item in screen.ids.watchlist.children:
            if item.text.split(" - ")[0] == self.current_stock['symbol']:
                logger.warning(f"Stock {self.current_stock['symbol']} already in watchlist")
                self.show_error_dialog("Duplicate", "This stock is already in your watchlist")
                return

        logger.info(f"Adding {self.current_stock['symbol']} to watchlist")
        list_item = StockListItem(text=f"{self.current_stock['symbol']} - ₹{self.current_stock['lastPrice']}")
        screen.ids.watchlist.add_widget(list_item)
        screen.ids.search_result_box.opacity = 0
        screen.ids.search_field.text = ""

        self.update_config_watchlist()

    def remove_stock(self, instance):
        symbol = instance.text.split(" - ")[0]
        logger.info(f"Removing {symbol} from watchlist")
        self.root.get_screen('main').ids.watchlist.remove_widget(instance)
        self.update_config_watchlist()

    def update_config_watchlist(self):
        """Update the watchlist in config file"""
        logger.info("Updating watchlist in config file")
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r+') as f:
                    config = json.load(f)
                    main_screen = self.root.get_screen('main')
                    watchlist_items = [item.text.split(" - ")[0] for item in main_screen.ids.watchlist.children]
                    config['LIST'] = watchlist_items
                    f.seek(0)
                    json.dump(config, f, indent=4)
                    f.truncate()
                    logger.info(f"Updated watchlist with {len(watchlist_items)} items")
            except Exception as e:
                logger.error(f"Error updating watchlist in config: {str(e)}")
                self.show_error_dialog("Config Error", f"Failed to update watchlist: {str(e)}")
        else:
            logger.warning("Config file not found - cannot update watchlist")

    def show_error_dialog(self, title, message):
        logger.error(f"Showing error dialog: {title} - {message}")
        if not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=message,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        theme_text_color="Custom",
                        text_color=self.color_palette["primary"],
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ]
            )
        self.dialog.text = message
        self.dialog.title = title
        self.dialog.open()

    def navigate_to_credentials(self):
        logger.info("Navigating to credentials screen")
        self.root.current = "credentials_input"


if __name__ == '__main__':
    try:
        logger.info("Starting TwentyFive application")
        if platform in ['win', 'linux', 'macosx']:
            Window.size = (400, 700)
        TwentyFiveApp().run()
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}", exc_info=True)
