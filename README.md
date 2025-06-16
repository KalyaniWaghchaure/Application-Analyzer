Task Overview 
Build a web-based admin tool that takes a city name and scrapes Google My 
Business listings, finds the Instagram profiles (if any), and displays the 
results in a filterable table. 
Functionality to Implement 
1. Input Panel for Admin: - City name input (e.g., Pune) - Business keyword (e.g., Cafe, Digital Agency) 
2. Data Scraping Module: - Scrape Google Maps listings (top 10–50 businesses): 
  • Business Name 
  • Contact Number 
  • Website - For each business: 
  • Search Google or use regex to find Instagram account 
  • Scrape Instagram page to get username, bio, followers 
3. Admin Table Display (Web UI): - Show: 
  • Business Name 
  • Contact Number 
  • Website 
  • Instagram Handle (or "Not found") 
4. Filter Feature: - Show businesses without websites - Show businesses without Instagram - Search business by name or phone number 
	
Tech Stack 
• Scraping: Selenium + BeautifulSoup 
• Backend: Flask or FastAPI 
• Frontend: Flask Templates (Jinja) or Streamlit 
• Instagram Scraping: Search via Google + Scrape with requests or 

 
Filters: 
☑ No Website 
☑ No Instagram 
�
� Search bar 
 
 
