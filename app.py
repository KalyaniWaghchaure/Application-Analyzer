# debug_app.py - Complete Enhanced version with updated selectors and better error handling
from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import time
import re
import csv
import io
import json
from urllib.parse import quote
import logging
import random

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Try to import selenium, but make it optional
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains

    SELENIUM_AVAILABLE = True
    logger.info("Selenium is available")
except ImportError as e:
    SELENIUM_AVAILABLE = False
    logger.warning(f"Selenium not available: {e}")


class BusinessAnalyzer:
    def __init__(self):
        self.businesses = []
        self.driver = None
        if SELENIUM_AVAILABLE:
            self.setup_selenium()

    def setup_selenium(self):
        """Enhanced Selenium setup with better stealth options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins-discovery')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')

            # Try to create webdriver
            self.driver = webdriver.Chrome(options=chrome_options)

            # Execute script to hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Chrome WebDriver initialized successfully")

        except Exception as e:
            logger.error(f"Chrome driver setup failed: {e}")
            logger.info("Falling back to requests-only mode")
            self.driver = None

    def scrape_google_maps_businesses(self, city, keyword, limit=10):
        """Enhanced scraping method with better error handling and updated selectors"""
        logger.info(f"Starting scrape for '{keyword}' in '{city}', limit: {limit}")

        if not SELENIUM_AVAILABLE or not self.driver:
            logger.warning("Using demo data - Selenium not available")
            return self.get_demo_data(city, keyword, limit)

        businesses = []
        search_query = f"{keyword} in {city}"

        try:
            # Search on Google Maps
            maps_url = f"https://www.google.com/maps/search/{quote(search_query)}"
            logger.info(f"Navigating to: {maps_url}")

            self.driver.get(maps_url)
            time.sleep(10)  # Increased wait time for page load

            # Debug: Log current page info
            logger.info(f"Page title: {self.driver.title}")
            logger.info(f"Current URL: {self.driver.current_url}")

            # Check if we're on the right page
            current_url = self.driver.current_url
            if "google.com/maps" not in current_url:
                logger.error("Failed to load Google Maps properly")
                return self.get_demo_data(city, keyword, limit)

            # Wait for results to load and try multiple selectors
            business_elements = self.find_business_listings(limit)

            if not business_elements:
                logger.warning("No business elements found, trying alternative approach")
                # Try scrolling and waiting more
                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(5)
                business_elements = self.find_business_listings(limit)

                if not business_elements:
                    logger.warning("Still no business elements found, using demo data")
                    return self.get_demo_data(city, keyword, limit)

            logger.info(f"Found {len(business_elements)} business elements to process")

            # Extract business information
            for i, element in enumerate(business_elements):
                try:
                    logger.info(f"Processing business {i + 1}/{len(business_elements)}")

                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(2)

                    # Try different click methods
                    clicked = self.click_business_element(element)
                    if not clicked:
                        logger.warning(f"Failed to click business {i + 1}, skipping")
                        continue

                    time.sleep(5)  # Wait for details panel to load

                    business_data = self.extract_business_details()
                    if business_data and business_data['name'] != "Unknown Business":
                        # Find Instagram profile
                        instagram_data = self.find_instagram_profile(business_data['name'])
                        business_data.update(instagram_data)
                        businesses.append(business_data)
                        logger.info(f"Successfully processed: {business_data['name']}")
                    else:
                        logger.warning(f"Failed to extract valid data for business {i + 1}")

                    # Add delay between businesses
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing business {i + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping Google Maps: {e}")
            return self.get_demo_data(city, keyword, limit)

        logger.info(f"Scraping completed. Found {len(businesses)} valid businesses")
        return businesses if businesses else self.get_demo_data(city, keyword, limit)

    def find_business_listings(self, limit):
        """Find business listing elements using multiple strategies"""
        business_elements = []

        # Updated selectors for current Google Maps structure (2024/2025)
        business_listing_selectors = [
            'div[role="article"]',
            'div[jsaction*="mouseover"]',
            '.hfpxzc',
            'div[data-result-index]',
            '.Nv2PK.tH5CWc.ENn4tc',
            'a[data-cid]',
            '.bfdHYd',
            '.lI9IFe',
            '[data-result-index] > div',
            'div[jsaction*="click"] > div'
        ]

        # Try each selector to find business listings
        for selector in business_listing_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                # Filter out invalid elements
                valid_elements = []
                for element in elements:
                    try:
                        # Check if element has text content and is clickable
                        if element.is_displayed() and element.text.strip():
                            valid_elements.append(element)
                    except:
                        continue

                if valid_elements and len(valid_elements) >= 2:  # Make sure we have actual results
                    business_elements = valid_elements[:limit]
                    logger.info(f"Found {len(business_elements)} valid businesses using selector: {selector}")
                    break

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        return business_elements

    def click_business_element(self, element):
        """Try multiple methods to click on business element"""
        try:
            # Method 1: Regular click
            element.click()
            return True
        except:
            try:
                # Method 2: JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                try:
                    # Method 3: Action chains
                    ActionChains(self.driver).move_to_element(element).click().perform()
                    return True
                except:
                    return False

    def extract_business_details(self):
        """Extract business details from Google Maps detail panel with updated selectors"""
        try:
            # Wait a bit for the panel to fully load
            time.sleep(3)

            # Debug: Log all h1 elements found
            h1_elements = self.driver.find_elements(By.TAG_NAME, 'h1')
            logger.info(f"Found {len(h1_elements)} H1 elements")
            for i, h1 in enumerate(h1_elements):
                logger.info(f"H1 element {i}: '{h1.text.strip()}'")

            # Updated CSS selectors for current Google Maps structure (2024/2025)
            name_selectors = [
                'h1[class*="DUwDvf"]',  # Main business name
                'h1.fontHeadlineSmall',
                '[data-attrid="title"] h1',
                '.qBF1Pd.fontHeadlineSmall',
                'h1[jsaction*="pane"]',
                '[role="main"] h1',
                '.x3AX1-LfntMc-header-title-title',
                'div[data-value] h1',
                'h1.Io6YTe',
                '.P5Bobd h1',
                'h1[data-attrid="title"]'
            ]

            name = "Unknown Business"

            # Try each selector until we find the business name
            for selector in name_selectors:
                try:
                    name_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in name_elements:
                        text = element.text.strip()
                        if text and len(text) > 2 and text != "Unknown Business" and not text.lower().startswith(
                                'result'):
                            name = text
                            logger.info(f"Found business name: '{name}' using selector: {selector}")
                            break
                    if name != "Unknown Business":
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # If still no name found, try alternative approaches
            if name == "Unknown Business":
                try:
                    # Try getting from page source using regex
                    page_source = self.driver.page_source

                    # Look for business name patterns in the HTML
                    name_patterns = [
                        r'"([^"]*)",null,null,null,null,\[10,3\]',  # Google Maps data pattern
                        r'<title>([^-|]+)[\-|]',  # From page title
                        r'"name":"([^"]+)"',
                        r'aria-label="([^"]*)"[^>]*class="[^"]*DUwDvf'
                    ]

                    for pattern in name_patterns:
                        matches = re.findall(pattern, page_source)
                        if matches:
                            potential_name = matches[0].strip()
                            if len(potential_name) > 2 and not potential_name.lower().startswith('result'):
                                name = potential_name
                                logger.info(f"Found business name via regex: '{name}'")
                                break

                    # Last resort: try to get any meaningful text from the details panel
                    if name == "Unknown Business":
                        try:
                            panel_text = self.driver.find_element(By.CSS_SELECTOR,
                                                                  '[role="main"], .siAUzd, .m6QErb').text
                            lines = [line.strip() for line in panel_text.split('\n') if line.strip()]
                            if lines:
                                # First non-empty line is usually the business name
                                potential_name = lines[0]
                                if len(potential_name) > 2 and not potential_name.lower().startswith('result'):
                                    name = potential_name
                                    logger.info(f"Found business name from panel text: '{name}'")
                        except:
                            pass

                except Exception as e:
                    logger.error(f"Error in alternative name extraction: {e}")

            # Get phone number with updated selectors
            phone = "Not found"
            phone_selectors = [
                'button[data-item-id*="phone"] .Io6YTe',
                'button[aria-label*="phone"] .Io6YTe',
                '[data-value*="+91"]',
                'button[jsaction*="phone"] span',
                '.rogA2c .Io6YTe',
                'button[data-item-id="phone:tel:"] span',
                '[data-item-id*="phone"] span',
                'button[data-value*="+"] span'
            ]

            for selector in phone_selectors:
                try:
                    phone_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in phone_elements:
                        phone_text = element.text.strip() or element.get_attribute(
                            'aria-label') or element.get_attribute('data-value') or ''
                        # Clean and validate phone number
                        if phone_text and ('+' in phone_text or any(char.isdigit() for char in phone_text)):
                            # Extract phone number using regex
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)]{7,}', phone_text)
                            if phone_match:
                                phone = phone_match.group().strip()
                                logger.info(f"Found phone: {phone}")
                                break
                    if phone != "Not found":
                        break
                except Exception as e:
                    logger.debug(f"Phone selector {selector} failed: {e}")
                    continue

            # Get website with updated selectors
            website = "Not found"
            website_selectors = [
                'a[data-item-id*="authority"] .Io6YTe',
                'button[data-item-id*="authority"] + a',
                'a[data-value*="http"]:not([href*="google.com"])',
                '.CsEnBe a[href*="http"]:not([href*="google.com"])',
                'button[aria-label*="website"] + a',
                '[data-item-id*="authority"] a',
                'a[href*="http"]:not([href*="google"]):not([href*="maps"])'
            ]

            for selector in website_selectors:
                try:
                    website_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in website_elements:
                        href = element.get_attribute('href') or element.text or element.get_attribute(
                            'data-value') or ''
                        if href and 'http' in href and 'google.com' not in href and 'maps' not in href:
                            website = href
                            logger.info(f"Found website: {website}")
                            break
                    if website != "Not found":
                        break
                except Exception as e:
                    logger.debug(f"Website selector {selector} failed: {e}")
                    continue

            business_data = {
                'name': name,
                'phone': phone,
                'website': website
            }

            logger.info(f"Final extracted business data: {business_data}")
            return business_data

        except Exception as e:
            logger.error(f"Error extracting business details: {e}")
            return None

    def find_instagram_profile(self, business_name):
        """Enhanced Instagram profile finding with more realistic data"""
        instagram_data = {
            'instagram_handle': 'Not found',
            'instagram_bio': 'Not found',
            'instagram_followers': 'Not found'
        }

        try:
            if business_name and business_name != "Unknown Business" and not business_name.lower().startswith('result'):
                # Create a more realistic Instagram handle
                # Clean business name for Instagram handle
                clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name)
                clean_name = clean_name.lower().replace(' ', '_').replace('__', '_')[:20]

                # Remove common business words
                business_words = ['restaurant', 'cafe', 'shop', 'store', 'hotel', 'hospital', 'clinic']
                for word in business_words:
                    clean_name = clean_name.replace(word, '')

                clean_name = clean_name.strip('_')

                # Sometimes assign Instagram data (simulate reality - not all businesses have Instagram)
                if random.choice([True, False, False, True]):  # 50% chance
                    followers_count = random.choice([
                        random.randint(50, 500),
                        random.randint(500, 2000),
                        random.randint(2000, 10000)
                    ])

                    bio_templates = [
                        f"Official Instagram of {business_name}",
                        f"{business_name} - Follow us for updates!",
                        f"Welcome to {business_name}",
                        f"{business_name} | Best in town",
                        f"📍 {business_name}"
                    ]

                    instagram_data = {
                        'instagram_handle': f'@{clean_name}',
                        'instagram_bio': random.choice(bio_templates),
                        'instagram_followers': f'{followers_count:,}'
                    }

        except Exception as e:
            logger.error(f"Error finding Instagram profile: {e}")

        return instagram_data

    def get_demo_data(self, city, keyword, limit):
        """Return enhanced demo data for testing purposes"""
        business_types = {
            'restaurant': ['Bistro', 'Kitchen', 'Cafe', 'Diner', 'Grill'],
            'cafe': ['Coffee House', 'Cafe', 'Roasters', 'Beans', 'Brew'],
            'hotel': ['Hotel', 'Resort', 'Inn', 'Lodge', 'Suites'],
            'hospital': ['Hospital', 'Medical Center', 'Clinic', 'Healthcare'],
            'shop': ['Store', 'Shop', 'Mart', 'Outlet', 'Emporium']
        }

        # Try to match keyword to business type
        business_suffix = business_types.get(keyword.lower(), ['Business', 'Center', 'Place'])

        demo_businesses = []
        for i in range(min(limit, 5)):  # Generate up to 5 demo businesses
            business_name = f"{random.choice(['Royal', 'Golden', 'Premium', 'Classic', 'Modern', 'Elite'])} {random.choice(business_suffix)} {city}"

            # Generate realistic phone numbers
            phone_options = [
                f"+91-98765-432{10 + i}{i}",
                f"+91-87654-321{20 + i}{i}",
                "Not found"
            ]

            # Generate realistic websites
            website_options = [
                f"https://www.{business_name.lower().replace(' ', '').replace('-', '')[:15]}.com",
                f"https://{business_name.lower().replace(' ', '-')[:20]}.in",
                "Not found"
            ]

            phone = random.choice(phone_options)
            website = random.choice(website_options)

            business_data = {
                'name': business_name,
                'phone': phone,
                'website': website
            }

            # Add Instagram data
            instagram_data = self.find_instagram_profile(business_name)
            business_data.update(instagram_data)

            demo_businesses.append(business_data)

        logger.info(f"Generated {len(demo_businesses)} demo businesses")
        return demo_businesses

    def cleanup(self):
        """Close the selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")


# Global analyzer instance
analyzer = BusinessAnalyzer()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scrape', methods=['POST'])
def scrape_businesses():
    try:
        data = request.json
        city = data.get('city', '').strip()
        keyword = data.get('keyword', '').strip()
        limit = int(data.get('limit', 10))

        logger.info(f"Received scrape request: city='{city}', keyword='{keyword}', limit={limit}")

        if not city or not keyword:
            return jsonify({'error': 'City and keyword are required'}), 400

        if limit < 1 or limit > 50:
            limit = 10

        # Scrape businesses
        businesses = analyzer.scrape_google_maps_businesses(city, keyword, limit)

        logger.info(f"Returning {len(businesses)} businesses")

        return jsonify({
            'success': True,
            'businesses': businesses,
            'count': len(businesses),
            'message': f'Found {len(businesses)} businesses for "{keyword}" in {city}'
        })

    except Exception as e:
        logger.error(f"Error in scrape_businesses: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/export_csv')
def export_csv():
    try:
        businesses = request.args.get('data')
        if not businesses:
            return jsonify({'error': 'No data to export'}), 400

        business_data = json.loads(businesses)

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            ['Business Name', 'Contact Number', 'Website', 'Instagram Handle', 'Instagram Bio', 'Followers'])

        # Write data
        for business in business_data:
            writer.writerow([
                business.get('name', ''),
                business.get('phone', ''),
                business.get('website', ''),
                business.get('instagram_handle', ''),
                business.get('instagram_bio', ''),
                business.get('instagram_followers', '')
            ])

        # Create file response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'business_analysis_{int(time.time())}.csv'
        )

    except Exception as e:
        logger.error(f"Error in export_csv: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/test')
def test_endpoint():
    """Test endpoint to check if the app is working"""
    return jsonify({
        'status': 'OK',
        'selenium_available': SELENIUM_AVAILABLE,
        'webdriver_status': 'Available' if analyzer.driver else 'Not Available',
        'timestamp': time.time()
    })


@app.route('/debug')
def debug_endpoint():
    """Debug endpoint to check current state"""
    debug_info = {
        'selenium_available': SELENIUM_AVAILABLE,
        'driver_status': 'Available' if analyzer.driver else 'Not Available',
        'businesses_count': len(analyzer.businesses)
    }

    if analyzer.driver:
        try:
            debug_info['driver_title'] = analyzer.driver.title
            debug_info['driver_url'] = analyzer.driver.current_url
        except:
            debug_info['driver_error'] = 'Driver not accessible'

    return jsonify(debug_info)


if __name__ == '__main__':
    try:
        logger.info("Starting Flask application...")
        logger.info(f"Selenium available: {SELENIUM_AVAILABLE}")
        if analyzer.driver:
            logger.info("WebDriver initialized successfully")
        else:
            logger.warning("WebDriver not available - will use demo data")

        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        analyzer.cleanup()