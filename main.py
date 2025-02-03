import requests
import openai
import random
import json
from auth_config import WOOCOMMERCE_CONSUMER_KEY, WOOCOMMERCE_CONSUMER_SECRET, OPENAI_API_KEY
from urllib.parse import urlparse

# WooCommerce API Base URL
WOOCOMMERCE_BASE_URL = "https://wordpress-1004298-3881926.cloudwaysapps.com/wp-json/wc/v3"

def get_product_info(product_url):
    """
    Fetch product information from WooCommerce API using product URL.
    :param product_url: URL of the product.
    :return: Dictionary containing product info (title, description, short description).
    """
    try:
        # Extract product slug from URL
        slug = product_url.rstrip("/").split("/")[-1]
        response = requests.get(
            f"{WOOCOMMERCE_BASE_URL}/products?slug={slug}",
            auth=(WOOCOMMERCE_CONSUMER_KEY, WOOCOMMERCE_CONSUMER_SECRET)
        )
        
        if response.status_code == 200 and response.json():
            product = response.json()[0]
            return {
                "product_id": product["id"],
                "title": product["name"],
                "description": product["description"],
                "short_description": product["short_description"]
            }
        else:
            raise ValueError("Product not found or invalid URL.")
    except Exception as e:
        raise RuntimeError(f"Error fetching product info: {e}")

def extract_store_name(product_url):
    """
    Extract the store name from the product URL's domain.
    :param product_url: URL of the product.
    :return: Store name.
    """
    try:
        domain = urlparse(product_url).hostname
        store_name = domain.split(".")[0].capitalize() if domain else "Store"
        return store_name
    except Exception as e:
        raise RuntimeError(f"Error extracting store name: {e}")

def load_reviewer_names():
    """
    Load reviewer names from the user_data.json file.
    :return: List of reviewer names.
    """
    try:
        with open("user_data.json", "r") as file:
            data = json.load(file)
            return data["reviewer_names"]
    except Exception as e:
        raise RuntimeError(f"Error loading reviewer names: {e}")

def introduce_typos(text):
    """
    Randomly introduce typos into a given text to mimic human errors.
    :param text: Original text.
    :return: Text with typos.
    """
    if random.random() > 0.3:  # Introduce typos in ~30% of cases
        return text

    words = text.split()
    if len(words) < 2:
        return text  # Skip if too short

    # Randomly choose a word to misspell
    index = random.randint(0, len(words) - 1)
    word = words[index]
    if len(word) > 3:
        typo = word[:random.randint(1, len(word) - 2)] + word[random.randint(1, len(word) - 1):]
        words[index] = typo
    return " ".join(words)

def clean_review_text(text):
    """
    Remove quotation marks from the review text.
    :param text: Original text.
    :return: Cleaned text without quotation marks.
    """
    return text.replace('"', '').replace("'", "")

def generate_reviews_with_openai(product_info, store_name, store_category):
    """
    Generate 10 reviews using OpenAI API: 7 for store services (6 short, 1 normal length) and 3 for product-specific feedback.
    :param product_info: Dictionary containing product details.
    :param store_name: Name of the store extracted from the product URL.
    :param store_category: Category of the store (e.g., electronics, clothing, cannabis).
    :return: List of reviews (review, reviewer_name).
    """
    try:
        openai.api_key = OPENAI_API_KEY
        reviews = []
        reviewer_names = load_reviewer_names()
        random.shuffle(reviewer_names)  # Shuffle names to ensure randomness

        # Generate 7 store reviews
        for i in range(7):
            if i < 6:  # First 6 are short reviews
                store_prompt = f"""
                Write a very short and casual customer review (1 sentence) about the store {store_name} specializing in {store_category}.
                Example: "This is a great store!" or "{store_name} gives me the best deals ever!"
                """
            else:  # 7th review is longer
                store_prompt = f"""
                Write a short and engaging customer review (2-3 sentences) about the store {store_name} specializing in {store_category}.
                Mention aspects like fast delivery, great customer service, or easy checkout.
                The review should sound natural, human-like, and occasionally include minor typos or slang.
                """

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": store_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            review_text = response['choices'][0]['message']['content'].strip()
            review_text = introduce_typos(clean_review_text(review_text))  # Add typos and remove quotation marks
            reviewer_name = reviewer_names.pop() if reviewer_names else "Anonymous"
            reviews.append((review_text, reviewer_name))

        # Generate 3 product reviews
        product_prompt = f"""
        Write a short and engaging product review (2-3 sentences) for the following product sold by {store_name}, specializing in {store_category}:
        - Title: {product_info['title']}
        - Description: {product_info['description']}
        - Short Description: {product_info['short_description']}
        
        The review should sound authentic, human-like, and occasionally use casual language or slang.
        """

        for _ in range(3):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": product_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            review_text = response['choices'][0]['message']['content'].strip()
            review_text = introduce_typos(clean_review_text(review_text))  # Add typos and remove quotation marks
            reviewer_name = reviewer_names.pop() if reviewer_names else "Anonymous"
            reviews.append((review_text, reviewer_name))

        random.shuffle(reviews)  # Shuffle reviews to mix short and long reviews
        return reviews

    except Exception as e:
        raise RuntimeError(f"Error generating reviews: {e}")

def post_review_to_woocommerce(product_id, review, reviewer_name, reviewer_email=None, rating=5):
    """
    Post the generated review to WooCommerce API.
    :param product_id: ID of the product to review.
    :param review: Generated review content.
    :param reviewer_name: Name of the reviewer.
    :param reviewer_email: Email of the reviewer.
    :param rating: Rating for the product (default is 5).
    :return: Response from the WooCommerce API.
    """
    try:
        if reviewer_email is None:
            reviewer_email = f"{reviewer_name.replace(' ', '').lower()}@gmail.com"

        payload = {
            "product_id": product_id,
            "review": review,
            "reviewer": reviewer_name,
            "reviewer_email": reviewer_email,
            "rating": rating
        }

        response = requests.post(
            f"{WOOCOMMERCE_BASE_URL}/products/reviews",
            json=payload,
            auth=(WOOCOMMERCE_CONSUMER_KEY, WOOCOMMERCE_CONSUMER_SECRET)
        )

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise ValueError(f"Failed to post review: {response.status_code}, {response.text}")
    except Exception as e:
        raise RuntimeError(f"Error posting review: {e}")

if __name__ == "__main__":
    try:
        # Get input from the user
        product_url = input("Enter the product URL: ")
        store_category = input("Enter the store category (e.g., electronics, clothing): ")

        # Step 1: Get product info
        try:
            product_info = get_product_info(product_url)
        except Exception as e:
            print(e)
            exit()

        # Step 2: Extract store name
        try:
            store_name = extract_store_name(product_url)
        except Exception as e:
            print(e)
            exit()

        # Step 3: Generate 10 reviews
        try:
            reviews = generate_reviews_with_openai(product_info, store_name, store_category)
        except Exception as e:
            print(e)
            exit()

        # Step 4: Post reviews to WooCommerce
        try:
            for review, reviewer_name in reviews:
                review_response = post_review_to_woocommerce(
                    product_id=product_info["produQct_id"],
                    review=review,
                    reviewer_name=reviewer_name
                )
                print("Review successfully posted:", review_response)
        except Exception as e:
            print(e)
            exit()

    except Exception as e:
        print("Error:", e)
