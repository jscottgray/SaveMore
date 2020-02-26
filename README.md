# SaveMore
This is a selenium-based web scraper designed to scrape the online store of Save-On-Foods. Ever wonder what a good price is for a product you don't frequently purchase? That's the driving force behind this project.

Uses Depth First Traversal to get all items listed. If an item isn't previously known (project stores a pkl file of product name dictionary) it scrapes that individual page as well which can add many hours to total traversal time. When SKUs are known the total scraping process can take 3-4 hours, due to very generous/friendly hard-coded wait times.

Currently under development.
