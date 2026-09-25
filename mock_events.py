import sqlite3
import requests
import time

def generate_mock_events():
    # 1. Get first business ID from sqlite
    conn = sqlite3.connect('humana.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM businesses LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("No business found in the database. Please create an account in the UI first.")
        return
        
    business_id = row[0]
    print(f"Generating events for business_id: {business_id}")
    
    events = [
        {"business_id": business_id, "event_type": "conversation_started", "data_json": "{}"},
        {"business_id": business_id, "event_type": "conversation_started", "data_json": "{}"},
        {"business_id": business_id, "event_type": "conversation_started", "data_json": "{}"},
        {"business_id": business_id, "event_type": "conversation_started", "data_json": "{}"},
        {"business_id": business_id, "event_type": "conversation_started", "data_json": "{}"},
        {"business_id": business_id, "event_type": "handoff_human", "data_json": "{}"},
        {"business_id": business_id, "event_type": "handoff_human", "data_json": "{}"},
        {"business_id": business_id, "event_type": "order_completed", "amount": 120.50, "data_json": '{"item":"Premium Widget"}'},
        {"business_id": business_id, "event_type": "order_completed", "amount": 45.00, "data_json": '{"item":"Basic Service"}'},
        {"business_id": business_id, "event_type": "order_completed", "amount": 299.99, "data_json": '{"item":"Enterprise AI Package"}'}
    ]
    
    for event in events:
        try:
            res = requests.post("http://localhost:8000/api/events", json=event)
            print(f"Posted {event['event_type']} -> {res.status_code}")
        except Exception as e:
            print(f"Error posting event: {e}")
        time.sleep(0.1)
        
    print("Mock generation complete. You can now visit the Dashboard and generate an AI dashboard.")

if __name__ == "__main__":
    generate_mock_events()
