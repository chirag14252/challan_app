import streamlit as st
import requests
import json
import base64
from PIL import Image
import pandas as pd
from io import BytesIO
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Challan OCR & Data Extractor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def encode_image(image):
    """Convert PIL Image to base64 string"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def list_available_models(api_key):
    """List available Gemini models"""
    try:
        genai.configure(api_key=api_key)
        models = []
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                models.append(model.name)
        return models
    except Exception as e:
        return []

def test_gemini_api_key(api_key):
    """Test if the Gemini API key is working"""
    try:
        genai.configure(api_key=api_key)
        
        # Simple test with text-only model
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello")
        
        if response.text:
            return True, "✅ Gemini API key is working!"
        else:
            return False, "❌ No response from Gemini API"
            
    except Exception as e:
        error_msg = str(e).lower()
        if "api_key" in error_msg or "invalid" in error_msg or "403" in error_msg:
            return False, "❌ Invalid Gemini API key"
        elif "quota" in error_msg or "limit" in error_msg or "429" in error_msg:
            return False, "❌ API quota exceeded"
        elif "404" in error_msg:
            return False, "❌ Model not found - trying different model"
        else:
            return False, f"❌ Gemini API error: {str(e)}"

def analyze_image_with_gemini(image, api_key, model="gemini-1.5-pro"):
    """Analyze image using Google Gemini Vision API - faster processing"""
    
    try:
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize the model
        gemini_model = genai.GenerativeModel(model)
        
        # Prepare the prompt
        prompt = """
        Please analyze this challan/invoice image and extract the following information in JSON format:

        1. Challan Information:
           - challan_number (Job ID from the image)
           - vendor_name (Name of Vendor/Party)
           - date (date from the challan)

        2. Table Data (extract all rows from any tables):
           For each row, extract:
           - description (Description of goods/Item)
           - weight_sent (Weight sent)
           - weight_received (Weight received - if empty, use "0")
           - number_of_bags (No. of bags)
           - plating_color (Plating color)

        Please return the data in this exact JSON structure:
        {
            "challan_info": {
                "challan_number": "",
                "vendor_name": "",
                "date": ""
            },
            "table_data": [
                {
                    "description": "",
                    "weight_sent": "",
                    "weight_received": "",
                    "number_of_bags": "",
                    "plating_color": ""
                }
            ]
        }

        Important notes:
        - If weight_received field is empty or not visible, use "0"
        - Extract all visible rows from any tables in the image
        - If any field is not visible or available, use an empty string ""
        
        Return only the JSON, no additional text.
        """
        
        # Generate content with image
        st.write(f"**Debug Info:** Using Gemini model `{model}`")
        response = gemini_model.generate_content([prompt, image])
        
        if not response.text:
            st.error("❌ No response from Gemini API")
            return None
        
        # Extract JSON from response
        content = response.text.strip()
        
        # Find JSON in the response
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx]
            return json.loads(json_str)
        else:
            st.error("Could not extract JSON from Gemini response")
            with st.expander("🔍 View Raw Response"):
                st.text(content)
            return None
            
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON response: {str(e)}")
        with st.expander("🔍 View Raw Response"):
            st.text(response.text if 'response' in locals() else "No response")
        return None
    except Exception as e:
        error_msg = str(e).lower()
        if "api_key" in error_msg or "invalid" in error_msg or "403" in error_msg:
            st.error("❌ Invalid Gemini API key. Please check your API key.")
        elif "quota" in error_msg or "limit" in error_msg or "429" in error_msg:
            st.error("❌ Gemini API quota exceeded. Please check your usage limits.")
        elif "404" in error_msg or "not found" in error_msg:
            st.error(f"❌ Model '{model}' not found. Try a different model from the dropdown.")
            st.info("💡 Click 'List Models' to see available models for your API key.")
        elif "safety" in error_msg:
            st.error("❌ Content blocked by Gemini safety filters. Try a different image.")
        else:
            st.error(f"❌ Gemini API error: {str(e)}")
            st.info("💡 Try using 'gemini-1.5-flash' model or click 'List Models' to see available options.")
        return None

def send_to_google_sheets(data, script_url, secret_key="abc123"):
    """Send extracted data to Google Apps Script - optimized for your specific script"""
    
    # Prepare data for Google Sheets exactly as your Apps Script expects
    rows = []
    
    challan_info = data.get('challan_info', {})
    table_data = data.get('table_data', [])
    
    # Get current date and timestamp for processing
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Convert table data to rows format for your Google Apps Script
    for item in table_data:
        # Skip if description (Item) is empty
        description = item.get('description', '').strip()
        if not description:
            continue
            
        # Get weight received and handle empty values
        weight_received = item.get('weight_received', '').strip()
        if not weight_received or weight_received == '':
            weight_received = '0'
        
        # Calculate status based on weight received
        try:
            weight_received_num = float(weight_received) if weight_received != '0' else 0
            status = "Received" if weight_received_num > 0 else "Not Received"
        except (ValueError, TypeError):
            status = "Not Received"
        
        # Calculate difference (weight_sent - weight_received)
        try:
            weight_sent_num = float(item.get('weight_sent', '0')) if item.get('weight_sent', '').strip() else 0
            weight_received_num = float(weight_received) if weight_received != '0' else 0
            difference = weight_sent_num - weight_received_num
        except (ValueError, TypeError):
            difference = 0
        
        # New column structure: Job ID, Party/Vendor, Item, Weight Sent, Weight Received, Status, Remarks, Difference, No. of Bags, Plating Colour, Photo Links, Date, Processing Timestamp
        row = [
            challan_info.get('challan_number', ''),  # Job ID
            challan_info.get('vendor_name', ''),     # Party/Vendor
            description,                             # Item
            item.get('weight_sent', ''),             # Weight Sent
            weight_received,                         # Weight Received
            status,                                  # Status
            '',                                      # Remarks (empty as requested)
            str(difference),                         # Difference
            item.get('number_of_bags', ''),          # No. of Bags
            item.get('plating_color', ''),           # Plating Colour
            '',                                      # Photo Links (empty as requested)
            current_date,                            # Date (when photo is uploaded)
            current_timestamp                        # Processing Timestamp (when photo is uploaded)
        ]
        rows.append(row)
    
    # If no table data, still send challan info as a single row
    if not rows:
        row = [
            challan_info.get('challan_number', ''),  # Job ID
            challan_info.get('vendor_name', ''),     # Party/Vendor
            '',                                      # Item (empty)
            '',                                      # Weight Sent (empty)
            '0',                                     # Weight Received (0)
            'Not Received',                          # Status
            '',                                      # Remarks (empty)
            '0',                                     # Difference (0)
            '',                                      # No. of Bags (empty)
            '',                                      # Plating Colour (empty)
            '',                                      # Photo Links (empty)
            current_date,                            # Date
            current_timestamp                        # Processing Timestamp
        ]
        rows.append(row)
    
    # Prepare payload exactly as your Apps Script expects
    payload = {
        "key": secret_key,
        "data": rows
    }
    
    try:
        # Debug: Show what we're sending
        st.write("**Debug Info:**")
        st.write(f"- Script URL: {script_url}")
        st.write(f"- Secret Key: {secret_key}")
        st.write(f"- Number of rows: {len(rows)}")
        
        # Send POST request to your Google Apps Script
        response = requests.post(
            script_url, 
            data=json.dumps(payload),  # Use data parameter with JSON string
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Debug: Show response details
        st.write(f"- Response Status: {response.status_code}")
        st.write(f"- Response Headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        # Check response from your Apps Script
        response_text = response.text.strip()
        if "Success" in response_text:
            return True, f"✅ Successfully added {len(rows)} rows to Google Sheets!"
        elif "Unauthorized" in response_text:
            return False, "❌ Unauthorized: Please check your secret key"
        elif "Invalid data format" in response_text:
            return False, "❌ Invalid data format sent to Apps Script"
        elif "No postData received" in response_text:
            return False, "❌ No data received by Apps Script"
        else:
            return False, f"❌ Apps Script returned: {response_text}"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return False, f"❌ Network error: {str(e)}"
    except Exception as e:
        return False, f"❌ Unexpected error: {str(e)}"

def main():
    # Header
    st.markdown('<h1 class="main-header">📋 Challan OCR & Data Extractor</h1>', unsafe_allow_html=True)
    st.markdown("Upload challan images, extract table data with **Google Gemini AI** (faster processing), and send to Google Sheets automatically!")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Gemini API Key
        gemini_api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Get your API key from https://aistudio.google.com/app/apikey"
        )
        
        # Test API Key button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Test API Key", help="Check if your Gemini API key is working"):
                if gemini_api_key:
                    with st.spinner("Testing API key..."):
                        is_working, message = test_gemini_api_key(gemini_api_key)
                        if is_working:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Please enter your API key first")
        
        with col2:
            if st.button("📋 List Models", help="Show available Gemini models"):
                if gemini_api_key:
                    with st.spinner("Fetching models..."):
                        models = list_available_models(gemini_api_key)
                        if models:
                            st.success(f"Found {len(models)} models:")
                            for model in models[:5]:  # Show first 5
                                st.write(f"• {model}")
                        else:
                            st.error("No models found or API error")
                else:
                    st.warning("Please enter your API key first")
        
        # Model selection
        model_option = st.selectbox(
            "Gemini Model",
            ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-1.5-pro-latest"],
            help="Select the Gemini model to use for image analysis. Try 'gemini-1.5-flash' first (fastest and most reliable)."
        )
        
        # Google Apps Script URL
        script_url = st.text_input(
            "Google Apps Script URL",
            value=os.getenv("GOOGLE_APPS_SCRIPT_URL", ""),
            help="Deploy your Apps Script as a web app and paste the URL here"
        )
        
        # Secret key for Apps Script (matches your script)
        secret_key = st.text_input(
            "Secret Key",
            value="abc123",
            help="Must match the secret key in your Apps Script (currently: abc123)"
        )
        
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Enter your Gemini API key
        2. Enter your Google Apps Script URL
        3. Upload a challan image
        4. Click 'Analyze with Gemini AI'
        5. Review extracted data
        6. Send to Google Sheets
        """)
        
        st.markdown("---")
        st.markdown("### 📊 Sheet Structure")
        st.markdown("""
        Your Google Sheet will receive data in this order:
        1. Job ID (Challan No.)
        2. Party/Vendor (Name of Vendor)
        3. Item (Description of goods)
        4. Weight Sent
        5. Weight Received (0 if empty)
        6. Status (Received/Not Received)
        7. Remarks (empty)
        8. Difference (Weight Sent - Weight Received)
        9. No. of Bags
        10. Plating Colour
        11. Photo Links (empty)
        12. Date (upload date)
        13. Processing Timestamp (upload time)
        """)
        
        st.markdown("---")
        st.markdown("### 🔧 Troubleshooting")
        
        with st.expander("🤖 Gemini API Issues"):
            st.markdown("""
            - **Invalid API Key**: Check your Gemini API key
            - **Quota Exceeded**: Check your usage limits
            - **Safety Filters**: Content blocked, try different image
            - **Test your key**: Use the test button above
            """)
        
        with st.expander("📊 Google Apps Script Issues"):
            st.markdown("""
            **401 Unauthorized Error:**
            1. **Check Deployment Settings:**
               - Execute as: "Me" (your account)
               - Who has access: "Anyone" or "Anyone, even anonymous"
            
            2. **Redeploy Your Script:**
               - Go to Deploy → New deployment
               - Change version to "New version"
               - Copy the new URL
            
            3. **Check Script Permissions:**
               - Make sure script has access to your spreadsheet
               - Try running the script manually first
            
            4. **Verify URL Format:**
               - Should end with `/exec` not `/dev`
               - Should be the web app URL, not editor URL
            """)
        
        with st.expander("🔍 Debug Mode"):
            st.markdown("""
            When you send data to Google Sheets, debug information will show:
            - Script URL being used
            - Response status and headers
            - Exact payload being sent
            """)
        
        
        st.markdown("---")
        st.markdown("### 🔗 Quick Links")
        st.markdown("- [Gemini API Keys](https://aistudio.google.com/app/apikey)")
        st.markdown("- [Gemini AI Studio](https://aistudio.google.com/)")
        st.markdown("- [Google Apps Script](https://script.google.com/)")

    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Image")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a challan image...",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'],
            help="Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF (Max 10MB)"
        )
        
        if uploaded_file is not None:
            # Display uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Challan", use_column_width=True)
            
            # Image info
            st.markdown(f"**File:** {uploaded_file.name}")
            st.markdown(f"**Size:** {uploaded_file.size:,} bytes")
            st.markdown(f"**Dimensions:** {image.size[0]} x {image.size[1]} pixels")
            
            # Analyze button
            if st.button("🤖 Analyze with Gemini AI", type="primary", use_container_width=True):
                if not gemini_api_key:
                    st.error("Please enter your Gemini API key in the sidebar!")
                else:
                    with st.spinner("Analyzing image with Gemini AI... This is much faster!"):
                        extracted_data = analyze_image_with_gemini(image, gemini_api_key, model_option)
                        
                        if extracted_data:
                            st.session_state.extracted_data = extracted_data
                            st.success("✅ Image analyzed successfully!")
                        else:
                            st.error("❌ Failed to analyze image. Please check your API key and try again.")
    
    with col2:
        st.header("📊 Extracted Data")
        
        if 'extracted_data' in st.session_state:
            data = st.session_state.extracted_data
            
            # Display challan information
            st.subheader("📋 Challan Information")
            challan_info = data.get('challan_info', {})
            
            info_df = pd.DataFrame([
                ["Job ID (Challan No.)", challan_info.get('challan_number', 'N/A')],
                ["Party/Vendor", challan_info.get('vendor_name', 'N/A')],
                ["Date", challan_info.get('date', 'N/A')]
            ], columns=["Field", "Value"])
            
            st.dataframe(info_df, use_container_width=True, hide_index=True)
            
            # Display table data
            st.subheader("📊 Table Data")
            table_data = data.get('table_data', [])
            
            if table_data:
                # Filter out rows with empty descriptions for display
                filtered_table_data = []
                for item in table_data:
                    description = item.get('description', '').strip()
                    if description:  # Only include rows with descriptions
                        filtered_table_data.append(item)
                
                if filtered_table_data:
                    df = pd.DataFrame(filtered_table_data)
                    st.dataframe(df, use_container_width=True)
                    
                    st.info(f"Found {len(filtered_table_data)} valid rows of table data (filtered from {len(table_data)} total)")
                else:
                    st.warning("No valid table data found (all descriptions were empty).")
            else:
                st.warning("No table data found in the image.")
            
            # Show JSON preview
            with st.expander("🔍 View Raw JSON Data"):
                st.json(data)
            
            # Send to Google Sheets button
            st.markdown("---")
            if st.button("📤 Send to Google Sheets", type="primary", use_container_width=True):
                if not script_url:
                    st.error("Please enter your Google Apps Script URL in the sidebar!")
                else:
                    with st.spinner("Sending data to Google Sheets..."):
                        success, message = send_to_google_sheets(data, script_url, secret_key)
                        
                        if success:
                            st.success(message)
                            # Show what was sent
                            st.info(f"Sent {len(table_data) if table_data else 1} rows to sheet 'Jobworksheet.csv'")
                        else:
                            st.error(message)
                            
                            # Debug information
                            with st.expander("🔧 Debug Information"):
                                st.write("**Script URL:**", script_url)
                                st.write("**Secret Key:**", secret_key)
                                st.write("**Data being sent:**")
                                
                                # Show the exact payload
                                from datetime import datetime
                                current_date = datetime.now().strftime("%Y-%m-%d")
                                current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                challan_info = data.get('challan_info', {})
                                table_data = data.get('table_data', [])
                                rows = []
                                
                                for item in table_data:
                                    # Skip if description (Item) is empty
                                    description = item.get('description', '').strip()
                                    if not description:
                                        continue
                                        
                                    # Get weight received and handle empty values
                                    weight_received = item.get('weight_received', '').strip()
                                    if not weight_received or weight_received == '':
                                        weight_received = '0'
                                    
                                    # Calculate status based on weight received
                                    try:
                                        weight_received_num = float(weight_received) if weight_received != '0' else 0
                                        status = "Received" if weight_received_num > 0 else "Not Received"
                                    except (ValueError, TypeError):
                                        status = "Not Received"
                                    
                                    # Calculate difference
                                    try:
                                        weight_sent_num = float(item.get('weight_sent', '0')) if item.get('weight_sent', '').strip() else 0
                                        weight_received_num = float(weight_received) if weight_received != '0' else 0
                                        difference = weight_sent_num - weight_received_num
                                    except (ValueError, TypeError):
                                        difference = 0
                                    
                                    row = [
                                        challan_info.get('challan_number', ''),  # Job ID
                                        challan_info.get('vendor_name', ''),     # Party/Vendor
                                        description,                             # Item
                                        item.get('weight_sent', ''),             # Weight Sent
                                        weight_received,                         # Weight Received
                                        status,                                  # Status
                                        '',                                      # Remarks
                                        str(difference),                         # Difference
                                        item.get('number_of_bags', ''),          # No. of Bags
                                        item.get('plating_color', ''),           # Plating Colour
                                        '',                                      # Photo Links
                                        current_date,                            # Date
                                        current_timestamp                        # Processing Timestamp
                                    ]
                                    rows.append(row)
                                
                                if not rows:
                                    row = [
                                        challan_info.get('challan_number', ''),  # Job ID
                                        challan_info.get('vendor_name', ''),     # Party/Vendor
                                        '',                                      # Item
                                        '',                                      # Weight Sent
                                        '0',                                     # Weight Received
                                        'Not Received',                          # Status
                                        '',                                      # Remarks
                                        '0',                                     # Difference
                                        '',                                      # No. of Bags
                                        '',                                      # Plating Colour
                                        '',                                      # Photo Links
                                        current_date,                            # Date
                                        current_timestamp                        # Processing Timestamp
                                    ]
                                    rows.append(row)
                                
                                payload = {"key": secret_key, "data": rows}
                                st.json(payload)
        else:
            st.info("Upload an image and click 'Analyze with Gemini AI' to see extracted data here.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>🚀 Powered by Google Gemini AI | Built with Streamlit</p>
        <p>⚡ Faster processing with Gemini Vision | Compatible with your Google Apps Script</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()