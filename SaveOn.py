import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import pickle
import os
import logging


def init_driver(headless=True):
    # options = Options()
    # if headless:
    #     # make the browser headless
    #     options.add_argument("--headless")
    #
    # driver = webdriver.Firefox(options=options)

    # TODO: Check which OS is running. If Mac then geckodriver is in path and don't need to specify
    # driver = webdriver.Firefox(executable_path=r'/usr/local/bin/gecko_driver/geckodriver')
    driver = webdriver.Firefox()
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


def scrape(driver, product_list):
    time.sleep(8)  # wait before checking if elements exist on the page

    # Option 1: "View All" button appears on page - indicates a category main page
    if check_exists_by_xpath(driver, "//button[contains(.,'View All')]"):
        # View All button exists on page
        categories_url = driver.current_url
        categories_size = len(driver.find_elements_by_xpath("//button[contains(.,'View All')]"))
        for i in range(categories_size):
            # load the categories page
            driver.get(categories_url)
            time.sleep(6) # wait for it to load before checking if elements exist
            categories = driver.find_elements_by_xpath("//button[contains(.,'View All')]")
            categories[i].click()
            scrape(driver, product_list)

    # Option 2: "Next" button appears on page - indicates a page with listings
    else:
    # Scrape the contents of the page
        try:
            products = driver.find_elements_by_class_name("product__itemContent")
            number_of_products = len(products)
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
                logging.debug(f"Name: {product_name} Size: {product_size} Price: {product_price}")
                # look up and see if name + size returns a known SKU
                # if it doesn't click on the listing and get the SKU
                SKU_lookup = str(product_name) + "::" + str(product_size)
                # check and see if we know the SKU based on Title+Size - if not we need to gather that info
                if SKU_lookup not in product_list:
                    logging.debug(f"{product_name} {product_size} was not found")
                    main_url = driver.current_url  # save the page url to reverse traversal
                    try:
                        # TODO: open item in new tab to save the reload time when you navigate to the previous page
                        # ActionChains(driver).key_down(Keys.COMMAND).key_down(Keys.SHIFT).perform()
                        # products[i].find_element_by_tag_name("h3").send_keys(Keys.COMMAND)
                        products[i].find_element_by_tag_name("h3").click()
                        # ActionChains(driver).key_up(Keys.COMMAND).key_up(Keys.SHIFT).perform()
                        time.sleep(4)

                        # retrieve SKU and description here
                        product_secondary_information = driver.find_element_by_class_name("secondaryInformation__section").get_attribute("innerText")
                        logging.debug(f"Product's Secondary Information: {product_secondary_information}")
                        product_secondary_information = product_secondary_information.split('\n')
                        for line in product_secondary_information:
                            if "SKU" in line:
                                product_SKU = line.replace("SKU ", "")
                                product_list[SKU_lookup] = product_SKU
                                logging.debug(f"SKU: {product_SKU}")
                                print(f"SKU_lookup: {SKU_lookup} SKU: {product_SKU}")
                    except ElementNotInteractableException:
                        logging.error(f"Element Not Interactable Exception occurred at: {driver.current_url} Element: {i}")
                    except NoSuchElementException:
                        logging.error(f"No Such Element Exception occurred at: {driver.current_url} Element: {i}")
                    except ElementClickInterceptedException:
                        logging.error(f"Element Click Intercepted Exception occurred at: {driver.current_url} Element: {i}")
                    finally:
                        # save to file
                        pkl_file = open('SKU.pkl', 'wb')
                        pickle.dump(product_list, pkl_file)
                        pkl_file.close()
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
            scrape(driver, product_list)
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


if __name__ == "__main__":
    logging.basicConfig(filename="test.log", level=logging.WARNING)  # change to level to DEBUG or ERROR

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

    logging.debug("Process Finished")

# TODO: better error handling that continues scraping and displays the error and the page it occurred on
# TODO: add ability to pass through via CL argument a file containing URLs to scrape
# TODO: save error URLs to separate file so you can pass it in later
# TODO: add a progress bar? Based on how many items scraped/time elapsed?
