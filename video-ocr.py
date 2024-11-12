import streamlit as st
import cv2
import pytesseract
import pandas as pd
import tempfile
import os
from datetime import timedelta
import sqlite3
import uuid

def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ocr_results (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        text TEXT
    )
    ''')
    conn.commit()

def insert_result(conn, session_id, timestamp, text):
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO ocr_results (id, timestamp, text)
    VALUES (?, ?, ?)
    ''', (f"{session_id}_{timestamp}", timestamp, text))
    conn.commit()

def get_results(conn, session_id):
    cursor = conn.cursor()
    cursor.execute('''
    SELECT timestamp, text FROM ocr_results
    WHERE id LIKE ?
    ORDER BY timestamp
    ''', (f"{session_id}_%",))
    return cursor.fetchall()

def process_video(video_file, session_id):
    # Create a temporary file to store the uploaded video
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        tmp_file.write(video_file.read())
        video_path = tmp_file.name

    # Open the video file
    video = cv2.VideoCapture(video_path)

    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    # Connect to SQLite database
    conn = sqlite3.connect('ocr_results.db')
    create_table(conn)

    # Process video frames
    for frame_number in range(frame_count):
        ret, frame = video.read()
        if not ret:
            break

        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Perform OCR
        text = pytesseract.image_to_string(gray)

        # Calculate timestamp
        timestamp = str(timedelta(seconds=frame_number/fps))

        # Insert results if text is found
        if text.strip():
        # Update progress bar
        progress = (frame_number + 1) / frame_count
        progress_bar.progress(progress)

    # Release video object and delete temporary file
    video.release()
    os.unlink(video_path)

    # Fetch all results for this session
    results = get_results(conn, session_id)
    conn.close()

    return pd.DataFrame(results, columns=['timestamp', 'text'])

# Streamlit app
st.title('Video OCR App with Database Storage')

# Generate a unique session ID
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# File uploader
uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov'])

if uploaded_file is not None:
    # Process video and display results
    st.write("Processing video...")
    progress_bar = st.progress(0)
    df = process_video(uploaded_file, st.session_state.session_id)
    st.write("OCR Results:")
    st.dataframe(df)

    # Create download link for CSV
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="ocr_results.csv",
        mime="text/csv"
    )
