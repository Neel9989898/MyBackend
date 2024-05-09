# from flask import Flask, request, jsonify, send_from_directory
from flask import Flask, request, jsonify, send_from_directory, render_template
from bs4 import BeautifulSoup
import requests
import logging
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from bson import ObjectId
from flask_cors import CORS
# Mar#2003!@00
app = Flask(__name__)
CORS(app)
logger = logging.getLogger(__name__)


uri = "mongodb+srv://21bcm043:Mar2003@internship.pmxvooh.mongodb.net/?retryWrites=true&w=majority&appName=Internship"

client = MongoClient(uri, server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client['ProductDatabase']  # Replace 'your_database_name_here' with your actual database name

# Accessing the collection
products_collection = db['ProductDetails']


@app.route('/scrape', methods=['GET'])
def scrape_product():
    url = request.args.get('url')
    # url = "https://www.amazon.in/Apple-MacBook-Chip-13-inch-256GB/dp/B08N5T6CZ6/ref=sr_1_1_sspa?dib=eyJ2IjoiMSJ9.0wUJxkajdW_AXocIRrc54ysXU75fq8Y4zSe_afkYWsLDtC-yfdnogJsxNFHjtyZRizyAoygfaQDRD15ZqimDaEo67YZ0msPlW77FWQVjmG0zQG2APt3nLqU7X05tVexXHfeYTirgNg999Ec7A6old5ZfDqv1ZNcWx2VTozoifLTSMuz8SqKc8gHbGfckDLTubm7FJMsYcrkT5JeyWqQegpPZDYopxXySmT0zetW8zUs.SvYOrXL1QDdhSR0K9zaTBrO0QWJNcwipJaTeipAlSYw&dib_tag=se&keywords=macbook&qid=1713349039&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1"
    if not url:
        return jsonify({'error': 'URL parameter is missing'}), 400

    try:
        headers_param={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 OPR/72.0.3815.378"}
        r = requests.get(url, headers=headers_param)
        soup = BeautifulSoup(r.content, "lxml")

        # Extracting price
        price = soup.find("span", attrs={"class": "aok-offscreen"}) or soup.find("span", attrs={"class": "a-offscreen"})
        if price:
            price_text = price.text.strip()
            match = re.search(r'(\D*)([\d,.]+)\s*(\w+)', price_text)
            if match:
                price_with_currency = match.group(1) + match.group(2) + ' ' + match.group(3)
                print(price_with_currency[0:-4]);
            else:
                price_with_currency = "Price format not recognized"
                
                
        else:
            price_with_currency = "Price not found"
            print("error")

        # Extracting description
        description = soup.find("span", attrs={"id": "productTitle"})
        description = description.text.strip() if description else "Description not found"

        # Extracting customer ratings
        ratings = soup.find("span", attrs={"id": "acrCustomerReviewText"})
        ratings = ratings.text.strip() if ratings else "Customer Ratings not found"

        # Extracting number of customer reviews
        reviews = soup.find("span", attrs={"id": "acrPopover"})
        reviews = reviews.text.strip() if reviews else "Number of Reviews not found"

        # Extracting images
        images = soup.find_all("img", attrs={"class": "a-dynamic-image"})
        image_urls = [image["src"] for image in images] if images else ["Product images not found"]
        image_urls = image_urls[:2]
        # Extracting specifications
        specifications = soup.find("div", attrs={"id": "productOverview_feature_div"})
        specifications = specifications.find_all("tr") if specifications else []

        specifications_dict = {}
        for row in specifications:
            cells = row.find_all("td")
            if cells:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                specifications_dict[key] = value
        
        price_element = soup.find("span", attrs={"class": "a-price-whole"})
        if price_element:
            price_text = price_element.text.strip()
            # Remove commas and convert to integer
            current_price = float(price_text.replace(',', ''))
        else:
            current_price = None 
        
        timestamp = datetime.now()

        products_collection.insert_one({
            "url": url,
            "description": description,
            "current_price": current_price,
            "timestamp": timestamp
            
        })
        return jsonify({
            "description": description,
            "price": price_with_currency[:-4],
            "customer_ratings": ratings,
            "number_of_reviews": reviews[4:],
            "image_urls": image_urls,
            "specifications": specifications_dict
        })
        # return "testing"

    except Exception as e:
        logger.exception("An error occurred during scraping:")
        return jsonify({'error': 'Internal server error'}), 500


bucket_list_collection = db["BucketList"]  # Your collection name

@app.route('/add_to_bucket_list', methods=['POST'])
def add_to_bucket_list():
    try:
        data = request.get_json()
        print(data)
    
        if data:
            bucket_item = {
                "url": data.get("url"),
                "shortName": data.get("shortName"),
                # "showUrl": False  # Initially set to False
            }
            # Inserting the bucket item into the collection
            result = bucket_list_collection.insert_one(bucket_item)
            print('Bucket database updated')
            return jsonify({"message": "Bucket item added successfully", "id": str(result.inserted_id)})
            
        else:
            return jsonify({"error": "Invalid request body"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_bucket_list', methods=['GET'])
def get_bucket_list():
    try:
        # Fetch all bucket list items from the collection
        bucket_list = list(bucket_list_collection.find({}, {"_id": 0}))
        return jsonify(bucket_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_bucket_list/<string:_id>', methods=['PUT'])
def update_bucket_list(_id):
    try:
        data = request.get_json()
        if data:
            updated_item = {
                "url": data.get("url"),
                "shortName": data.get("shortName"),
            }
            # Updating the bucket item based on _id
            result = bucket_list_collection.update_one({"_id": ObjectId(_id)}, {"$set": updated_item})
            if result.modified_count == 1:
                return jsonify({"message": "Bucket item updated successfully"})
            else:
                return jsonify({"error": "Failed to update bucket item"}), 400
        else:
            return jsonify({"error": "Invalid request body"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/delete_from_bucket_list/<string:shortName>', methods=['DELETE'])
def delete_from_bucket_list(shortName):
    try:
        # Deleting the bucket item
        result = bucket_list_collection.delete_one({"shortName": shortName})
        if result.deleted_count == 1:
            return jsonify({"message": "Bucket item deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete bucket item"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/price-history', methods=['GET'])
def get_price_history():
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({'error': 'URL parameter is missing'}), 400

        # Query the database for price history of the given URL
        price_history = list(products_collection.find({"url": url}, {"_id": 0, "current_price": 1, "timestamp": 1}))

        return jsonify(price_history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/configure-email', methods=['POST'])
def configure_email():
    try:
        data = request.get_json()
        email = data.get('email')
        url = data.get('url')

        # Update or insert the email address into the ProductDetails collection
        products_collection.update_one(
            {'url': url},
            {'$set': {'email': email}},
            upsert=True
        )

        return jsonify({'message': 'Email configuration successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
