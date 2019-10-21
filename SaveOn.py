from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.firefox.options import Options
import time
import datetime
import sys
import os
import logging
import pickle


today = datetime.date.today()
output_filename = today.strftime("SaveOnFoods%b%d.txt")
# line count for number of items scraped last week
last_week_total = sum(1 for line in open("output.txt"))
tally_total = 0
if os.path.isfile(output_filename):
    tally_total = sum(1 for line in open(output_filename, "r+"))


def init_driver(headless=True):
    options = Options()
    if headless:
        # make the browser headless
        options.add_argument("--headless")
    # todo: throw this into a try except block to make sure geckodriver is installed
    # driver = webdriver.Firefox(executable_path=r'/usr/local/bin/gecko_driver/geckodriver')
    try:
        driver = webdriver.Firefox(options=options)
    except all as e:
        print(e.msg)

    # TODO: Check which OS is running. If Mac then geckodriver is in path and don't need to specify
    driver.wait = WebDriverWait(driver, 5)
    return driver


def check_exists_by_xpath(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True


def lookup():
    # load the department url text file
    F = open("departments.txt", "r")
    department_urls = []
    for line in F:
        department_urls.append(line.rstrip().split(" : "))
    F.close()

    if os.path.isfile('SKU.pkl'):
        pkl_file = open('SKU.pkl', 'rb')
        name_to_SKU = pickle.load(pkl_file)
        pkl_file.close()
    else:
        logging.warning("Name to SKU File not found. Should be named SKU.pkl")
        name_to_SKU = dict()

    # scrape each department
    for department in department_urls:
        driver = init_driver()
        print(f"Scraping department: {department[0]}")
        logging.debug(f"Scraping department: {department[0]}")
        driver.get(department[1])
        scrape(driver, name_to_SKU)
        driver.close()

    # save the updated name to SKU dictionary to file
    pkl_file = open('SKU.pkl', 'wb')
    pickle.dump(name_to_SKU, pkl_file)
    pkl_file.close()


def scrape(driver, product_list, completed_categories):
    time.sleep(8)  # wait before checking if elements exist on the page
    # Given a page - is it a page with categories or a page with products?
    # A category page will have at least one button that says "View All"
    # If it doesn't say "View All" then we can assume it's a page with product listings

    # Option 1: "View All" button appears on page - indicates a category main page
    if check_exists_by_xpath(driver, "//button[contains(.,'View All')]"):
        # View All button exists on page
        categories_url = driver.current_url
        categories_size = len(driver.find_elements_by_xpath("//button[contains(.,'View All')]"))
        # .subCategoryProductsList > li:nth-child(1) > div:nth-child(1) > h3:nth-child(1)
        category_name_list = []
        category_names = driver.find_elements_by_class_name("subCategoryProducts__title")
        for i in range(len(category_names)):
            category_name_list.append(category_names[i].get_attribute("innerText"))
        for i in range(categories_size):
            # go through each category on the page
            categories = driver.find_elements_by_xpath("//button[contains(.,'View All')]")
            current_category = category_name_list[i]
            if current_category not in completed_categories:

                try:
                    categories[i].click()
                except ElementClickInterceptedException as e:
                    logging.error(e.msg)
                    print(e.msg)
                    time.sleep(10)
                    categories = driver.find_elements_by_xpath("//button[contains(.,'View All')]")
                    categories[i].click()
                scrape(driver, product_list, completed_categories)
                driver.get(categories_url)
                with open("completed_categories.txt", "a") as f:
                    f.write(current_category + "\n")
                time.sleep(6)

    # Option 2: "Next" button appears on page - indicates a page with listings
    else:
        revert_url = driver.current_url
        try:
            products = driver.find_elements_by_class_name("product__itemContent")
            number_of_products = len(products)
            if number_of_products != 0:
                for i in range(number_of_products):
                    try:
                        product = products[i]
                    except IndexError:
                        logging.error(f"Index Error occurred on element {i} at: {driver.currenturl}")
                        print(f"Index Error occurred on element {i} at: {driver.currenturl}")
                        time.sleep(10)
                        products = driver.find_elements_by_class_name("product__itemContent")
                        product = products[i]
                    product_name = product.find_element_by_tag_name("h3").get_attribute("innerText")
                    product_size = product.find_element_by_class_name("productInfo__size").get_attribute("innerText")
                    product_price = product.find_element_by_class_name("priceInfo").get_attribute("innerText")
                    product_multibuy = False
                    # could split price up, check the size
                    price_list = product_price.split()
                    if "for" in product_price:
                        # multi-buy, e.g. "2 for $4.00"
                        # price_list = product_price.split()
                        total_price = price_list[2].strip("$")
                        quantity = price_list[0]
                        product_price = str(round(float(total_price) / int(quantity), 2))
                        product_multibuy = True
                    elif "Buy" in product_price and "Get" in product_price:  # and "points" not in product_price:
                        if "points" not in product_price:
                            # buy 2 get 1 free
                            price = price_list[0]
                            price = price[1:]
                            price = float(price)
                            product_price = int(price_list[2]) * price / (int(price_list[2]) + int(price_list[4]))
                        else:
                            # getting free points
                            product_multibuy = price_list[0]
                    elif "On Sale!" in product_price:
                        product_price = price_list[0]
                    elif "avg/ea" in product_price:
                        avg_price = product_price.split()[0].strip("$")
                        # confirm the weight is an average
                        if "avg" in product_size:
                            if (product_size.split()[1] == "g"):
                                multiplier = 1000 / int(product_size.split()[0])
                            else:
                                # kg
                                logging.warning(f"not g: {product_size}")
                                multiplier = 1 / float(product_size.split()[0])
                            product_price = float(product_price.split()[0].strip("$")) * multiplier
                            product_price = str(round(product_price, 2))
                            product_size = "/kg"
                        # need to multiply product_size by avg_price to get price/kg

                    if isinstance(product_price, str):
                        product_price = product_price.strip("$")

                    logging.debug(f"Name: {product_name} Size: {product_size} Price: {product_price}")
                    # look up and see if name + size returns a known SKU
                    # if it doesn't click on the listing and get the SKU
                    SKU_lookup = str(product_name) + "::" + str(product_size)
                    global tally_total
                    global last_week_total
                    tally_total += 1
                    print_progress(tally_total, last_week_total)

                    # check and see if we know the SKU based on Title+Size - if not we need to gather that info
                    if SKU_lookup in product_list:
                        product_SKU = product_list[SKU_lookup]
                        logging.debug(f"{product_SKU} {product_price} {product_multibuy}")
                        with open(output_filename, "a") as out:
                            out.write(f"{product_SKU} {product_price} {product_multibuy}\n")
                    if SKU_lookup not in product_list:
                        logging.debug(f"{product_name} {product_size} was not found")
                        main_url = driver.current_url  # save the page url to reverse traversal
                        try:
                            products[i].find_element_by_tag_name("h3").click()
                            time.sleep(4)
                            # retrieve SKU and description here
                            product_secondary_information = driver.find_element_by_class_name("secondaryInformation__section").get_attribute("innerText")
                            logging.debug(f"Product's Secondary Information: {product_secondary_information}")
                            product_secondary_information = product_secondary_information.split('\n')
                            for line in product_secondary_information:
                                if "SKU" in line:
                                    product_SKU = line.replace("SKU ", "")
                                    product_list[SKU_lookup] = product_SKU
                                    logging.debug(f"{product_SKU} {product_price} {product_multibuy}")
                                    with open(output_filename, "a") as out:
                                        out.write(f"{product_SKU} {product_price} {product_multibuy}\n")
                        except ElementNotInteractableException:
                            logging.error(f"Element Not Interactable Exception occurred at: {driver.current_url} Element: {i}")
                        except NoSuchElementException:
                            logging.error(f"No Such Element Exception occurred at: {driver.current_url} Element: {i}")
                        except ElementClickInterceptedException:
                            logging.error(f"Element Click Intercepted Exception occurred at: {driver.current_url} Element: {i}")
                        finally:
                            # save to file
                            with open('SKU.pkl', 'wb') as pkl_file:
                                pickle.dump(product_list, pkl_file)
                            # return back to listings
                            driver.get(main_url)
                            time.sleep(6)
                            products = driver.find_elements_by_class_name("product__itemContent")
        except NoSuchElementException:
            logging.error(f"No Such Element Exception occurred at: {driver.current_url}")
        # hit the next button
        try:
            button = driver.find_element_by_xpath('/html/body/div[1]/div/div[1]/div[1]/div/div[2]/div[1]/nav/button[2]')
            button.click()
            scrape(driver, product_list, completed_categories)
            return
        except ElementNotInteractableException:
            # Exception raised when done scraping a category.
            # The element exists but obviously doesn't appear on the last page
            # logging level is debug not error as this is an expected issue at the end of each category
            logging.debug(f"Element Not Interactable Exception occurred at: {driver.current_url}")
            return
        except NoSuchElementException:
            # for categories which do not have more than 1 page - hence no navigation
            return
        except ElementClickInterceptedException:
            driver.close()
            driver = init_driver()
            driver.get(revert_url)
            logging.warning("Element Click Intercepted Exception occurred")
            time.sleep(6)


def print_progress(progress, total):
    width = 50
    blockwidth = int(total / width)
    num_blocks = int(progress / blockwidth)
    string = "["
    string += str("█" * num_blocks)
    remainder = int((progress % blockwidth) / blockwidth * 8)
    if remainder == 0:
        string += " "
    elif remainder == 1:
        string += "▏"
    elif remainder == 2:
        string += "▎"
    elif remainder == 3:
        string += "▍"
    elif remainder == 4:
        string += "▌"
    elif remainder == 5:
        string += "▋"
    elif remainder == 6:
        string += "▊"
    elif remainder == 7:
        string += "▉"
    elif remainder == 8:
        string += "█"
    string += " " * (width - num_blocks - 1)
    string += "]"
    print(f"{string} {int(progress / total) * 100}% {progress}/{total}", end="\r")


if __name__ == "__main__":
    print(f"tally total: {tally_total} last week total: {last_week_total}")

    # change to level to DEBUG / ERROR / WARNING
    logging.basicConfig(filename="test.log", level=logging.WARNING)

    SKU_filename = 'SKU.pkl'
    URL_filename = 'departments.txt'
    # update this so it includes the date
    completed_categories_filename = "completed_categories.txt"

    # print(sys.argv)
    if "-h" in sys.argv or "--headless" in sys.argv:
        headless = True
    else:
        headless = False

    # load the ProductName -> SKU conversion list
    if os.path.isfile(SKU_filename):
        pkl_file = open(SKU_filename, 'rb')
        name_to_SKU = pickle.load(pkl_file)
        pkl_file.close()
    else:
        logging.warning(f"Name to SKU File not found. Should be named {SKU_filename}")
        name_to_SKU = dict()

    # load the department url text file
    department_URLs = []
    with open(URL_filename, "r") as departments_file:
        for line in departments_file:
            department_URLs.append(line.rstrip().split(" : "))

    completed_categories = []
    if os.path.isfile(completed_categories_filename):
        with open(completed_categories_filename, "r") as f:
            for line in f:
                completed_categories.append(line.strip())

    # scrape each department
    for department in department_URLs:
        if department[0] not in completed_categories:
            driver = init_driver(headless)
            print(f"Scraping department: {department[0]}")
            logging.debug(f"Scraping department: {department[0]}")
            print_progress(tally_total, last_week_total)
            # Scrape the Department
            driver.get(department[1])
            scrape(driver, name_to_SKU, completed_categories)
            # Record that we have successfully scraped the department
            with open("completed_categories.txt", "a") as f:
                f.write(department[0] + "\n")
            logging.debug(f"Done scraping department: {department[0]}")
            driver.close()

# TODO: better error handling that continues scraping and displays the error and the page it occurred on
# TODO: add ability to pass through via CL argument a file containing URLs to scrape
# TODO: save error URLs to separate file so you can pass it in later
# TODO: add a progress bar? Based on how many items scraped/time elapsed?

# TODO: decode the product_price
