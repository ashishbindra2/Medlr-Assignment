import json

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.db import add_urls_to_medicine
from app.utils.logger import logger

# class_path = "style__inner-container___3BZU9 style__product-grid___3noQW style__padding-top-bottom-12px___1-DPF"
headers = {
    "user_agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"}


async def get_medicine_detail_scrap(url: str):
    response = requests.get(url)
    logger.info("Starting the scraping process for URL: %s", url)

    if response.status_code == 200:
        logger.info("Received response with status code: %d", response.status_code)

        html_content = response.text
        logger.info("HTML content fetched successfully")

        soup = BeautifulSoup(html_content, 'lxml')  # html.parser
        try:
            heading = soup.find('h1').get_text(strip=True)

            json_str = html_content.split('window.__INITIAL_STATE__ = ')
            data = json.loads(json_str[1].split(';\n')[0])

            price_list = data['drugPageReducer']['dynamicData']['priceBox']['priceList'][0]

            mrp_price = None
            discount_price = None
            if price_list:
                mrp_price = price_list['mrp']['price']
                discount_price = price_list['discount']['price']
                logger.info("MRP price: %s, Discounted price: %s", mrp_price, discount_price)

            yield {
                "medicine_name": heading,
                "retail_price": mrp_price,
                "discounted_price": discount_price
            }
        except AttributeError as AE:
            logger.error("Request failed: %s", AE)
            raise HTTPException(status_code=500, detail="OOPS somthing went wrong !!!")
        except Exception as e:
            logger.error("Request failed: %s", e)
            raise HTTPException(status_code=500, detail="OOPS somthing went wrong !!!")

    else:
        raise HTTPException(status_code=400,
                            detail="The provided URL is invalid. Please check the format and try again.!!")


async def get_urls(start_page=1, end_page=336):
    """
       Asynchronously fetches URLs of medicines from a paginated website.

       This function iterates through pages from `start_page` to `end_page` (inclusive),
       scraping the 1mg website to extract medicine names and their corresponding URLs.
       If the data is missing or malformed, an error is logged.

       Args:
           start_page (int): The starting page number for scraping (default is 1).
           end_page (int): The ending page number for scraping (default is 336).

       Yields:
           dict: A dictionary containing 'medicine_name' and 'url' for each medicine.
       """
    logger.info(f"Starting URL scraping from page {start_page} to {end_page}")
    for i in range(start_page, end_page):
        website_url = f"https://www.1mg.com/drugs-all-medicines?page={i}"
        logger.debug(f"Requesting URL: {website_url}")
        try:

            response = requests.get(website_url, headers=headers)
            html_content = response.text

            # soup = BeautifulSoup(html_content, 'lxml')  # html.parser
            json_str = html_content.split('window.__INITIAL_STATE__ = ')

            data: dict = json.loads(json_str[1].split(';\n')[0])
            links = data['shellReducer']['schema']['schema']['itemListElement']

            if not data:
                logger.error(f"Data missing on page number: {i}")
            else:
                for dic_dict in links:
                    logger.debug(f"Found medicine: {dic_dict.get('name', 'Unknown')}", )
                    yield {
                        "medicine_name": dic_dict.get('name', None),
                        "url": dic_dict.get('url', None)
                    }
        except Exception as e:
            logger.error("Error occurred while scraping page %d: %s", i, e)

    logger.info("Completed URL scraping from page %d to %d", start_page, end_page)


async def add_urls():
    """
    One-time API call to fetch URLs and add them to the medicine database.

    This function retrieves a list of URLs from the `get_urls` function for the specified range
    and then adds each URL to the medicine database by calling the `add_urls_to_medicine` function.

    Returns:
        dict: A status message indicating success
    """
    try:
        logger.info("Starting the process of adding URLs to the database.")

        urls = get_urls(1, 10)
        async for url in urls:
            logger.debug(f"Adding URL for medicine: { url.get('medicine_name')}")

            await add_urls_to_medicine(url)
        logger.info("Successfully added URLs for all medicines.")

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error occurred while adding URLs: {e}")
        return {"status": "failure", "error": str(e)}