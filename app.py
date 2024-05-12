from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import logging
import re
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime
from bson import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_URI = "mongodb+srv://21bcm043:Mar2003@internship.pmxvooh.mongodb.net/?retryWrites=true&w=majority&appName=Internship"
try:
    client = MongoClient(MONGO_URI)
    db = client['ProductDatabase']
    products_collection = db['ProductDetails']
    bucket_list_collection = db['BucketList']
    logger.info("Connected to MongoDB successfully!")
except PyMongoError as e:
    logger.error("Error connecting to MongoDB: %s", e)

# Utility function for scraping product data
def scrape_product_data(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 OPR/72.0.3815.378"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "lxml")

        # Extracting price
        price_element = soup.find("span", class_=re.compile(r'a-price'))
        price_with_currency = price_element.text.strip() if price_element else "Price not found"

        # Extracting description
        description_element = soup.find("span", id="productTitle")
        description = description_element.text.strip() if description_element else "Description not found"

        # Extracting customer ratings
        ratings_element = soup.find("span", id="acrCustomerReviewText")
        ratings = ratings_element.text.strip() if ratings_element else "Customer Ratings not found"

        # Extracting number of customer reviews
        reviews_element = soup.find("span", id="acrPopover")
        reviews = reviews_element.text.strip() if reviews_element else "Number of Reviews not found"

        # Extracting images
        images = soup.find_all("img", class_="a-dynamic-image")
        image_urls = [image["src"] for image in images[:2]] if images else ["Product images not found"]

        # Extracting specifications
        specifications_element = soup.find("div", id="productOverview_feature_div")
        specifications = specifications_element.find_all("tr") if specifications_element else []
        specifications_dict = {cell[0].text.strip(): cell[1].text.strip() for cell in [row.find_all("td") for row in specifications]}

        # Extracting current price
        current_price_element = soup.find("span", class_="a-price-whole")
        current_price = float(current_price_element.text.strip().replace(',', '')) if current_price_element else None

        return {
            "description": description,
            "price": price_with_currency[:-4],
            "customer_ratings": ratings,
            "number_of_reviews": reviews[4:],
            "image_urls": image_urls,
            "specifications": specifications_dict,
            "current_price": current_price
        }
    except Exception as e:
        logger.error("Error occurred while scraping: %s", e)
        return None

# Route for scraping product data
@app.route('/scrape', methods=['GET'])
def scrape_endpoint():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is missing'}), 400

    product_data = scrape_product_data(url)
    if product_data:
        product_data["timestamp"] = datetime.now()
        try:
            products_collection.insert_one(product_data)
            logger.info("Product data inserted into MongoDB")
        except PyMongoError as e:
            logger.error("Error inserting product data into MongoDB: %s", e)
        return jsonify(product_data)
    else:
        return jsonify({'error': 'Failed to scrape product data'}), 500

# Route for adding a product to the bucket list
@app.route('/add_to_bucket_list', methods=['POST'])
def add_to_bucket_list():
    data = request.get_json()
    if not data or 'url' not in data or 'shortName' not in data:
        return jsonify({"error": "Invalid request body"}), 400

    try:
        result = bucket_list_collection.insert_one(data)
        logger.info("Product added to bucket list: %s", data)
        return jsonify({"message": "Bucket item added successfully", "id": str(result.inserted_id)})
    except PyMongoError as e:
        logger.error("Error adding product to bucket list: %s", e)
        return jsonify({"error": "Failed to add product to bucket list"}), 500

# Route for retrieving the bucket list
@app.route('/get_bucket_list', methods=['GET'])
def get_bucket_list():
    try:
        bucket_list = list(bucket_list_collection.find({}, {"_id": 0}))
        return jsonify(bucket_list)
    except PyMongoError as e:
        logger.error("Error retrieving bucket list: %s", e)
        return jsonify({"error": "Failed to retrieve bucket list"}), 500

# Route for updating a product in the bucket list
@app.route('/update_bucket_list/<string:_id>', methods=['PUT'])
def update_bucket_list(_id):
    data = request.get_json()
    if not data or 'url' not in data or 'shortName' not in data:
        return jsonify({"error": "Invalid request body"}), 400

    try:
        result = bucket_list_collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
        if result.modified_count == 1:
            logger.info("Bucket item updated: %s", data)
            return jsonify({"message": "Bucket item updated successfully"})
        else:
            return jsonify({"error": "Failed to update bucket item"}), 400
    except PyMongoError as e:
        logger.error("Error updating bucket item: %s", e)
        return jsonify({"error": "Failed to update bucket item"}), 500

# Route for deleting a product from the bucket list
@app.route('/delete_from_bucket_list/<string:_id>', methods=['DELETE'])
def delete_from_bucket_list(_id):
    try:
        result = bucket_list_collection.delete_one({"_id": ObjectId(_id)})
        if result.deleted_count == 1:
            logger.info("Bucket item deleted: %s", _id)
            return jsonify({"message": "Bucket item deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete bucket item"}), 400
    except PyMongoError as e:
        logger.error("Error deleting bucket item: %s", e)
        return jsonify({"error": "Failed to delete bucket item"}), 500

# Route for retrieving price history of a product
@app.route('/price-history', methods=['GET'])
def get_price_history():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is missing'}), 400

    try:
        price_history = list(products_collection.find({"url": url}, {"_id": 0, "current_price": 1, "timestamp": 1}))
        return jsonify(price_history)
    except PyMongoError as e:
        logger.error("Error retrieving price history: %s", e)
        return jsonify({"error": "Failed to retrieve price history"}), 500

# Route for configuring email for price notifications
@app.route('/configure-email', methods=['POST'])
def configure_email():
    data = request.get_json()
    if not data or 'email' not in data or 'url' not in data:
        return jsonify({"error": "Invalid request body"}), 400

    try:
        products_collection.update_one({'url': data['url']}, {'$set': {'email': data['email']}}, upsert=True)
        logger.info("Email configuration successful for URL: %s", data['url'])
        return jsonify({'message': 'Email configuration successful'})
    except PyMongoError as e:
        logger.error("Error configuring email: %s", e)
        return jsonify({'error': 'Failed to configure email'}), 500

if __name__ == '__main__':
    app.run(debug=True)
