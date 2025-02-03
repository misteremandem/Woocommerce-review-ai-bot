import requests
import openai
import random
import json
from urllib.parse import urlparse
from auth_config import OPENAI_API_KEY

# Load store information and API credentials from store_info.json
STORE_INFO_FILE = "store_info.json"

# WooCommerce API Base URL
WOOCOMMERCE_BASE_URL_TEMPLATE = "{base_url}/wp-json/wc/v3"

def load_store_info():
    """
    Load store information from the store_info.json file.
    :return: Dictionary containing store information.
    """
    try:
        with open(STORE_INFO_FILE, "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading store information: {e}")
        exit()

def get_product_info(product_url, consumer_key, consumer_secret):
    """
    Fetch product information from WooCommerce API using product URL.
    """
    try:
        slug = product_url.rstrip("/").split("/")[-1]
        base_url = urlparse(product_url).scheme + "://" + urlparse(product_url).hostname
        woocommerce_base_url = WOOCOMMERCE_BASE_URL_TEMPLATE.format(base_url=base_url)

        response = requests.get(
            f"{woocommerce_base_url}/products?slug={slug}",
            auth=(consumer_key, consumer_secret)
        )
        response.raise_for_status()

        if response.json():
            product = response.json()[0]
            return {
                "product_id": product["id"],
                "title": product["name"],
                "description": product["description"],
                "short_description": product["short_description"]
            }
        else:
            raise ValueError("Product not found or invalid URL.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product info: {e}")
        exit()

def extract_store_name(product_url):
    """
    Extract the store name from the product URL's domain.
    """
    try:
        domain = urlparse(product_url).hostname
        return domain.split(".")[0].capitalize() if domain else "Store"
    except Exception as e:
        print(f"Error extracting store name: {e}")
        exit()

def load_reviewer_names():
    """
    Load reviewer names from the user_data.json file.
    """
    try:
        with open("user_data.json", "r") as file:
            data = json.load(file)
            return data["reviewer_names"]
    except Exception as e:
        print(f"Error loading reviewer names: {e}")
        exit()

def generate_reviews_with_openai(product_info, store_name, store_category):
    """
    Generate 10 reviews using OpenAI API.
    """
    try:
        openai.api_key = OPENAI_API_KEY
        reviews = []
        reviewer_names = load_reviewer_names()
        random.shuffle(reviewer_names)

        for i in range(7):
            prompt = f"Write a {'very short' if i < 6 else 'short'} review about {store_name} specializing in {store_category}."
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            review_text = response['choices'][0]['message']['content'].strip()
            reviewer_name = reviewer_names.pop() if reviewer_names else "Anonymous"
            reviews.append((review_text, reviewer_name))

        random.shuffle(reviews)
        return reviews
    except Exception as e:
        print(f"Error generating reviews: {e}")
        exit()

if __name__ == "__main__":
    try:
        store_info = load_store_info()
        store_name = input("Enter the store name: ").strip()
        if store_name not in store_info:
            print("Store not found in store_info.json")
            exit()

        store_data = store_info[store_name]
        consumer_key = store_data["consumer_key"]
        consumer_secret = store_data["consumer_secret"]
        store_category = store_data["category"]

        product_url = input("Enter the product URL: ")
        product_info = get_product_info(product_url, consumer_key, consumer_secret)
        reviews = generate_reviews_with_openai(product_info, store_name, store_category)

        print("Reviews generated successfully!")
        for review in reviews:
            print(review)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit()
