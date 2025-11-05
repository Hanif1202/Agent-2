import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from livekit import api
from livekit.api import LiveKitAPI, ListRoomsRequest
#import redis.asyncio as redis

load_dotenv()

print(f"DEBUG: LIVEKIT_API_KEY exists: {bool(os.getenv('LIVEKIT_API_KEY'))}")
print(f"DEBUG: LIVEKIT_API_SECRET exists: {bool(os.getenv('LIVEKIT_API_SECRET'))}")
print(f"DEBUG: LIVEKIT_URL: {os.getenv('LIVEKIT_URL')}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

async def get_rooms():
    api = LiveKitAPI()
    rooms = await api.room.list_rooms(ListRoomsRequest())
    await api.aclose()
    return [room.name for room in rooms]

def get_dynamic_room_name():
    return "call-main"

@app.route("/api/getActiveRoom", methods=["GET"])
def get_active_room():
    try:
        room = "call-main"
        return jsonify({"room": room})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/getToken", methods=["POST"])
@app.route("/api/getToken", methods=["POST"])
def get_token_post():
    try:
        data = request.get_json()
        print(f"DEBUG: Received data: {data}")

        if data is None:
            print("DEBUG: No JSON data received")
            return jsonify({"error": "No JSON data provided"}), 400

        name = data.get("name", "my name")
        room = data.get("room", None)

        print(f"DEBUG: name='{name}', room='{room}'")

        if not room:
            room = "call-main"
            print(f"DEBUG: Using default room: {room}")

        if not room.startswith("call-"):
            print(f"DEBUG: Room validation failed: '{room}' doesn't start with 'call-'")
            return jsonify({"error": "Invalid room name format"}), 400

        print("DEBUG: Creating token...")
        token = api.AccessToken(os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET")) \
            .with_identity(name) \
            .with_name(name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room
            ))

        jwt_token = token.to_jwt()
        print(f"DEBUG: Token created successfully for room: {room}")
        return jsonify({"token": jwt_token, "room": room})

    except Exception as e:
        print(f"DEBUG: Exception in get_token_post: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # ✅ Render uses this
    app.run(host="0.0.0.0", port=port, debug=True)

 
