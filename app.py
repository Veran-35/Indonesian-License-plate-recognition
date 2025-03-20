from flask import Flask, jsonify, request, render_template
import mysql.connector
import cv2
import numpy as np
from tensorflow.keras import models
import base64
from io import BytesIO
from PIL import Image
import os
from datetime import datetime
from flask import send_from_directory
from flask import redirect, url_for

app = Flask(__name__)


db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'ml_db'
}
UPLOAD_FOLDER = './uploaded_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 

label_map = {
    0: "0", 1: "1", 2: '2', 3: "3", 4: '4', 5: '5', 6: "6", 7: "7", 8: "8", 9: "9", 10: "A", 11: "B", 12: 'C', 13: "D", 14: "E",
    15: "F", 16: 'G', 17: "H", 18: "I", 19: 'J', 20: 'K', 21: "L", 22: "M", 23: "N", 24: "O", 25: "P", 26: "Q", 27: "R", 28: "S",
    29: "T", 30: "U", 31: "V", 32: "W", 33: "X", 34: "Y", 35: "Z"
}

# Load the trained model
model = models.load_model('./best-model/0.8806-0.3081-0.9333-0.1942.h5')


 

def save_to_database(message, image_path):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        query = "INSERT INTO predictions (response_message, image_path) VALUES (%s, %s)"
        cursor.execute(query, (message, image_path))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()



def process_predict(input_image, warna=None):
    input_size = (40, 40)

    # Convert base64 string to an image
    image_data = base64.b64decode(input_image.split(',')[1])  # Skip base64 metadata
    image = Image.open(BytesIO(image_data))
    image = np.array(image)  # Convert PIL Image to numpy array

    image = cv2.resize(image, (1600, 700))
    image_removed_alpha = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    image_ori = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    gray = cv2.cvtColor(image_removed_alpha, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    rect_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilation = cv2.dilate(thresh, rect_kern, iterations=1)
    contours, hierarchy = cv2.findContours(dilation, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    contours = sorted(contours, key=lambda ctr: cv2.boundingRect(ctr)[0])

    im2 = gray.copy()
    plate_num = ""
    roi_images = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        height, width = im2.shape

        if height / float(h) > 3.5: continue
        ratio = h / float(w)
        if ratio < 1.5: continue
        if width / float(w) > 38: continue
        area = h * w
        if area < 100: continue
        cv2.rectangle(dilation, (x, y), (x + w, y + h), (0, 255, 0), 10)
        
        if warna == 'Hitam':
            roi = gray[y:y + h, x:x + w]
            
        
        elif warna=='Putih':
            roi = dilation[y:y + h, x:x + w]
                

        roi_resized = cv2.resize(roi, input_size)
        roi_resized = roi_resized.reshape(1, input_size[0], input_size[1], 1)
        roi_resized = roi_resized.astype('float32') / 255.0

        pred = model.predict(roi_resized)
        predicted_index = np.argmax(pred)
        predicted_char = label_map.get(predicted_index, "?")
        plate_num += str(predicted_char)
        roi_images.append((roi, predicted_char))

    return plate_num


@app.route('/')
def home():
    return render_template('index.html')




@app.route('/history')
def history():
    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  # Use dictionary=True to get column names
        query = "SELECT * FROM predictions ORDER BY id DESC"
        cursor.execute(query)
        results = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        results = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    # Render the results in a template
    return render_template('history.html', predictions=results)


@app.route('/delete_prediction/<int:prediction_id>', methods=['POST'])
def delete_prediction(prediction_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Fetch the image path from the database
        cursor.execute("SELECT image_path FROM predictions WHERE id = %s", (prediction_id,))
        result = cursor.fetchone()
        
        if result:
            image_path = result[0]
            # Delete the image file from the server
            if os.path.exists(image_path):
                os.remove(image_path)
            
            # Delete the prediction record from the database
            cursor.execute("DELETE FROM predictions WHERE id = %s", (prediction_id,))
            connection.commit()

        return redirect('/history')
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({"error": "Failed to delete prediction"}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        warna = data.get('warna')
        image = data.get('image')

        if not image:
            return jsonify({"error": "No image data provided"}), 400

        predict_num = process_predict(image, warna=warna)

        # Save image to disk
        image_binary = base64.b64decode(image.split(',')[1])  # Skip base64 metadata
        image_path = os.path.join('static', 'uploaded_images', f"{predict_num}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png")

        with open(image_path, 'wb') as img_file:
            img_file.write(image_binary)

        if predict_num:  # If the response is not empty
            save_to_database(predict_num, image_path)

        response = {"message": predict_num}
        return jsonify(response)
    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({"error": "Error during prediction"}), 500


if __name__ == '__main__':
    # Disable Flask debug mode to prevent auto-reload causing infinite loops
    app.run(debug=False)
