# Challan OCR & Data Extractor (Streamlit + OpenAI)

A powerful Streamlit web application that uses OpenAI's GPT-4 Vision API to extract structured data from challan images and automatically sends it to Google Sheets via Google Apps Script.

## 🚀 Features

- 📷 **Image Upload**: Easy drag & drop interface for challan images
- 🤖 **AI-Powered Analysis**: Uses GPT-4 Vision for accurate data extraction
- 📊 **Smart Data Parsing**: Intelligently structures challan data into tables
- 📋 **Live Preview**: Real-time preview of extracted data
- 📤 **Google Sheets Integration**: Direct submission to Google Sheets
- 🎨 **Modern UI**: Beautiful, responsive Streamlit interface
- 🔒 **Secure**: API keys handled securely

## 📋 Prerequisites

1. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
2. **Google Apps Script**: Set up the provided script as a web app
3. **Python 3.8+**: Required for running the application

## 🛠️ Installation

### 1. Clone or Download
```bash
cd challan_access
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## ⚙️ Configuration

### OpenAI API Setup
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Enter the key in the sidebar when using the app

### Google Apps Script Setup
1. Go to [Google Apps Script](https://script.google.com/)
2. Create a new project
3. Replace the default code with:

```javascript
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      Logger.log("No postData received.");
      return ContentService.createTextOutput("Error: No postData received");
    }

    Logger.log("Raw postData: " + e.postData.contents);

    var secret = "abc123";
    var params = JSON.parse(e.postData.contents);

    if (params.key !== secret) {
      Logger.log("Unauthorized attempt with key: " + params.key);
      return ContentService.createTextOutput("Unauthorized");
    }

    if (!params.data || !Array.isArray(params.data)) {
      Logger.log("Invalid data format.");
      return ContentService.createTextOutput("Error: Invalid data format");
    }

    var rows = params.data;
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Jobworksheet.csv");

    for (var i = 0; i < rows.length; i++) {
      sheet.appendRow(rows[i]);
    }

    Logger.log("Successfully added " + rows.length + " rows.");
    return ContentService.createTextOutput("Success");

  } catch (err) {
    Logger.log("Error: " + err);
    return ContentService.createTextOutput("Error: " + err);
  }
}
```

4. Deploy as web app:
   - Click "Deploy" > "New deployment"
   - Choose type: "Web app"
   - Execute as: "Me"
   - Who has access: "Anyone"
   - Click "Deploy"
5. Copy the web app URL

### Google Sheets Setup
1. Create a new Google Spreadsheet
2. Add a sheet named "Jobworksheet.csv"
3. Ensure the Apps Script has access to this spreadsheet

## 📱 How to Use

1. **Start the App**: Run `streamlit run app.py`
2. **Configure APIs**: Enter your OpenAI API key and Google Apps Script URL in the sidebar
3. **Upload Image**: Drag and drop or browse to upload a challan image
4. **Analyze**: Click "Analyze with AI" to extract data using GPT-4 Vision
5. **Review**: Check the extracted challan information and table data
6. **Submit**: Click "Send to Google Sheets" to submit the data

## 📊 Data Structure

The application extracts and structures:

### Challan Information
- Company name
- Vendor name
- Challan number
- Date
- Address

### Table Data (per item)
- Serial number
- Description of goods
- Plating/Color information
- Weight sent
- Number of bags
- Weight received
- Date of receiving
- Remarks

## 🔧 Advanced Features

### Environment Variables (Optional)
Create a `.env` file for default configurations:
```
OPENAI_API_KEY=your_key_here
GOOGLE_APPS_SCRIPT_URL=your_script_url_here
```

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff)
- Maximum file size: 10MB

## 🚨 Troubleshooting

### Common Issues

**OpenAI API Errors**
- Verify your API key is correct
- Check you have sufficient credits
- Ensure GPT-4 Vision access is enabled

**Google Sheets Issues**
- Verify Apps Script URL is correct
- Check that the script is deployed as web app
- Ensure sheet name is "Jobworksheet.csv"
- Verify the secret key matches ("abc123")

**Image Analysis Issues**
- Use clear, well-lit images
- Ensure text is horizontal and readable
- Try different image formats if extraction fails

### Error Messages
- **"Please enter your OpenAI API key"**: Add API key in sidebar
- **"Failed to analyze image"**: Check image quality and API key
- **"Error submitting to Google Sheets"**: Verify Apps Script URL and deployment

## 💡 Tips for Best Results

1. **Image Quality**: Use high-resolution, clear images
2. **Lighting**: Ensure good lighting and contrast
3. **Orientation**: Keep text horizontal for better recognition
4. **Format**: PNG or JPEG formats work best
5. **Size**: Larger images (within 10MB limit) often work better

## 🔒 Security Notes

- API keys are handled securely in memory only
- No images are stored permanently
- All processing happens locally except API calls
- Use environment variables for production deployments

## 📈 Performance

- **Analysis Time**: 10-30 seconds depending on image complexity
- **Accuracy**: Significantly higher than traditional OCR
- **Supported Languages**: Primarily English, but can handle other languages
- **Concurrent Users**: Supports multiple users (limited by API quotas)

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Check API quotas and limits
4. Review error messages in the Streamlit interface

## 📄 License

MIT License - feel free to modify and use as needed.

---

**Note**: This application requires active internet connection for OpenAI API calls and Google Sheets integration.