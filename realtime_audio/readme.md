# how to run aoai/openai

you need either the rta key or the openai key.

configure your twilio so that the webhook for incoming call is the ngrok url.

if you are using a trial account, also verify the phone number you are calling from with sms.

open two terminals. run `./webapp.sh` in the first, and `ngrok.sh` in the second.

you should now be able to call the number and hear response in audio from 