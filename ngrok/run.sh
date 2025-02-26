python main.py &

pkill ngrok
ngrok http 5050 --url=$NGROK_URL
# ngrok tunnel --label edge=$NGROK_EDGE http://localhost:5050
