# SaveMore

This is a Selenium-based web scraper designed to scrape the online store of Save-On-Foods. Ever wonder what a good price is for a product you don't frequently purchase? That's the driving force behind this project.

Uses Depth First Traversal to get all items listed. If an item isn't previously known it scrapes that individual page as well which can add many hours to total traversal time. When SKUs are known the total scraping process can take 3-4 hours, due to very generous/friendly hard-coded wait times.

**First time initialization** (requires Homebrew, available on MacOS and Linux):
```bash
git clone https://github.com/jscottgray/SaveMore.git
cd SaveMore
brew install geckodriver
pip install -r requirements.txt
```

**Running the scraper** (Weekly frequency recommended - prices aren't updated more frequently than that):
```bash
rm completed_categories.txt
python3 SaveOn.py
```
The scraper records progress of it's scraping progress so that if you stop the program mid-scrape it will not unnecessarily scrape already scrapped departments. This progress is saved in the completed_categories file.

## Graph showing the Store's Tree Structure
![Graph](./Graph.svg)

The scraper only receives a list of Departments. It then determines whether it is on a product page or not. It does not know categories or sub-categories. 

If there are subcategories on the page it traverses them depth first.

If there are no subcategories on the page then it retrieves the product pricing.

If we encounter a new product we have to traverse to it's individual page to retrieve all the product's information. This traversal into each product's page would be costly if we had to do it on every product (since there is well over 10k products to scrape). Unfortunately the first time running the scraper this operation is required which results in a one-time slowdown of 20x. 
