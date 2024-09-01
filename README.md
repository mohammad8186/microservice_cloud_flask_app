# in this APP we implemented a song recognition and suggestion service.
# The purpose  is  Getting to know and working with cloud services. From these services to create a database , storage
# we  use audio file, send email and recognize and suggest songs.


All the services and how they are connected are shown in the image below, which is an architecture: 

![Screenshot 2024-09-01 083034](https://github.com/user-attachments/assets/47379be9-df64-45d2-b0e9-df1f4418e255)


Also, to interact with the main backend app, two simple frontends are considered for sending requests from the user.



we used these services:  RabbitMq --> Message Broker 
                         LiaraPostgres ---> Database as a Service(Daas)
                         Arvan Cloud Object Storage ------> Object Storage


out backend app sends APIs to :  Shazam API to get Spotify ID
                                 SpotifyAPI to get  music information

                                 

The general description is as follows:

First Service:
First, a request containing the recipient's email and the audio file of the desired song will be received. Audio file sent in
An object store
is saved Other request information with pending status is stored in the database
can be If this step is successful, the appropriate message will be displayed to the user. Then ID
The request is written to the RabbitMQ queue to be processed.



Second service:
In this service, the process of recognizing the song and finding the SpotifyID of the song is done. In this service first
The ID sent is received on RabbitMQ and then the audio file corresponding to the request is received
Object storage is called. Then this file is sent to the Shazam API to get the song information
to be After receiving the song information, we search for its name using Spotify API.
Finally, the SpotifyID related to this song is received and placed in the SongID field of this request in the database
(which is currently empty) is placed. If all these steps are successful, the status
The request in the database changes from pending to ready to indicate that it is ready to be used in the service
is the third.



Third service:
This service reads uncompleted requests with ready status from the database and for
Each of these requests will extract the SongID from the request and send it to the spotify song recommender API
does Then send the suggestions received from the spotify API to the user's email registered in the request
does After the successful completion of these steps, the status of the request will change to done.
