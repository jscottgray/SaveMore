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
import database


# TODO: create query to find out how many products scraped last week
tally_total = 0
last_week_total = 11931

# TODO: need to remove all references to saving the results in a txt file


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


def scrape(driver, completed_categories, department, current_category=""):
    time.sleep(8)  # wait before checking if elements exist on the page
    # Given a page - is it a page with categories or a page with products?
    # A category page will have at least one button that says "View All"
    # If it doesn't say "View All" then we can assume it's a page with product listings

    # Option 1: "View All" button appears on page - indicates a category main page
    if check_exists_by_xpath(driver, "//button[contains(.,'View All')]"):
        # View All button exists on page
        categories_url = driver.current_url
        categories_size = len(driver.find_elements_by_xpath(
            "//button[contains(.,'View All')]"))
        # .subCategoryProductsList > li:nth-child(1) > div:nth-child(1) > h3:nth-child(1)
        category_name_list = []
        category_names = driver.find_elements_by_class_name(
            "subCategoryProducts__title")
        for i in range(len(category_names)):
            category_name_list.append(
                category_names[i].get_attribute("innerText"))
        for i in range(categories_size):
            # go through each category on the page
            categories = driver.find_elements_by_xpath(
                "//button[contains(.,'View All')]")
            current_category = category_name_list[i]
            if current_category not in completed_categories:

                try:
                    categories[i].click()
                except ElementClickInterceptedException as e:
                    logging.error(e.msg)
                    print(e.msg)
                    time.sleep(10)
                    categories = driver.find_elements_by_xpath(
                        "//button[contains(.,'View All')]")
                    categories[i].click()
                scrape(driver,
                       completed_categories, department, current_category)
                driver.get(categories_url)
                with open("completed_categories.txt", "a") as f:
                    f.write(current_category + "\n")
                    # f.write(f"Current URL:{driver.current_url}")
                time.sleep(6)

    # Option 2: "Next" button appears on page - indicates a page with listings
    else:

        # with open(url_filename, "a") as f:
        #     f.write(driver.current_url + "\n")
        revert_url = driver.current_url
        try:
            products = driver.find_elements_by_class_name(
                "product__itemContent")
            number_of_products = len(products)
            if number_of_products != 0:
                for i in range(number_of_products):
                    try:
                        product = products[i]
                    except IndexError:
                        logging.error(
                            f"Index Error occurred on element {i} at: {driver.current_url}")
                        print(
                            f"Index Error occurred on element {i} at: {driver.current_url}")
                        time.sleep(10)
                        products = driver.find_elements_by_class_name(
                            "product__itemContent")
                        product = products[i]
                    product_name = product.find_element_by_tag_name(
                        "h3").get_attribute("innerText")
                    product_size = product.find_element_by_class_name(
                        "productInfo__size").get_attribute("innerText")
                    product_price = product.find_element_by_class_name(
                        "priceInfo").get_attribute("innerText")
                    product_multibuy = False
                    # could split price up, check the size
                    price_list = product_price.split()
                    if "for" in product_price:
                        # multi-buy, e.g. "2 for $4.00"
                        # price_list = product_price.split()
                        total_price = price_list[2].strip("$")
                        quantity = price_list[0]
                        product_price = str(
                            round(float(total_price) / int(quantity), 2))
                        product_multibuy = True
                    # and "points" not in product_price:
                    elif "Buy" in product_price and "Get" in product_price:
                        if "points" not in product_price:
                            # buy 2 get 1 free
                            price = price_list[0]
                            price = price[1:]
                            price = float(price)
                            product_price = int(
                                price_list[2]) * price / (int(price_list[2]) + int(price_list[4]))
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
                                multiplier = 1000 / \
                                    int(product_size.split()[0])
                            else:
                                # kg
                                logging.warning(f"not g: {product_size}")
                                multiplier = 1 / float(product_size.split()[0])
                            product_price = float(product_price.split()[
                                                  0].strip("$")) * multiplier
                            product_price = str(round(product_price, 2))
                            product_size = "/kg"
                        # need to multiply product_size by avg_price to get price/kg

                    if isinstance(product_price, str):
                        product_price = product_price.strip("$")

                    logging.debug(
                        f"Name: {product_name} Size: {product_size} Price: {product_price}")
                    # look up and see if name + size returns a known SKU
                    # if it doesn't click on the listing and get the SKU
                    SKU_lookup = str(product_name) + "::" + str(product_size)
                    global tally_total
                    global last_week_total
                    tally_total += 1
                    print_progress(tally_total, last_week_total)

                    # check and see if we know the SKU based on Title+Size - if not we need to gather that info
                    sku = database.get_SKU(product_name, product_size)

                    if sku:
                        print(f"SKU Found {sku}")
                        # product_SKU = product_list[SKU_lookup]
                        logging.debug(
                            f"{sku} {product_price} {product_multibuy}")
                        # save the item
                        # database.save_price(
                        #     sku, product_price, product_multibuy)
                    else:
                        logging.debug(
                            f"{product_name} {product_size} was not found")
                        main_url = driver.current_url  # save the page url to reverse traversal
                        try:
                            products[i].find_element_by_tag_name("h3").click()
                            time.sleep(4)
                            # retrieve SKU and description here
                            product_secondary_information = driver.find_element_by_class_name(
                                "secondaryInformation__section").get_attribute("innerText")
                            product_secondary_information = product_secondary_information.split(
                                '\n')

                            description = ""
                            for line in product_secondary_information:
                                if "SKU" in line:
                                    product_SKU = line.replace("SKU ", "")
                                elif "Description" in line:
                                    description = line.replace(
                                        "Description", "")

                            database.new_product(
                                product_SKU, product_name, description, department, current_category, product_size)
                            # save price
                            database.save_price(
                                product_SKU, product_price, product_multibuy)
                        except ElementNotInteractableException:
                            logging.error(
                                f"Element Not Interactable Exception occurred at: {driver.current_url} Element: {i}")
                        except NoSuchElementException:
                            logging.error(
                                f"No Such Element Exception occurred at: {driver.current_url} Element: {i}")
                        except ElementClickInterceptedException:
                            logging.error(
                                f"Element Click Intercepted Exception occurred at: {driver.current_url} Element: {i}")
                        finally:
                            # # save to file
                            # with open('SKU.pkl', 'wb') as pkl_file:
                            #     pickle.dump(product_list, pkl_file)
                            # return back to listings
                            driver.get(main_url)
                            time.sleep(6)
                            products = driver.find_elements_by_class_name(
                                "product__itemContent")
        except NoSuchElementException:
            logging.error(
                f"No Such Element Exception occurred at: {driver.current_url}")
        # hit the next button
        try:
            button = driver.find_element_by_xpath(
                '/html/body/div[1]/div/div[1]/div[1]/div/div[2]/div[1]/nav/button[2]')
            button.click()
            scrape(driver, completed_categories,
                   department, current_category)
            return
        except ElementNotInteractableException:
            # Exception raised when done scraping a category.
            # The element exists but obviously doesn't appear on the last page
            # logging level is debug not error as this is an expected issue at the end of each category
            logging.debug(
                f"Element Not Interactable Exception occurred at: {driver.current_url}")
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
    print(f"{string} {int(progress * 100 / total)}% {progress}/{total}", end="\r")


if __name__ == "__main__":
    print(f"tally total: {tally_total} last week total: {last_week_total}")

    # retrieve todays date and the current week (starting on Thursdays)
    todays_date = datetime.date.today()
    todays_week = (todays_date + datetime.timedelta(days=4)).isocalendar()[1]
    todays_year = (todays_date + datetime.timedelta(days=4)).year

    # change to level to DEBUG / ERROR / WARNING
    logging.basicConfig(filename="test.log", level=logging.WARNING)

    # print(sys.argv)
    if "-h" in sys.argv or "--headless" in sys.argv:
        headless = True
    else:
        headless = False

    # connect to DB
    database.connect()

    # load the department url text file
    departments = database.get_departments()

    completed_categories = []

    # scrape each department
    for department in departments:
        if department[0] not in completed_categories:
            driver = init_driver(headless)
            print(f"Scraping department: {department[0]}")
            logging.debug(f"Scraping department: {department[0]}")
            print_progress(tally_total, last_week_total)
            # Scrape the Department
            link = f"https://shop.saveonfoods.com/store/AF1F1129#/category/{department[1]}/{department[2]}"
            driver.get(link)
            scrape(driver, completed_categories, department[0])
            # Record that we have successfully scraped the department
            with open("completed_categories.txt", "a") as f:
                f.write(department[0] + "\n")
            logging.debug(f"Done scraping department: {department[0]}")
            driver.close()
    database.close_db()
    print("Finished Scraping")
