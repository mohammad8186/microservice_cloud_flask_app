import base64
import hashlib
import hmac
import os
from datetime import datetime

import requests
from boto3 import s3
from flask import Flask, request, jsonify
import boto3
import logging
from botocore.exceptions import ClientError
import pika
import logging
app = Flask(__name__)


# becouse of public repository . filling complete secret data is not recommended , user can fill them base on his or her needs
# Replace with your actual credentials

#Liara Information
LIARA_CONNECTION_STRING = '.......'

#Arvancloud Information
ARVANCLOUD_ACCESS_KEY = '.........'
ARVANCLOUD_SECRET_KEY = '......'
ARVANCLOUD_BUCKET_NAME = '........'
ARVANCLOUD_ENDPOINT = '.........'

#RabbitMq Information
RABBIT_MQ_SERVER_NAME = '.......'
RABBIT_MQ_QUEUE_NAME = '.........'


# Sample database table (adjust as needed)
# Assume you have a table named "audio_requests" with columns: id, email, status, song_id
import psycopg2

def save_audio_request_in_database(email):
    try:
        conn = psycopg2.connect(LIARA_CONNECTION_STRING)
        cursor = conn.cursor()

        # Insert data into the table
        cursor.execute(
            "INSERT INTO audio_requests (email, status, song_id) VALUES (%s, %s, %s) RETURNING id",
            (email, 'pending', None)  # Set initial status and empty song_id
        )
        request_id = cursor.fetchone()[0]  # Get the inserted ID

        # Close the connection
        cursor.close()
        conn.commit()
        conn.close()

        return request_id
    except Exception as e:
        print(f"Error saving audio request: {e}")
        return None

def upload_audio_to_arvancloud(file , filename):
    storage = boto3.client('s3',
        aws_access_key_id=ARVANCLOUD_ACCESS_KEY,
        aws_secret_access_key=ARVANCLOUD_SECRET_KEY,
        endpoint_url=ARVANCLOUD_ENDPOINT

    )
    try:
        storage.put_object(
            Bucket = ARVANCLOUD_BUCKET_NAME,
            ACL = 'private' ,
            Body = file ,
            Key = filename)  # Corrected here

        print('send obj')

    except ClientError as e:
        logging.error(e)

def publish_audio_id_to_queue(audio_id):
        try:
            # Establishing a connection to RabbitMQ server
            url_params = pika.URLParameters('....') # Replace with your RabbitMQ server details
            connection = pika.BlockingConnection(url_params)
            channel = connection.channel()

            # Declaring the queue (if not already created)

            channel.queue_declare(queue=RABBIT_MQ_QUEUE_NAME)

            # Publishing the audio ID to the queue
            channel.basic_publish(exchange='', routing_key=RABBIT_MQ_QUEUE_NAME, body=str(audio_id))

            # Close the connection
            connection.close()
            logging.info(f"Audio ID '{audio_id}' published to queue '{RABBIT_MQ_QUEUE_NAME}'")
        except Exception as e:
            logging.error(f"Error publishing audio ID to RabbitMQ: {e}")



def update_request_status(db_connection_string, request_id, new_status):
    try:
        # Establishing a connection to the database
        conn = psycopg2.connect(db_connection_string)
        cursor = conn.cursor()

        # SQL statement to update the status
        update_sql = "UPDATE audio_requests SET status = %s WHERE id = %s"

        # Executing the update statement
        cursor.execute(update_sql, (new_status, request_id))

        # Commiting the changes
        conn.commit()

        # Closing the cursor and the connection
        cursor.close()
        conn.close()

        return "Status updated successfully."
    except Exception as e:
        return f"An error occurred: {e}"


@app.route('/read_from_RabbitMq' , methods= ['GET'])
def read_from_RabbitMq():
    #try:
        # Step 1: Receiving the ID from RabbitMQ
        url_params = pika.URLParameters(
            '....')
        connection = pika.BlockingConnection(url_params)
        channel = connection.channel()
        method_frame, header_frame, body = channel.basic_get(queue=RABBIT_MQ_QUEUE_NAME)
        if method_frame:
            audio_id = body.decode('utf-8')
            audio_id = int(audio_id)
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        return audio_id


def read_from_ObjectStorege(filename , bucket):
    try:
        s3 = boto3.client('s3', aws_access_key_id=ARVANCLOUD_ACCESS_KEY, aws_secret_access_key=ARVANCLOUD_SECRET_KEY ,
                          endpoint_url=ARVANCLOUD_ENDPOINT)
        body = s3.get_object(Bucket = bucket , Key = filename)["Body"]
        print('content-type: ',s3.get_object(Bucket = bucket , Key = filename)['ContentType'])
        logging.info("Got Object  '%s' from bucket '%s' . ",
                     filename , bucket)
    except ClientError:
        logging.exception("Couldn't get object '%s' from bucket '%s' . "
                          ,filename,
                          bucket)
        raise
    else:
        return body


@app.route('/service_1/readobj', methods=['GET'])
def read_from_obj():
    try:
        result = read_from_ObjectStorege(request.args.get('filename'), request.args.get('bucket'))
        print(result)
        return result  # Returning the result as the response
    except Exception as e:
        print(str(e))  # Printing the error message
        return str(e), 500  # Returning the error message as the response








def identify_use_shazamAPI(audio_file_content):



        url = "....."

        # The 'audio_file_content' is the binary content of the audio file received from object storage
        files = {'upload_file': ('filename.mp3', audio_file_content, 'audio/mpeg')}

        headers = {
            "X-RapidAPI-Key": "......",
            "X-RapidAPI-Host": "....."
        }

        response = request.post(url, files=files, headers=headers)

        if response.status_code == 200:
            # If the request is successful, parse the JSON response
            response_data = response.json()

            # Extracting the first song from the list of predicted songs
            if 'tracks' in response and ['tracks']:
                song_title = response['tracks'][0]['title']
                return song_title
        else:
            # If there's an error, return the status code and error message
            return {'status_code': response.status_code, 'error': response.text}




def search_track_Spotify(track_name):
    search_url = "......"
    querystring = {"q": track_name, "type": "tracks", "offset": "0", "limit": "1", "numberOfTopResults": "1"}
    headers = {
        "X-RapidAPI-Key": "...",
        "X-RapidAPI-Host": "....."
    }
    response = request.get(search_url, headers=headers, params=querystring)
    if response.status_code == 200:
        search_results = response.json()
        # Extracting the Spotify ID of the first result
        spotify_id = search_results['tracks']['items'][0]['id']
        return spotify_id
    else:
        return None



def get_recommendations(spotify_id):
    recommend_url = "....."
    querystring = {"seed_tracks": spotify_id, "limit": "5"}
    headers = {
        "X-RapidAPI-Key": "....",
        "X-RapidAPI-Host": "...."
    }
    response = request.get(recommend_url, headers=headers, params=querystring)
    if response.status_code == 200:
        recommend_results = response.json()
        return recommend_results['tracks']
    else:
        return None



def send_email_via_mailgun(recipient, subject, text):
    try:
        return request.post(
            ".....",
            auth=("api", "...."),
            data={"from": ".....",
                  "to": [recipient],
                  "subject": subject,
                  "text": text})

    except :
        return 'message sending failed'





#service 1
@app.route('/service_1', methods=['POST'])
def register_audio():
    try:
        # Extracting data from the request
        recipient_email = request.form.get('email')
        music = request.files['audio']  # Access the uploaded file

        # Saving audio request to LiaraSQL
        request_id = save_audio_request_in_database(recipient_email)
        #uploading to arvancloud
        #upload_audio_to_arvancloud(music , music.filename)
        #upload in RabbitMq
        #publish_audio_id_to_queue(request_id)




        if request_id:
            # Writing audio ID to RabbitMQ queue (replacing with actual code)
            # Example: Using RabbitMQ SDK to publish the message
            # ...

            # Sending appropriate response to the user
            return jsonify({'message': 'Audio registration successful!', 'id': request_id})
        else:
            return jsonify({'error': 'Failed to save audio request'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



#service 2 and service 3

@app.route("/service_2"  , methods = ['POST'])
def service_2():

    audio_id = read_from_RabbitMq()
    audio_content=read_from_ObjectStorege()
    track_name = identify_use_shazamAPI(audio_content)
    spotify_id = search_track_Spotify(track_name)
    text=get_recommendations(spotify_id)
    message = update_request_status(LIARA_CONNECTION_STRING , audio_id , 'ready')
    if "Status updated successfully." == message:

         send_email_via_mailgun(recipient='mohammad.sh8186@gmail.com' , subject='the recommendations' , text=text)
         message = update_request_status(LIARA_CONNECTION_STRING, audio_id, 'done')
         if 'message sending failed'==message:
              update_request_status(LIARA_CONNECTION_STRING, audio_id, 'failure')

